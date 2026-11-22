import os
import re
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

# Set before app imports. Never use the application DATABASE_URL for test cleanup.
_temp = tempfile.TemporaryDirectory()
os.environ['DATABASE_URL'] = f'sqlite:///{Path(_temp.name) / "test.db"}'
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import delete, select
from alembic.config import Config
from alembic import command
from app.main import app
from app.database import SessionLocal
from app.models import Editor, Verification, Session, Contact, WebsiteTemplateSelection, WebPage, EditorJournal, EditorJournalPage, JournalIssue, JournalArticle, ManuscriptSubmission, SubmissionCaptcha
from app import routes
from app.security import digest

@pytest.fixture(autouse=True)
def setup(monkeypatch):
    from app.config import settings
    monkeypatch.setattr(settings,"internal_api_key","test-internal-key")
    command.upgrade(Config('alembic.ini'), 'head')
    with SessionLocal() as db:
        for model in (SubmissionCaptcha, ManuscriptSubmission, JournalArticle, JournalIssue, EditorJournalPage, EditorJournal, WebPage, WebsiteTemplateSelection, Session, Verification, Contact, Editor):
            db.execute(delete(model))
        db.commit()
    messages = []
    monkeypatch.setattr(routes, 'send_email', lambda to, subject, body: messages.append((to, subject, body)))
    yield messages

@pytest.fixture
def client():
    with TestClient(app,headers={"X-Internal-API-Key":"test-internal-key"}) as c:
        yield c

payload = dict(first_name='Himanshu', last_name='Jain', phone='+91 9876543210',
               gender='Male', email='editor@example.com', password='test-password-1234')

def register(client, messages):
    assert client.post('/api/v1/auth/register', json=payload).status_code == 202
    return re.search(r'token=([^\s]+)', messages[-1][2]).group(1)

def authenticate(client, messages):
    token = register(client, messages)
    assert client.post('/api/v1/auth/verify-email', json={'token': token}).status_code == 200
    r = client.post('/api/v1/auth/login', json={k: payload[k] for k in ('email', 'password')})
    assert r.status_code == 200
    return r.json()['access_token']

def auth_headers(client, token):
    headers={"Authorization":f"Bearer {token}"}
    identity=client.get("/api/v1/auth/me",headers=headers)
    if identity.status_code==200:
        headers["X-Editor-Code"]=identity.json()["public_code"]
    return headers

def test_full_auth_flow(client, setup):
    token = register(client, setup)
    credentials = {k: payload[k] for k in ('email', 'password')}
    assert client.post('/api/v1/auth/login', json=credentials).status_code == 403
    assert client.post('/api/v1/auth/verify-email', json={'token': token}).status_code == 200
    assert client.post('/api/v1/auth/verify-email', json={'token': token}).status_code == 400
    session = client.post('/api/v1/auth/login', json=credentials).json()['access_token']
    headers = auth_headers(client, session)
    profile = client.get('/api/v1/auth/me', headers=headers)
    assert profile.status_code == 200
    assert profile.json()['is_verified'] is True
    assert 'password_hash' not in profile.json()
    with SessionLocal() as db:
        assert db.get(Session, digest(session)) is not None
        assert db.get(Session, session) is None
        assert db.scalar(select(Editor)).password_hash != payload['password']
    assert client.post('/api/v1/auth/logout', headers=headers).status_code == 204
    assert client.get('/api/v1/auth/me', headers=headers).status_code == 401

def test_resend_expiry_and_duplicate(client, setup):
    old = register(client, setup)
    assert client.post('/api/v1/auth/register', json=payload).status_code == 202
    assert len(setup) == 1
    assert client.post('/api/v1/auth/resend-verification', json={'email': payload['email']}).status_code == 202
    new = re.search(r'token=([^\s]+)', setup[-1][2]).group(1)
    assert old != new
    assert client.post('/api/v1/auth/verify-email', json={'token': old}).status_code == 400
    with SessionLocal() as db:
        db.get(Verification, digest(new)).expires_at = datetime.now(timezone.utc) - timedelta(minutes=1)
        db.commit()
    assert client.post('/api/v1/auth/verify-email', json={'token': new}).status_code == 400

def test_validation_and_invalid_login(client, setup):
    assert client.post('/api/v1/auth/register', json={**payload, 'password': 'short'}).status_code == 422
    assert client.post('/api/v1/auth/register', json={**payload, 'email': 'invalid'}).status_code == 422
    assert client.post('/api/v1/auth/register', json={**payload, 'first_name': '   '}).status_code == 422
    assert client.get('/api/v1/auth/me').status_code == 401
    assert client.post('/api/v1/auth/login', json={'email': payload['email'], 'password': 'wrong'}).status_code == 401
    authenticate(client, setup)
    assert client.post('/api/v1/auth/login', json={'email': payload['email'], 'password': 'wrong'}).status_code == 401

def test_expired_session(client, setup):
    token = authenticate(client, setup)
    with SessionLocal() as db:
        db.get(Session, digest(token)).expires_at = datetime.now(timezone.utc) - timedelta(seconds=1)
        db.commit()
    assert client.get('/api/v1/auth/me', headers=auth_headers(client, token)).status_code == 401

def test_contact_persists_when_smtp_fails(client, setup, monkeypatch):
    def fail(*args):
        raise OSError('SMTP unavailable')
    monkeypatch.setattr(routes, 'send_email', fail)
    r = client.post('/api/v1/contact', json={'name': 'Editor', 'email': 'editor@example.com', 'message': 'Please contact me about Edora.'})
    assert r.status_code == 201
    with SessionLocal() as db:
        assert db.scalar(select(Contact)).message == 'Please contact me about Edora.'

def test_verification_delivery_recovery(client, setup, monkeypatch):
    def fail(*args):
        raise OSError('SMTP unavailable')
    monkeypatch.setattr(routes, 'send_email', fail)
    assert client.post('/api/v1/auth/register', json=payload).status_code == 202
    with SessionLocal() as db:
        assert db.scalar(select(Editor)).is_verified is False
    monkeypatch.setattr(routes, 'send_email', lambda *args: setup.append(args))
    assert client.post('/api/v1/auth/resend-verification', json={'email': payload['email']}).status_code == 202
    token = re.search(r'token=([^\s]+)', setup[-1][2]).group(1)
    assert client.post('/api/v1/auth/verify-email', json={'token': token}).status_code == 200


def test_admin_permissions_and_inactive_sessions(client, setup, monkeypatch):
    from app.config import settings
    from app.seed_admin import seed_admin
    monkeypatch.setattr(settings, "super_admin_email", "admin@example.com")
    monkeypatch.setattr(settings, "super_admin_password", "admin-password-1234")
    assert seed_admin() is True
    assert seed_admin() is False
    user_token = authenticate(client, setup)
    user_headers = auth_headers(client, user_token)
    assert client.get("/api/v1/admin/users").status_code == 401
    assert client.get("/api/v1/admin/users", headers=user_headers).status_code == 403
    token = client.post("/api/v1/auth/login", json={"email": "admin@example.com", "password": "admin-password-1234"}).json()["access_token"]
    headers = auth_headers(client, token)
    users = client.get("/api/v1/admin/users", headers=headers).json()
    assert users["total"] == 2
    editor = next(u for u in users["items"] if u["role"] == "editor")
    admin = next(u for u in users["items"] if u["role"] == "super_admin")
    path = f'/api/v1/admin/users/{editor["id"]}'
    data = {k: editor[k] for k in ("first_name", "last_name", "phone", "gender", "email", "is_active")}
    assert client.patch(path, headers=user_headers, json=data).status_code == 403
    assert client.delete(path, headers=user_headers).status_code == 403
    assert client.patch(path, headers=headers, json={**data, "role": "super_admin"}).status_code == 422
    assert client.patch(path, headers=headers, json={**data, "is_active": False}).status_code == 200
    assert client.get("/api/v1/auth/me", headers=user_headers).status_code == 401
    assert client.post("/api/v1/auth/login", json={k: payload[k] for k in ("email", "password")}).status_code == 403
    assert client.patch(path, headers=headers, json=data).status_code == 200
    assert client.get("/api/v1/auth/me", headers=user_headers).status_code == 401
    assert client.patch(path, headers=headers, json={**data, "email": "admin@example.com"}).status_code == 409
    changed = client.patch(path, headers=headers, json={**data, "email": "new@example.com"})
    assert changed.status_code == 200
    assert changed.json()["is_verified"] is False
    assert client.delete(f'/api/v1/admin/users/{admin["id"]}', headers=headers).status_code == 403
    assert client.patch(f'/api/v1/admin/users/{admin["id"]}', headers=headers, json=data).status_code == 403
    assert client.delete(path, headers=headers).status_code == 204
    assert client.delete(path, headers=headers).status_code == 404


def test_template_management_and_user_selection(client, setup, monkeypatch):
    from app.config import settings
    from app.seed_admin import seed_admin
    from app.models import WebsiteTemplate
    from app.template_schemas import TemplateInput
    monkeypatch.setattr(settings, "super_admin_email", "admin@example.com")
    monkeypatch.setattr(settings, "super_admin_password", "admin-password-1234")
    seed_admin()
    credentials = {"email": "admin@example.com", "password": "admin-password-1234"}
    token = client.post("/api/v1/auth/login", json=credentials).json()["access_token"]
    admin = auth_headers(client, token)
    user = auth_headers(client, authenticate(client, setup))
    assert client.get("/api/v1/admin/templates").status_code == 401
    assert client.get("/api/v1/admin/templates", headers=user).status_code == 403
    starters = client.get("/api/v1/templates", headers=user).json()
    assert {t["name"] for t in starters} >= {"Classic Journal", "Sidebar Studio"}
    assert {t["layout"]["menu_position"] for t in starters} >= {"top", "left"}
    assert client.get("/api/v1/website/template", headers=user).json() is None
    data = {"name": "Test Portfolio", "description": "A right sidebar layout", "layout": starters[0]["layout"]}
    for template in starters:
        for section in template["layout"]["sections"]:
            assert re.fullmatch(r"#[0-9a-f]{6}", section["background_color"])
            assert re.fullmatch(r"#[0-9a-f]{6}", section["text_color"])
    data["layout"]["menu_position"] = "right"
    for section in data["layout"]["sections"]:
        section["background_color"] = "#123ABC"
        section["text_color"] = "#FEDCBA"
    assert client.post("/api/v1/admin/templates", headers=user, json=data).status_code == 403
    created = client.post("/api/v1/admin/templates", headers=admin, json=data)
    assert created.status_code == 201
    template_id = created.json()["id"]
    delete_path = f"/api/v1/admin/templates/{template_id}"
    assert client.delete(delete_path).status_code == 401
    assert client.delete(delete_path, headers=user).status_code == 403
    assert client.delete("/api/v1/admin/templates/999999", headers=admin).status_code == 404
    assert client.post("/api/v1/admin/templates", headers=admin, json=data).status_code == 409
    with SessionLocal() as db:
        stored = db.get(WebsiteTemplate, template_id).layout
        assert stored["menu_position"] == "right"
        assert all(section["background_color"] == "#123abc" and section["text_color"] == "#fedcba" for section in stored["sections"])
    import copy
    for field in ("background_color", "text_color"):
        for invalid_color in ("red", "#123", "#1234567", "url(https://example.com)", "#zzzzzz", ""):
            invalid_colors = copy.deepcopy(data)
            invalid_colors["layout"]["sections"][0][field] = invalid_color
            assert client.post("/api/v1/admin/templates", headers=admin, json=invalid_colors).status_code == 422
            assert client.patch(f"/api/v1/admin/templates/{template_id}", headers=admin, json=invalid_colors).status_code == 422
    invalid = {**data, "layout": {"menu_position": "right", "sections": [data["layout"]["sections"][0]] * 4}}
    assert client.post("/api/v1/admin/templates", headers=admin, json=invalid).status_code == 422
    assert client.post("/api/v1/admin/templates", headers=admin, json={**data, "name": "   "}).status_code == 422
    assert client.post("/api/v1/admin/templates", headers=admin, json={**data, "layout": {**data["layout"], "menu_position": "invalid"}}).status_code == 422
    assert client.post("/api/v1/website/template", json={"template_id": template_id}).status_code == 401
    assert client.post("/api/v1/website/template", headers=user, json={"template_id": 999999}).status_code == 404
    assert client.post("/api/v1/website/template", headers=user, json={"template_id": template_id}).status_code == 200
    assert client.get("/api/v1/website/template", headers=user).json()["id"] == template_id
    assert client.delete(delete_path, headers=admin).status_code == 409
    assert client.get("/api/v1/website/template", headers=user).json()["id"] == template_id
    assert client.get("/api/v1/website/template", headers=admin).json() is None
    data["layout"]["sections"][0]["title"] = "Updated site title"
    data["layout"]["sections"][0]["background_color"] = "#345678"
    data["layout"]["sections"][0]["text_color"] = "#ffffff"
    path = f"/api/v1/admin/templates/{template_id}"
    assert client.patch(path, headers=user, json=data).status_code == 403
    assert client.patch("/api/v1/admin/templates/999999", headers=admin, json=data).status_code == 404
    assert client.patch(path, headers=admin, json=data).status_code == 200
    selected = client.get("/api/v1/website/template", headers=user).json()
    assert selected["layout"]["sections"][0]["title"] == "Updated site title"
    assert selected["layout"]["sections"][0]["background_color"] == "#345678"
    assert selected["layout"]["sections"][0]["text_color"] == "#ffffff"
    assert client.post("/api/v1/website/template", headers=user, json={"template_id": starters[0]["id"]}).status_code == 200
    assert client.get("/api/v1/website/template", headers=user).json()["id"] == starters[0]["id"]
    deleted = client.delete(delete_path, headers=admin)
    assert deleted.status_code == 204
    assert deleted.content == b""
    assert client.delete(delete_path, headers=admin).status_code == 404
    assert template_id not in {item["id"] for item in client.get("/api/v1/templates", headers=user).json()}
    assert template_id not in {item["id"] for item in client.get("/api/v1/admin/templates", headers=admin).json()}
    with SessionLocal() as db:
        assert db.get(WebsiteTemplate, template_id) is None
    assert client.post("/api/v1/website/template", headers=user, json={"template_id": template_id}).status_code == 404
    with SessionLocal() as db:
        editor_id = db.scalar(select(Editor).where(Editor.email == payload["email"])).id
    assert client.delete(f"/api/v1/admin/users/{editor_id}", headers=admin).status_code == 204


def test_page_crud_permissions_html_and_validation(client, setup, monkeypatch):
    from app.config import settings
    from app.seed_admin import seed_admin
    monkeypatch.setattr(settings, "super_admin_email", "admin@example.com")
    monkeypatch.setattr(settings, "super_admin_password", "admin-password-1234")
    seed_admin()
    token = client.post("/api/v1/auth/login", json={"email": "admin@example.com", "password": "admin-password-1234"}).json()["access_token"]
    admin = auth_headers(client, token)
    user = auth_headers(client, authenticate(client, setup))
    base = "/api/v1/admin/pages"
    data = {"title": "About us", "slug": "about-us", "content_html": '<h2>Our team</h2><p>Hello <strong>world</strong>.</p><ul><li>One</li></ul><a href="https://example.com">Visit</a>'}
    assert client.get(base).status_code == 401
    assert client.get(base, headers=user).status_code == 403
    assert client.post(base, headers=user, json=data).status_code == 403
    result = client.post(base, headers=admin, json=data)
    assert result.status_code == 201
    page_id = result.json()["id"]
    path = f"{base}/{page_id}"
    html = result.json()["content_html"]
    assert "<h2>Our team</h2>" in html and "<strong>world</strong>" in html
    assert '<a href="https://example.com"' in html
    with SessionLocal() as db:
        assert db.get(WebPage, page_id).content_html == html
    assert client.get(path, headers=admin).json()["content_html"] == html
    assert "content_html" not in client.get(base, headers=admin).json()[0]
    assert client.get(path, headers=user).status_code == 403
    assert client.patch(path, headers=user, json=data).status_code == 403
    assert client.delete(path, headers=user).status_code == 403
    assert client.delete(path).status_code == 401
    assert client.post(base, headers=admin, json=data).status_code == 409
    for changes in ({"title": " "}, {"slug": "../bad"}, {"slug": "Bad Slug"}, {"content_html": "<p>&nbsp;</p>"}, {"content_html": "<script>alert(1)</script>"}, {"content_html": "x" * 100001}):
        assert client.post(base, headers=admin, json={**data, **changes}).status_code == 422
    attacks = '<p onclick="alert(1)">Safe <em>text</em></p><script>alert(1)</script><style>body{display:none}</style><img src=x onerror="alert(1)"><iframe src="https://example.com"></iframe><svg onload="alert(1)"></svg><a href="javascript:alert(1)">Bad link</a>'
    updated = client.patch(path, headers=admin, json={**data, "title": "Updated", "content_html": attacks})
    assert updated.status_code == 200
    sanitized = updated.json()["content_html"]
    assert "<em>text</em>" in sanitized
    for unsafe in ("onclick", "onerror", "javascript:", "<script", "<style", "<img", "<iframe", "<svg", "alert(1)"):
        assert unsafe not in sanitized
    second = client.post(base, headers=admin, json={**data, "slug": "contact"}).json()
    assert client.patch(f'{base}/{second["id"]}', headers=admin, json=data).status_code == 409
    assert client.get(f'{base}/{second["id"]}', headers=admin).json()["slug"] == "contact"
    assert client.get(f"{base}/999999", headers=admin).status_code == 404
    assert client.patch(f"{base}/999999", headers=admin, json=data).status_code == 404
    assert client.delete(f"{base}/999999", headers=admin).status_code == 404
    assert client.delete(path, headers=admin).status_code == 204
    assert client.get(path, headers=admin).status_code == 404
    assert client.delete(path, headers=admin).status_code == 404
    with SessionLocal() as db:
        assert db.get(WebPage, page_id) is None


def test_editor_profile_updates_and_email_verification(client, setup):
    token = authenticate(client, setup)
    headers = auth_headers(client, token)
    profile = {key: payload[key] for key in ("first_name", "last_name", "phone", "gender", "email")}
    assert client.patch("/api/v1/editor/profile", json=profile).status_code == 401
    assert client.patch("/api/v1/editor/profile", headers=headers, json={**profile, "role": "super_admin"}).status_code == 422
    assert client.patch("/api/v1/editor/profile", headers=headers, json={**profile, "first_name": " "}).status_code == 422
    saved = client.patch("/api/v1/editor/profile", headers=headers, json={**profile, "first_name": "Updated"})
    assert saved.status_code == 200
    assert saved.json()["first_name"] == "Updated"
    assert client.get("/api/v1/auth/me", headers=headers).status_code == 200
    result = client.patch("/api/v1/editor/profile", headers=headers, json={**profile, "email": "new-editor@example.com"})
    assert result.status_code == 200 and result.json()["is_verified"] is False
    assert client.get("/api/v1/auth/me", headers=headers).status_code == 401
    assert client.post("/api/v1/auth/login", json={"email": "new-editor@example.com", "password": payload["password"]}).status_code == 403
    verification = re.search(r'token=([^\s]+)', setup[-1][2]).group(1)
    assert client.post("/api/v1/auth/verify-email", json={"token": verification}).status_code == 200
    assert client.post("/api/v1/auth/login", json={"email": "new-editor@example.com", "password": payload["password"]}).status_code == 200


def test_private_journal_copies_and_tenant_isolation(client, setup, monkeypatch):
    from app.config import settings
    from app.seed_admin import seed_admin
    from app.models import WebsiteTemplate
    monkeypatch.setattr(settings, "super_admin_email", "admin@example.com")
    monkeypatch.setattr(settings, "super_admin_password", "admin-password-1234")
    seed_admin()
    admin_token = client.post("/api/v1/auth/login", json={"email": "admin@example.com", "password": "admin-password-1234"}).json()["access_token"]
    admin = auth_headers(client, admin_token)
    first = auth_headers(client, authenticate(client, setup))
    second_data = {**payload, "email": "second-editor@example.com"}
    assert client.post("/api/v1/auth/register", json=second_data).status_code == 202
    verification = re.search(r'token=([^\s]+)', setup[-1][2]).group(1)
    client.post("/api/v1/auth/verify-email", json={"token": verification})
    second_token = client.post("/api/v1/auth/login", json={"email": second_data["email"], "password": payload["password"]}).json()["access_token"]
    second = auth_headers(client, second_token)
    starter = client.get("/api/v1/templates", headers=first).json()[0]
    source_template = {"name": "Private Journal Source", "description": "Snapshot source", "layout": starter["layout"]}
    template = client.post("/api/v1/admin/templates", headers=admin, json=source_template).json()
    source_page = {"title": "Source page", "slug": "source-one", "content_html": "<h2>Original</h2><p>Keep this content</p>"}
    page_one = client.post("/api/v1/admin/pages", headers=admin, json=source_page).json()
    page_two = client.post("/api/v1/admin/pages", headers=admin, json={**source_page, "title": "Second source", "slug": "source-two"}).json()
    journal_input = {"name": "My Journal", "template_id": template["id"], "page_ids": [page_two["id"], page_one["id"]], "new_pages": [{"title": "My introduction", "slug": "my-introduction", "content_html": "<p>Private introduction</p>"}]}
    assert client.get("/api/v1/editor/journal").status_code == 401
    assert client.get("/api/v1/editor/journal", headers=admin).status_code == 403
    assert client.get("/api/v1/editor/journal", headers=first).json() is None
    assert client.post("/api/v1/editor/journal", headers=first, json={**journal_input, "editor_id": 999}).status_code == 422
    assert client.post("/api/v1/editor/journal", headers=first, json={**journal_input, "page_ids": [], "new_pages": []}).status_code == 422
    assert client.post("/api/v1/editor/journal", headers=first, json={**journal_input, "page_ids": [page_one["id"], page_one["id"]]}).status_code == 422
    assert client.post("/api/v1/editor/journal", headers=first, json={**journal_input, "template_id": 999999}).status_code == 404
    assert client.post("/api/v1/editor/journal", headers=first, json={**journal_input, "page_ids": [page_one["id"], 999999]}).status_code == 404
    assert client.get("/api/v1/editor/journal", headers=first).json() is None
    library = client.get("/api/v1/editor/pages", headers=first)
    assert library.status_code == 200 and len(library.json()) == 2
    assert client.get(f'/api/v1/editor/pages/{page_one["id"]}', headers=first).status_code == 200
    duplicate_slug = {**journal_input, "new_pages": [{"title": "Conflict", "slug": "source-one", "content_html": "<p>New text</p>"}]}
    assert client.post("/api/v1/editor/journal", headers=first, json=duplicate_slug).status_code == 409
    assert client.get("/api/v1/editor/journal", headers=first).json() is None
    one = client.post("/api/v1/editor/journal", headers=first, json=journal_input)
    assert one.status_code == 201
    one = one.json()
    two = client.post("/api/v1/editor/journal", headers=second, json={**journal_input, "name": "Another Journal"}).json()
    assert re.fullmatch(r"[a-z0-9]{8}", one["editor_code"])
    assert re.fullmatch(r"[a-z0-9]{8}", two["editor_code"])
    assert one["editor_code"] != two["editor_code"]
    assert one["slug"] == "my-journal"
    assert one["preview_path"] == f'/{one["editor_code"]}/my-journal/source-two'
    assert one["id"] != two["id"]
    assert one["pages"][2]["id"] != two["pages"][2]["id"]
    assert one["pages"][2]["content_html"] == "<p>Private introduction</p>"
    assert len(client.get("/api/v1/editor/pages", headers=first).json()) == 2
    assert len(client.get("/api/v1/admin/pages", headers=admin).json()) == 2
    assert one["pages"][0]["id"] != two["pages"][0]["id"]
    assert [p["slug"] for p in one["pages"]] == ["source-two", "source-one", "my-introduction"]
    assert client.post("/api/v1/editor/journal", headers=first, json=journal_input).status_code == 409
    private_page = {"title": "My custom page", "slug": "my-custom-page", "content_html": '<p onclick="bad()">Private content</p><script>bad()</script>'}
    own_path = f'/api/v1/editor/journal/pages/{one["pages"][0]["id"]}'
    assert client.patch(own_path, headers=second, json=private_page).status_code == 404
    saved = client.patch(own_path, headers=first, json=private_page)
    assert saved.status_code == 200
    assert saved.json()["pages"][0]["content_html"] == "<p>Private content</p>"
    import copy
    private_template = copy.deepcopy(source_template)
    private_template["layout"]["sections"][0]["background_color"] = "#112233"
    assert client.patch("/api/v1/editor/journal/template", headers=first, json=private_template).status_code == 200
    assert client.get("/api/v1/editor/journal", headers=second).json()["template_layout"] == two["template_layout"]
    assert client.get("/api/v1/editor/journal", headers=second).json()["pages"] == two["pages"]
    assert client.get(f'/api/v1/admin/pages/{page_two["id"]}', headers=admin).json()["title"] == "Second source"
    assert next(t for t in client.get("/api/v1/admin/templates", headers=admin).json() if t["id"] == template["id"])["layout"] == template["layout"]
    changed_source = copy.deepcopy(source_template)
    changed_source["layout"]["sections"][0]["title"] = "Admin changes"
    client.patch(f'/api/v1/admin/templates/{template["id"]}', headers=admin, json=changed_source)
    client.patch(f'/api/v1/admin/pages/{page_one["id"]}', headers=admin, json={**source_page, "content_html": "<p>Admin changes</p>"})
    assert client.get("/api/v1/editor/journal", headers=second).json()["pages"] == two["pages"]
    assert client.get("/api/v1/editor/journal", headers=second).json()["template_layout"] == two["template_layout"]
    assert client.delete(f'/api/v1/admin/templates/{template["id"]}', headers=admin).status_code == 204
    assert client.delete(f'/api/v1/admin/pages/{page_one["id"]}', headers=admin).status_code == 204
    assert client.get("/api/v1/editor/journal", headers=second).json()["pages"] == two["pages"]
    before_add = client.get("/api/v1/editor/journal", headers=first).json()
    new_page = {"title": "Added after creation", "slug": "added-later", "content_html": '<p onclick="bad()">Only mine</p><script>bad()</script>'}
    add_url = "/api/v1/editor/journal/pages"
    assert client.post(add_url, json=new_page).status_code == 401
    assert client.post(add_url, headers=admin, json=new_page).status_code == 403
    assert client.post(add_url, headers=first, json={**new_page, "editor_id": 99}).status_code == 422
    assert client.post(add_url, headers=first, json={**new_page, "content_html": "<p></p>"}).status_code == 422
    added = client.post(add_url, headers=first, json=new_page)
    assert added.status_code == 201
    added = added.json()
    assert len(added["pages"]) == len(before_add["pages"]) + 1
    last_page = added["pages"][-1]
    assert last_page["slug"] == "added-later" and last_page["content_html"] == "<p>Only mine</p>"
    assert client.post(add_url, headers=first, json=new_page).status_code == 409
    assert client.get("/api/v1/editor/journal", headers=second).json()["pages"] == two["pages"]
    assert all(page["slug"] != "added-later" for page in client.get("/api/v1/editor/pages", headers=first).json())
    assert all(page["slug"] != "added-later" for page in client.get("/api/v1/admin/pages", headers=admin).json())
    ids = [page["id"] for page in added["pages"]]
    order_url = "/api/v1/editor/journal/pages/order"
    assert client.patch(order_url, json={"page_ids": ids}).status_code == 401
    assert client.patch(order_url, headers=admin, json={"page_ids": ids}).status_code == 403
    assert client.patch(order_url, headers=first, json={"page_ids": ids[:-1]}).status_code == 409
    assert client.patch(order_url, headers=first, json={"page_ids": [two["pages"][0]["id"]] + ids[1:]}).status_code == 409
    assert client.patch(order_url, headers=first, json={"page_ids": [ids[0]] * len(ids)}).status_code == 422
    assert client.patch(order_url, headers=first, json={"page_ids": []}).status_code == 422
    assert client.patch(order_url, headers=first, json={"page_ids": [True]}).status_code == 422
    assert [page["id"] for page in client.get("/api/v1/editor/journal", headers=first).json()["pages"]] == ids
    new_order = list(reversed(ids))
    reordered = client.patch(order_url, headers=first, json={"page_ids": new_order})
    assert reordered.status_code == 200
    assert [page["id"] for page in reordered.json()["pages"]] == new_order
    assert [page["id"] for page in client.get("/api/v1/editor/journal", headers=first).json()["pages"]] == new_order
    public_url = f'/api/v1/public/journals/{one["editor_code"]}/{one["slug"]}'
    assert [page["slug"] for page in client.get(public_url,headers=first).json()["pages"]] == [page["slug"] for page in reordered.json()["pages"]]
    assert client.get("/api/v1/editor/journal", headers=second).json()["pages"] == two["pages"]
    with SessionLocal() as db:
        editor_id = db.scalar(select(Editor).where(Editor.email == payload["email"])).id
    assert client.delete(f"/api/v1/admin/users/{editor_id}", headers=admin).status_code == 204
    with SessionLocal() as db:
        assert db.get(EditorJournal, one["id"]) is None
        assert db.scalars(select(EditorJournalPage).where(EditorJournalPage.journal_id == one["id"])).all() == []
        assert db.get(EditorJournal, two["id"]) is not None


def test_journal_with_only_new_pages_and_invalid_drafts(client, setup):
    headers = auth_headers(client, authenticate(client, setup))
    template_id = client.get("/api/v1/templates", headers=headers).json()[0]["id"]
    new_page = {"title": "Original research", "slug": "original-research", "content_html": '<h2>My research</h2><p onclick="bad()">Private article</p><script>bad()</script>'}
    body = {"name": "Custom Journal", "template_id": template_id, "new_pages": [new_page]}
    for changes in ({"new_pages": []}, {"new_pages": [new_page, new_page]}, {"new_pages": [{**new_page, "slug": "Bad Slug"}]}, {"new_pages": [{**new_page, "content_html": "<p></p>"}]}, {"new_pages": [{**new_page, "editor_id": 999}]}, {"new_pages": [{**new_page, "content_html": "a" * 100001}]}):
        assert client.post("/api/v1/editor/journal", headers=headers, json={**body, **changes}).status_code == 422
        assert client.get("/api/v1/editor/journal", headers=headers).json() is None
    assert client.post("/api/v1/editor/journal", json=body).status_code == 401
    created = client.post("/api/v1/editor/journal", headers=headers, json=body)
    assert created.status_code == 201
    journal = created.json()
    assert journal["slug"] == "custom-journal"
    public_url = f'/api/v1/public/journals/{journal["editor_code"]}/{journal["slug"]}'
    assert client.get(public_url).status_code == 404
    public_response = client.get(public_url,headers=headers)
    assert public_response.status_code == 200
    public = public_response.json()
    assert public["name"] == "Custom Journal"
    assert public["template_layout"] == journal["template_layout"]
    assert public["pages"][0]["content_html"] == "<h2>My research</h2><p>Private article</p>"
    assert set(public) == {"name", "slug", "editor_code", "template_layout", "pages", "journal_info", "editor_email", "menu_order"}
    assert set(public["pages"][0]) == {"title", "slug", "content_html"}
    assert public["editor_email"] == payload["email"]
    assert client.get(f'/api/v1/public/journals/{journal["editor_code"]}/wrong-journal').status_code == 404
    assert client.get('/api/v1/public/journals/00000000/custom-journal').status_code == 404
    assert client.get('/api/v1/public/journals/invalid/custom-journal').status_code == 422
    page = journal["pages"][0]
    assert page["slug"] == "original-research"
    assert page["content_html"] == "<h2>My research</h2><p>Private article</p>"
    assert client.get("/api/v1/editor/pages", headers=headers).json() == []
    with SessionLocal() as db:
        assert db.get(EditorJournalPage, page["id"]) is not None
        assert db.scalars(select(WebPage)).all() == []
    edited = client.patch(f'/api/v1/editor/journal/pages/{page["id"]}', headers=headers, json={**new_page, "content_html": "<p>Updated private text</p>"})
    assert edited.status_code == 200
    assert client.get("/api/v1/editor/journal", headers=headers).json()["pages"][0]["content_html"] == "<p>Updated private text</p>"
    assert client.get(public_url,headers=headers).json()["pages"][0]["content_html"] == "<p>Updated private text</p>"
    with SessionLocal() as db:
        editor = db.scalar(select(Editor).where(Editor.email == payload["email"]))
        editor.is_active = False
        db.commit()
    assert client.get(public_url).status_code == 404



def test_journal_page_total_and_size_limits():
    from app.journal_schemas import JournalCreate
    from pydantic import ValidationError
    page = {"title": "Custom", "slug": "custom", "content_html": "<p>Content</p>"}
    with pytest.raises(ValidationError):
        JournalCreate(name="Journal", template_id=1, page_ids=list(range(1, 101)), new_pages=[page])
    large_pages = [{**page, "slug": f"page-{index}", "content_html": "<p>" + "a" * 99980 + "</p>"} for index in range(11)]
    with pytest.raises(ValidationError):
        JournalCreate(name="Journal", template_id=1, new_pages=large_pages)


def test_multiple_journal_tiles_and_scoped_management(client, setup, monkeypatch):
    first = auth_headers(client, authenticate(client, setup))
    template_id = client.get("/api/v1/templates", headers=first).json()[0]["id"]
    body = {"name": "First Journal", "template_id": template_id, "new_pages": [{"title": "Home", "slug": "home", "content_html": "<p>Original content</p>"}]}
    assert client.get("/api/v1/editor/journals").status_code == 401
    assert client.get("/api/v1/editor/journals", headers=first).json() == []
    assert client.post("/api/v1/editor/journal", headers=first, json={**body, "status": "Published"}).status_code == 422
    one = client.post("/api/v1/editor/journal", headers=first, json=body).json()
    assert one["status"] == "Draft"
    two_response = client.post("/api/v1/editor/journal", headers=first, json={**body, "name": "Second Journal"})
    assert two_response.status_code == 201
    two = two_response.json()
    assert one["editor_code"] == two["editor_code"]
    assert one["preview_path"] != two["preview_path"]
    assert client.post("/api/v1/editor/journal", headers=first, json=body).status_code == 409
    tiles = client.get("/api/v1/editor/journals", headers=first).json()
    assert {tile["id"] for tile in tiles} == {one["id"], two["id"]}
    assert all(tile["page_count"] == 1 for tile in tiles)
    assert all("pages" not in tile and "template_layout" not in tile for tile in tiles)
    assert client.get("/api/v1/editor/journal", headers=first).status_code == 409
    one_path = f'/api/v1/editor/journal?journal_id={one["id"]}'
    two_path = f'/api/v1/editor/journal?journal_id={two["id"]}'
    assert client.get(one_path, headers=first).json()["name"] == "First Journal"
    assert client.get(two_path, headers=first).json()["name"] == "Second Journal"
    new_page = {"title": "Only first", "slug": "only-first", "content_html": "<p>Private content</p>"}
    assert client.post("/api/v1/editor/journal/pages", headers=first, json=new_page).status_code == 409
    assert client.post(f'/api/v1/editor/journal/pages?journal_id={one["id"]}', headers=first, json=new_page).status_code == 201
    assert len(client.get(one_path, headers=first).json()["pages"]) == 2
    assert len(client.get(two_path, headers=first).json()["pages"]) == 1
    cross_page = f'/api/v1/editor/journal/pages/{two["pages"][0]["id"]}?journal_id={one["id"]}'
    assert client.patch(cross_page, headers=first, json=new_page).status_code == 404
    assert client.patch(f'/api/v1/editor/journal/pages/order?journal_id={one["id"]}', headers=first, json={"page_ids": [two["pages"][0]["id"]]}).status_code == 409
    second_data = {**payload, "email": "another-owner@example.com"}
    client.post("/api/v1/auth/register", json=second_data)
    token = re.search(r'token=([^\s]+)', setup[-1][2]).group(1)
    client.post("/api/v1/auth/verify-email", json={"token": token})
    other_token = client.post("/api/v1/auth/login", json={"email": second_data["email"], "password": payload["password"]}).json()["access_token"]
    other = auth_headers(client, other_token)
    assert client.get("/api/v1/editor/journals", headers=other).json() == []
    assert client.get(one_path, headers=other).status_code == 404
    assert client.post(f'/api/v1/editor/journal/pages?journal_id={one["id"]}', headers=other, json=new_page).status_code == 404
    other_journal = client.post("/api/v1/editor/journal", headers=other, json=body)
    assert other_journal.status_code == 201
    assert other_journal.json()["slug"] == one["slug"]
    assert other_journal.json()["editor_code"] != one["editor_code"]
    status_url = f'/api/v1/editor/journal/status?journal_id={one["id"]}'
    assert client.patch(status_url, json={"status": "Published"}).status_code == 401
    assert client.patch(status_url, headers=other, json={"status": "Published"}).status_code == 404
    assert client.patch(status_url, headers=first, json={"status": "Invalid"}).status_code == 422
    assert client.patch(status_url, headers=first, json={"status": "Published", "editor_id": 99}).status_code == 422
    assert client.patch("/api/v1/editor/journal/status", headers=first, json={"status": "Published"}).status_code == 409
    for status in ("Published", "NotPublished", "Draft"):
        updated = client.patch(status_url, headers=first, json={"status": status})
        assert updated.status_code == 200 and updated.json()["status"] == status
        assert client.get(one_path, headers=first).json()["status"] == status
        listed = client.get("/api/v1/editor/journals", headers=first).json()
        assert next(item for item in listed if item["id"] == one["id"])["status"] == status
        assert client.get(two_path, headers=first).json()["status"] == "Draft"
    with SessionLocal() as db:
        assert db.get(EditorJournal, one["id"]).status == "Draft"

    from app.config import settings
    from app.seed_admin import seed_admin
    monkeypatch.setattr(settings, "super_admin_email", "admin@example.com")
    monkeypatch.setattr(settings, "super_admin_password", "admin-password-1234")
    seed_admin()
    admin_token = client.post("/api/v1/auth/login", json={"email": "admin@example.com", "password": "admin-password-1234"}).json()["access_token"]
    admin = auth_headers(client, admin_token)
    with SessionLocal() as db:
        first_owner = db.scalar(select(Editor).where(Editor.email == payload["email"])).id
        db.get(EditorJournal, one["id"]).created_at = datetime(2026, 11, 1, 23, 59, 59, tzinfo=timezone.utc)
        db.get(EditorJournal, two["id"]).created_at = datetime(2026, 11, 2, 0, 0, tzinfo=timezone.utc)
        db.get(EditorJournal, other_journal.json()["id"]).created_at = datetime(2026, 11, 3, 12, 0, tzinfo=timezone.utc)
        db.commit()
    admin_list = "/api/v1/admin/editor-journals"
    assert client.get(admin_list).status_code == 401
    assert client.get(admin_list, headers=first).status_code == 403
    assert client.get("/api/v1/admin/journal-editors", headers=first).status_code == 403
    result = client.get(admin_list, headers=admin).json()
    assert result["total"] == 3 and len(result["items"]) == 3
    assert next(item for item in result["items"] if item["id"] == one["id"])["preview_path"] == client.get(one_path, headers=first).json()["preview_path"]
    assert next(item for item in result["items"] if item["id"] == two["id"])["preview_path"] == client.get(two_path, headers=first).json()["preview_path"]
    assert all("template_layout" not in row and "pages" not in row for row in result["items"])
    assert client.get(f"{admin_list}?editor_id={first_owner}", headers=admin).json()["total"] == 2
    assert client.get(f"{admin_list}?date_from=2026-11-01&date_to=2026-11-01", headers=admin).json()["total"] == 1
    combined = client.get(f"{admin_list}?editor_id={first_owner}&date_from=2026-11-02&date_to=2026-11-03", headers=admin).json()
    assert combined["total"] == 1 and combined["items"][0]["id"] == two["id"]
    page = client.get(f"{admin_list}?offset=1&limit=1", headers=admin).json()
    assert page["total"] == 3 and len(page["items"]) == 1
    assert client.get(f"{admin_list}?date_from=2026-11-03&date_to=2026-11-01", headers=admin).status_code == 422
    assert client.get(f"{admin_list}?editor_id=-1", headers=admin).status_code == 422
    assert len(client.get("/api/v1/admin/journal-editors", headers=admin).json()) == 2
    detail_path = f'{admin_list}/{one["id"]}'
    assert client.get(detail_path).status_code == 401
    assert client.get(detail_path, headers=first).status_code == 403
    before = client.get(one_path, headers=first).json()
    detail = client.get(detail_path, headers=admin).json()
    assert detail["editor_email"] == payload["email"]
    assert detail["template_layout"] == before["template_layout"] and detail["pages"] == before["pages"]
    assert client.patch(detail_path, headers=admin, json={"status": "Published"}).status_code == 405
    assert client.delete(detail_path, headers=admin).status_code == 405
    assert client.get(one_path, headers=first).json() == before
    assert client.get(f"{admin_list}/999999", headers=admin).status_code == 404
    with SessionLocal() as db:
        owner = db.get(Editor, first_owner)
        owner.is_active = False
        owner.is_verified = False
        db.commit()
    assert client.get(detail_path, headers=admin).status_code == 200
    assert client.get(f"{admin_list}?editor_id={first_owner}", headers=admin).json()["total"] == 2

    export_url = f'{admin_list}/{one["id"]}/export'
    assert client.get(export_url).status_code == 401
    assert client.get(export_url, headers=other).status_code == 403
    assert client.get(export_url, headers=admin).status_code == 409
    assert client.get(f"{admin_list}/999999/export", headers=admin).status_code == 404
    with SessionLocal() as db:
        target = db.get(EditorJournal, one["id"])
        target.status = "Published"
        db.commit()
        db.refresh(target)
        updated_before_export = target.updated_at
    exported = client.get(export_url, headers=admin)
    assert exported.status_code == 200
    assert exported.headers["content-type"] == "application/zip"
    assert 'attachment; filename="first-journal-website.zip"' == exported.headers["content-disposition"]
    assert exported.headers["cache-control"] == "no-store"
    from io import BytesIO
    from zipfile import ZipFile
    with ZipFile(BytesIO(exported.content)) as archive:
        assert "first-journal/index.html" in archive.namelist()
        assert "first-journal/assets/styles.css" in archive.namelist()
        assert ("mailto:" + payload["email"]).encode() in archive.read("first-journal/index.html")
    with SessionLocal() as db:
        assert db.get(EditorJournal, one["id"]).updated_at == updated_before_export

    # Published feeds are scoped to both editor code and journal slug.
    with SessionLocal() as db:
        owner = db.get(Editor, first_owner)
        owner.is_active = True
        owner.is_verified = True
        db.get(EditorJournal, two["id"]).status = "Published"
        db.get(EditorJournal, other_journal.json()["id"]).status = "Published"
        db.commit()
    feed_base = f'/api/v1/public/journals/{one["editor_code"]}/{one["slug"]}'
    metadata=client.get(feed_base+"/info")
    assert metadata.status_code==200
    assert metadata.json()["editor_code"]==one["editor_code"]
    assert metadata.json()["journal_slug"]==one["slug"]
    assert set(metadata.json())=={"editor_code","journal_slug","journal_info","editor_email","updated_at"}
    assert client.get(feed_base + "/current").json()["issue"] is None
    assert client.get(feed_base + "/archives").json()["items"] == []
    now = datetime.now(timezone.utc)
    with SessionLocal() as db:
        latest = JournalIssue(journal_id=one["id"], title="Latest issue", volume="1", number="3", is_published=True, published_at=now - timedelta(days=1))
        old = JournalIssue(journal_id=one["id"], title="Older issue", is_published=True, is_archived=True, published_at=now - timedelta(days=7))
        oldest = JournalIssue(journal_id=one["id"], title="Oldest issue", is_published=True, is_archived=True, published_at=now - timedelta(days=14))
        future = JournalIssue(journal_id=one["id"], title="Future issue", is_published=True, published_at=now + timedelta(days=1))
        draft = JournalIssue(journal_id=one["id"], title="Draft issue", is_published=False, published_at=now)
        other_same = JournalIssue(journal_id=two["id"], title="Same editor different journal", is_published=True, published_at=now)
        other_owner = JournalIssue(journal_id=other_journal.json()["id"], title="Another editor issue", is_published=True, published_at=now)
        db.add_all([latest, old, oldest, future, draft, other_same, other_owner])
        db.flush()
        db.add_all([
            JournalArticle(journal_id=one["id"], issue_id=latest.id, title="Published article", authors=["Author One"], abstract="Research abstract", article_url="https://example.com/article", is_published=True),
            JournalArticle(journal_id=one["id"], issue_id=latest.id, title="Hidden draft article", is_published=False),
            JournalArticle(journal_id=one["id"], issue_id=latest.id, title="Unsafe link article", article_url="javascript:bad()", is_published=True),
            JournalArticle(journal_id=one["id"], issue_id=old.id, title="Archived article", is_published=True),
            JournalArticle(journal_id=two["id"], issue_id=other_same.id, title="Other journal article", is_published=True)])
        db.commit()
    current = client.get(feed_base + "/current")
    assert current.status_code == 200
    data = current.json()
    assert data["editor_code"] == one["editor_code"] and data["journal_slug"] == one["slug"]
    assert data["issue"]["title"] == "Latest issue"
    assert [article["title"] for article in data["issue"]["articles"]] == ["Published article", "Unsafe link article"]
    assert data["issue"]["articles"][0]["article_url"] == "https://example.com/article"
    assert data["issue"]["articles"][1]["article_url"] is None
    assert "Hidden draft article" not in current.text and "Other journal article" not in current.text
    assert payload["email"] not in current.text
    archives = client.get(feed_base + "/archives?limit=1&offset=0").json()
    assert archives["total"] == 2 and len(archives["items"]) == 1
    assert archives["items"][0]["title"] == "Older issue"
    assert archives["items"][0]["articles"][0]["title"] == "Archived article"
    assert client.get(feed_base + "/archives?limit=1&offset=1").json()["items"][0]["title"] == "Oldest issue"
    assert client.get(feed_base + "/archives?limit=0").status_code == 422
    assert client.get('/api/v1/public/journals/invalid/first-journal/current').status_code == 422
    assert client.get(f'/api/v1/public/journals/{other_journal.json()["editor_code"]}/{two["slug"]}/current').status_code == 404
    assert client.get(f'/api/v1/public/journals/{two["editor_code"]}/{two["slug"]}/current').json()["issue"]["title"] == "Same editor different journal"
    with SessionLocal() as db:
        db.get(EditorJournal, one["id"]).status = "NotPublished"
        db.commit()
    assert client.get(feed_base + "/current").status_code == 404
    assert client.get(feed_base + "/archives").status_code == 404
    assert client.get(feed_base + "/info").status_code == 404


def test_editor_article_pdf_and_single_volume_management(client, setup, monkeypatch):
    import base64
    from app.config import settings
    from app.seed_admin import seed_admin
    headers = auth_headers(client, authenticate(client, setup))
    template_id = client.get("/api/v1/templates", headers=headers).json()[0]["id"]
    journal_body = {"name": "Article Management", "template_id": template_id, "new_pages": [{"title": "Home", "slug": "home", "content_html": "<p>Home</p>"}]}
    journal = client.post("/api/v1/editor/journal", headers=headers, json=journal_body).json()
    second = client.post("/api/v1/editor/journal", headers=headers, json={**journal_body, "name": "Other Journal"}).json()
    suffix = f'?journal_id={journal["id"]}'
    order_url = "/api/v1/editor/journal/pages/order" + suffix
    selected_page = journal["pages"][0]["id"]
    combined_order = ["submission", "archives", selected_page, "current"]
    reordered = client.patch(order_url, headers=headers, json={"page_ids": combined_order})
    assert reordered.status_code == 200
    assert reordered.json()["menu_order"] == ["submission", "archives", "home", "current"]
    public_order = client.get(f'/api/v1/public/journals/{journal["editor_code"]}/{journal["slug"]}',headers=headers).json()
    assert public_order["menu_order"] == ["submission", "archives", "home", "current"]
    assert client.patch(order_url, headers=headers, json={"page_ids": [selected_page, "current"]}).status_code == 409
    assert client.get(f'/api/v1/editor/journal?journal_id={second["id"]}', headers=headers).json()["menu_order"] == ["home", "current", "archives", "submission"]
    info_url = "/api/v1/editor/journal/info" + suffix
    info = {"editor_in_chief": "Narjess ALOUI", "frequency": "Four iss./ year", "final_decision": "75 days", "acceptance_rate": "15%", "plagiarism": "<10%", "language": "English", "review_process": "Single-blind", "open_access": "Yes", "copyright": "CC-BY 4.0", "eissn": "2323-5233"}
    assert client.patch(info_url, json=info).status_code == 401
    saved = client.patch(info_url, headers=headers, json=info)
    assert saved.status_code == 200 and saved.json()["journal_info"] == info
    public_details = client.get(f'/api/v1/public/journals/{journal["editor_code"]}/{journal["slug"]}',headers=headers).json()
    assert public_details["journal_info"] == info
    assert public_details["template_layout"]["show_journal_info"] is True
    assert client.get("/api/v1/editor/journal" + suffix, headers=headers).json()["journal_info"] == info
    assert client.get(f'/api/v1/editor/journal?journal_id={second["id"]}', headers=headers).json()["journal_info"]["editor_in_chief"] == ""
    assert client.patch(info_url, headers=headers, json={"language": "x" * 151}).status_code == 422
    assert client.patch(info_url, headers=headers, json={"unknown": "value"}).status_code == 422

    articles = "/api/v1/editor/articles"
    volumes = "/api/v1/editor/volumes"
    pdf = b"%PDF-1.4\n1 0 obj<</Type/Catalog>>endobj\ntrailer<</Root 1 0 R>>\n%%EOF"
    data = {"how_to_cite": "Author One & Author Two (2026). Research heading. Journal 1(1).", "title": "Research heading", "authors": ["Author One", "Author Two"], "abstract": "Abstract text", "is_published": True, "pdf_base64": base64.b64encode(pdf).decode()}
    assert client.get(articles + suffix).status_code == 401
    assert client.post(articles + suffix, headers=headers, json={k: v for k, v in data.items() if k != "pdf_base64"}).status_code == 422
    assert client.post(articles + suffix, headers=headers, json={**data, "pdf_base64": "invalid"}).status_code == 422
    assert client.post(articles + suffix, headers=headers, json={**data, "pdf_base64": base64.b64encode(b"not a PDF").decode()}).status_code == 422
    assert client.post(articles + suffix, headers=headers, json={**data, "authors": [" "]}).status_code == 422
    assert client.post(articles + suffix, headers=headers, json={**data, "editor_id": 99}).status_code == 422
    first = client.post(articles + suffix, headers=headers, json=data)
    assert first.status_code == 201
    first = first.json()
    assert first["authors"] == ["Author One", "Author Two"] and first["volume_id"] is None
    assert first["has_pdf"] and first["pdf_size"] == len(pdf)
    assert first["how_to_cite"] == data["how_to_cite"]
    citation_url=f'{articles}/{first["id"]}{suffix}'
    omitted=client.patch(citation_url,headers=headers,json={key:value for key,value in data.items() if key not in {"how_to_cite","pdf_base64"}})
    assert omitted.status_code==200 and omitted.json()["how_to_cite"]==data["how_to_cite"]
    assert client.patch(citation_url,headers=headers,json={**data,"how_to_cite":"x"*2001}).status_code==422
    assert client.patch(citation_url,headers=headers,json={**data,"how_to_cite":""}).json()["how_to_cite"]==""
    assert client.patch(citation_url,headers=headers,json=data).json()["how_to_cite"]==data["how_to_cite"]

    assert first["journal_name"] == "Article Management" and first["created_at"]
    another_article = client.post(f'{articles}?journal_id={second["id"]}', headers=headers, json={**data, "title": "Other journal research"}).json()

    assert "pdf_content" not in first
    second_article = client.post(articles + suffix, headers=headers, json={**data, "title": "Another article", "is_published": False}).json()
    assert client.get(f'{articles}/{first["id"]}/pdf{suffix}', headers=headers).content == pdf
    viewed = client.get(f'{articles}/{first["id"]}/pdf{suffix}&inline=true', headers=headers)
    assert viewed.status_code == 200 and viewed.content == pdf
    assert viewed.headers["content-disposition"].startswith("inline;")
    assert client.get(f'{articles}/{first["id"]}/pdf{suffix}', headers=headers).headers["content-disposition"].startswith("attachment;")
    assert client.get(f'{articles}/{first["id"]}/pdf').status_code in (401, 422)
    assert client.get(f'{articles}/{first["id"]}/pdf?journal_id={second["id"]}', headers=headers).status_code == 404
    edited = {key: value for key, value in data.items() if key != "pdf_base64"}
    edited["title"] = "Updated heading"
    assert client.patch(f'{articles}/{first["id"]}{suffix}', headers=headers, json=edited).status_code == 200
    assert client.get(f'{articles}/{first["id"]}/pdf{suffix}', headers=headers).content == pdf
    volume_data = {"title": "Volume one", "volume": "1", "number": "1", "is_published": True, "article_ids": [first["id"], second_article["id"]]}
    volume = client.post(volumes + suffix, headers=headers, json=volume_data)
    assert volume.status_code == 201
    volume = volume.json()
    assert volume["article_ids"] == [first["id"], second_article["id"]]
    another_volume = client.post(f'{volumes}?journal_id={second["id"]}', headers=headers, json={**volume_data, "title": "Other journal volume", "article_ids": [another_article["id"]]}).json()
    with SessionLocal() as db:
        db.get(JournalArticle, first["id"]).created_at = datetime(2026, 11, 1, 23, 59, 59, tzinfo=timezone.utc)
        db.get(JournalArticle, second_article["id"]).created_at = datetime(2026, 11, 2, 0, 0, tzinfo=timezone.utc)
        db.get(JournalArticle, another_article["id"]).created_at = datetime(2026, 11, 3, 12, 0, tzinfo=timezone.utc)
        db.get(JournalIssue, volume["id"]).created_at = datetime(2026, 11, 1, 23, 59, 59, tzinfo=timezone.utc)
        db.get(JournalIssue, another_volume["id"]).created_at = datetime(2026, 11, 2, 0, 0, tzinfo=timezone.utc)
        db.commit()
    assert len(client.get(articles, headers=headers).json()) == 3
    assert len(client.get(volumes, headers=headers).json()) == 2
    assert len(client.get(articles + suffix, headers=headers).json()) == 2
    assert client.get(articles + "?date_from=2026-11-01&date_to=2026-11-01", headers=headers).json()[0]["id"] == first["id"]
    filtered_articles = client.get(articles + suffix + "&date_from=2026-11-02&date_to=2026-11-03", headers=headers).json()
    assert [item["id"] for item in filtered_articles] == [second_article["id"]]
    assert [item["id"] for item in client.get(volumes + "?date_from=2026-11-01&date_to=2026-11-01", headers=headers).json()] == [volume["id"]]
    assert client.get(volumes + suffix + "&date_from=2026-11-02&date_to=2026-11-03", headers=headers).json() == []
    assert client.get(articles + "?date_from=2026-11-03&date_to=2026-11-01", headers=headers).status_code == 422
    assert client.get(volumes + "?date_from=2026-11-03&date_to=2026-11-01", headers=headers).status_code == 422
    assert client.get(articles + "?journal_id=-1", headers=headers).status_code == 422
    assert client.patch(f'{volumes}/{volume["id"]}?journal_id={second["id"]}', headers=headers, json=volume_data).status_code == 404

    assert client.post(volumes + suffix, headers=headers, json={**volume_data, "title": "Conflicting", "volume": "2"}).status_code == 409
    assert len(client.get(volumes + suffix, headers=headers).json()) == 1
    assert client.post(f'{volumes}?journal_id={second["id"]}', headers=headers, json=volume_data).status_code == 404
    code, slug = journal["editor_code"], journal["slug"]
    public_pdf = f'/api/v1/public/journals/{code}/{slug}/articles/{first["id"]}/pdf'
    assert client.get(public_pdf).status_code == 404
    client.patch(f'/api/v1/editor/journal/status?journal_id={journal["id"]}', headers=headers, json={"status": "Published"})
    assert client.get(public_pdf).status_code == 200 and client.get(public_pdf).content == pdf
    assert client.get(f'/api/v1/public/journals/{code}/{slug}/articles/{second_article["id"]}/pdf').status_code == 404
    current = client.get(f'/api/v1/public/journals/{code}/{slug}/current').json()
    assert current["issue"]["title"] == "Volume one"
    assert len(current["issue"]["articles"]) == 1
    assert "/api/journal/article-pdf?" in current["issue"]["articles"][0]["article_url"]
    assert current["issue"]["articles"][0]["how_to_cite"]==data["how_to_cite"]
    archived = client.patch(f'{volumes}/{volume["id"]}{suffix}', headers=headers, json={**volume_data, "is_archived": True})
    assert archived.status_code == 200 and archived.json()["is_archived"] is True
    assert client.get(f'/api/v1/public/journals/{code}/{slug}/current').json()["issue"] is None
    archive_feed = client.get(f'/api/v1/public/journals/{code}/{slug}/archives').json()
    assert archive_feed["items"][0]["id"] == volume["id"]
    assert len(archive_feed["items"][0]["articles"]) == 1
    assert client.get(public_pdf).status_code == 200
    for status in ("UnPublished", "Published", "Archived"):
        changed = client.patch(f'{volumes}/{volume["id"]}{suffix}', headers=headers, json={**volume_data, "status": status})
        assert changed.status_code == 200 and changed.json()["status"] == status
        assert changed.json()["is_published"] == (status != "UnPublished")
        assert changed.json()["is_archived"] == (status == "Archived")
        feed = client.get(f'/api/v1/public/journals/{code}/{slug}/current').json()
        history = client.get(f'/api/v1/public/journals/{code}/{slug}/archives').json()
        assert (feed["issue"] is not None) == (status == "Published")
        assert bool(history["items"]) == (status == "Archived")
        assert client.get(public_pdf).status_code == (404 if status == "UnPublished" else 200)
    assert client.patch(f'{volumes}/{volume["id"]}{suffix}', headers=headers, json={**volume_data, "status": "Invalid"}).status_code == 422
    # Remove an article, then assign it to another volume. Membership cannot overlap.
    assert client.patch(f'{volumes}/{volume["id"]}{suffix}', headers=headers, json={**volume_data, "article_ids": [second_article["id"]]}).status_code == 200
    another = client.post(volumes + suffix, headers=headers, json={**volume_data, "title": "Volume two", "volume": "2", "article_ids": [first["id"]]}).json()
    assert client.patch(f'{volumes}/{volume["id"]}{suffix}', headers=headers, json=volume_data).status_code == 409
    assert client.delete(f'{volumes}/{another["id"]}{suffix}', headers=headers).status_code == 204
    listed = client.get(articles + suffix, headers=headers).json()
    assert next(article for article in listed if article["id"] == first["id"])["volume_id"] is None
    assert client.get(f'{articles}/{first["id"]}/pdf{suffix}', headers=headers).content == pdf
    # Another editor cannot inspect or modify this journal's articles/volumes.
    other_data = {**payload, "email": "publication-other@example.com"}
    client.post("/api/v1/auth/register", json=other_data)
    verification = re.search(r'token=([^\s]+)', setup[-1][2]).group(1)
    client.post("/api/v1/auth/verify-email", json={"token": verification})
    token = client.post("/api/v1/auth/login", json={"email": other_data["email"], "password": payload["password"]}).json()["access_token"]
    other = auth_headers(client, token)
    assert client.patch(info_url, headers=other, json=info).status_code == 404

    assert client.get(articles + suffix, headers=other).status_code == 404
    assert client.get(articles, headers=other).json() == []
    assert client.get(volumes, headers=other).json() == []

    assert client.post(volumes + suffix, headers=other, json=volume_data).status_code == 404
    assert client.patch(f'{articles}/{first["id"]}{suffix}', headers=other, json=edited).status_code == 404
    assert client.get(f'{articles}/{first["id"]}/pdf{suffix}', headers=other).status_code == 404
    monkeypatch.setattr(settings, "super_admin_email", "admin@example.com")
    monkeypatch.setattr(settings, "super_admin_password", "admin-password-1234")
    seed_admin()
    admin_token = client.post("/api/v1/auth/login", json={"email": "admin@example.com", "password": "admin-password-1234"}).json()["access_token"]
    admin = auth_headers(client, admin_token)
    assert client.post(articles + suffix, headers=admin, json=data).status_code == 403
    assert client.delete(f'{articles}/{second_article["id"]}{suffix}', headers=headers).status_code == 204
    assert client.get(volumes + suffix, headers=headers).json()[0]["article_ids"] == []
    assert client.delete(f'{volumes}/{volume["id"]}{suffix}', headers=headers).status_code == 204
    with SessionLocal() as db:
        owner_id = db.scalar(select(Editor.id).where(Editor.email == payload["email"]))
    delete_url = "/api/v1/editor/journal" + suffix
    assert client.delete(delete_url).status_code == 401
    assert client.delete(delete_url, headers=other).status_code == 404
    assert client.delete(delete_url, headers=admin).status_code == 403
    replacement = client.post(volumes + suffix, headers=headers, json={**volume_data, "article_ids": [first["id"]]})
    assert replacement.status_code == 201
    removed = client.delete(delete_url, headers=headers)
    assert removed.status_code == 204 and not removed.content
    assert client.delete(delete_url, headers=headers).status_code == 404
    assert client.get(f'/api/v1/editor/journal?journal_id={second["id"]}', headers=headers).status_code == 200
    assert client.get("/api/v1/templates", headers=headers).json()
    with SessionLocal() as db:
        from app.models import EditorJournalPage
        assert db.get(EditorJournal, journal["id"]) is None
        assert not db.scalars(select(JournalArticle).where(JournalArticle.journal_id == journal["id"])).all()
        assert not db.scalars(select(JournalIssue).where(JournalIssue.journal_id == journal["id"])).all()
        assert not db.scalars(select(EditorJournalPage).where(EditorJournalPage.journal_id == journal["id"])).all()
    assert client.delete(f"/api/v1/admin/users/{owner_id}", headers=admin).status_code == 204

def test_visitor_manuscript_submission_captcha_and_editor_delivery(client, setup, monkeypatch):
    import base64
    from app import submission_routes
    from app.models import ManuscriptSubmission, SubmissionCaptcha
    headers = auth_headers(client, authenticate(client, setup))
    template_id = client.get("/api/v1/templates", headers=headers).json()[0]["id"]
    body = {"name": "Submission Journal", "template_id": template_id, "new_pages": [{"title": "Home", "slug": "home", "content_html": "<p>Home</p>"}]}
    journal = client.post("/api/v1/editor/journal", headers=headers, json=body).json()
    other = client.post("/api/v1/editor/journal", headers=headers, json={**body,"name":"Other Submission Journal"}).json()
    base = f'/api/v1/public/journals/{journal["editor_code"]}/{journal["slug"]}/submission'
    assert client.get(base + "/captcha").status_code == 404
    for item in (journal,other):
        client.patch(f'/api/v1/editor/journal/status?journal_id={item["id"]}',headers=headers,json={"status":"Published"})
    def challenge():
        response = client.get(base + "/captcha")
        assert response.status_code == 200
        data = response.json()
        svg = base64.b64decode(data["image"].split(",",1)[1]).decode()
        answer = "".join(re.findall(r">([A-Z0-9])</text>",svg))
        assert len(answer) == 6 and "answer" not in data
        return data["captcha_id"],answer
    sent=[]
    monkeypatch.setattr(submission_routes,"send_manuscript_email",lambda to,name,record: sent.append((to,name,record.title,record.pdf_content)))
    pdf=b"%PDF-1.4\n1 0 obj<</Type/Catalog>>endobj\n%%EOF"
    token,answer=challenge()
    payload_data={"how_to_cite":"Visitor Name (2026). New research.","full_name":"Visitor Name","email":"visitor@example.com","title":"New research","authors":"Visitor Name, Other Author","abstract":"An original research manuscript for consideration.","pdf_base64":base64.b64encode(pdf).decode(),"captcha_id":token,"captcha_answer":"WRONG"}
    assert client.post(base,json=payload_data).status_code == 422
    assert client.post(base,json={**payload_data,"captcha_answer":answer}).status_code == 422
    token,answer=challenge()
    payload_data.update(captcha_id=token,captcha_answer=answer)
    other_base=f'/api/v1/public/journals/{other["editor_code"]}/{other["slug"]}/submission'
    assert client.post(other_base,json=payload_data).status_code == 422
    assert client.post(base,json={**payload_data,"pdf_base64":base64.b64encode(b"bad").decode()}).status_code == 422
    response=client.post(base,json=payload_data)
    assert response.status_code == 201
    assert response.json()["reference"]
    assert sent == [(payload["email"],journal["name"],"New research",pdf)]
    assert client.post(base,json=payload_data).status_code == 422
    with SessionLocal() as db:
        saved=db.get(JournalArticle,response.json()["reference"])
        assert saved.journal_id == journal["id"] and saved.notification_sent
        assert saved.submitter_email == "visitor@example.com" and saved.pdf_content == pdf
        assert saved.status == "Submitted" and not saved.is_published
        assert saved.pdf_size == len(pdf) and saved.submitter_name == "Visitor Name"
        assert saved.how_to_cite == payload_data["how_to_cite"]
        assert not db.scalars(select(ManuscriptSubmission).where(ManuscriptSubmission.journal_id==journal["id"])).all()
    listing=client.get("/api/v1/editor/articles",headers=headers).json()
    assert len(listing)==1 and listing[0]["status"]=="Submitted"
    assert listing[0]["submitter_email"]=="visitor@example.com"
    article_id=response.json()["reference"]
    pdf_url=f'/api/v1/editor/articles/{article_id}/pdf?journal_id={journal["id"]}&inline=true'
    assert client.get(pdf_url).status_code==401
    assert client.get(pdf_url,headers=headers).content==pdf
    volume=client.post(f'/api/v1/editor/volumes?journal_id={journal["id"]}',headers=headers,json={"title":"Current volume","volume":"1","status":"Published","article_ids":[article_id]}).json()
    feed_url=base.removesuffix("/submission")+"/current"
    assert client.get(feed_url).json()["issue"]["articles"]==[]
    article_data={"title":"New research","authors":["Visitor Name","Other Author"],"abstract":payload_data["abstract"],"status":"Published"}
    changed=client.patch(f'/api/v1/editor/articles/{article_id}?journal_id={journal["id"]}',headers=headers,json=article_data)
    assert changed.status_code==200 and changed.json()["status"]=="Published" and changed.json()["is_published"]
    assert len(client.get(feed_url).json()["issue"]["articles"])==1
    # A failed notification never discards the manuscript.
    def fail_mail(*args):
        raise OSError("SMTP unavailable")
    monkeypatch.setattr(submission_routes,"send_manuscript_email",fail_mail)
    token,answer=challenge()
    pending=client.post(base,json={**payload_data,"captcha_id":token,"captcha_answer":answer})
    assert pending.status_code == 201 and "pending" in pending.json()["message"]
    with SessionLocal() as db:
        assert not db.get(JournalArticle,pending.json()["reference"]).notification_sent
    # Owner deletion also removes private visitor manuscripts.
    assert client.delete(f'/api/v1/editor/journal?journal_id={journal["id"]}',headers=headers).status_code == 204
    with SessionLocal() as db:
        assert not db.scalars(select(ManuscriptSubmission).where(ManuscriptSubmission.journal_id==journal["id"])).all()

    with SessionLocal() as db:
        assert not db.scalars(select(JournalArticle).where(JournalArticle.journal_id==journal["id"])).all()

def test_mutations_require_gateway_valid_token_and_matching_editor_code(client, setup):
    token=authenticate(client,setup)
    headers=auth_headers(client,token)
    body={k:payload[k] for k in ("first_name","last_name","phone","gender","email")}
    url="/api/v1/editor/profile"
    assert client.patch(url,headers={**headers,"X-Internal-API-Key":""},json=body).status_code==403
    assert client.patch(url,headers={**headers,"X-Internal-API-Key":"wrong"},json=body).status_code==403
    assert client.patch(url,headers={"Authorization":f"Bearer {token}"},json=body).status_code==422
    assert client.patch(url,headers={**headers,"X-Editor-Code":"zzzzzzzz"},json=body).status_code==403
    assert client.patch(url+"?editor_code=zzzzzzzz",headers=headers,json=body).status_code==403
    assert client.patch(url,headers={**headers,"Authorization":"Bearer invalid-token"},json=body).status_code==401
    assert client.patch(url,headers={"X-Editor-Code":headers["X-Editor-Code"]},json=body).status_code==401
    assert client.get("/api/v1/editor/articles").status_code==401
    assert client.get("/api/v1/editor/articles?editor_code=zzzzzzzz",headers=headers).status_code==403
    assert client.patch(url,headers=headers,json=body).status_code==200
    # Expired credentials do not become valid just because the editor code matches.
    with SessionLocal() as db:
        db.get(Session,digest(token)).expires_at=datetime.now(timezone.utc)-timedelta(seconds=1)
        db.commit()
    assert client.patch(url,headers=headers,json=body).status_code==401


def test_other_editor_cannot_read_draft_preview_even_with_known_code(client, setup):
    headers=auth_headers(client,authenticate(client,setup))
    template=client.get("/api/v1/templates",headers=headers).json()[0]["id"]
    journal=client.post("/api/v1/editor/journal",headers=headers,json={"name":"Private draft","template_id":template,"new_pages":[{"title":"Home","slug":"home","content_html":"<p>Private content</p>"}]}).json()
    url=f'/api/v1/public/journals/{journal["editor_code"]}/{journal["slug"]}'
    assert client.get(url).status_code==404
    assert client.get(url,headers=headers).status_code==200
    other_data={**payload,"email":"second-preview@example.com"}
    client.post("/api/v1/auth/register",json=other_data)
    code=re.search(r'token=([^\s]+)',setup[-1][2]).group(1)
    client.post("/api/v1/auth/verify-email",json={"token":code})
    token=client.post("/api/v1/auth/login",json={"email":other_data["email"],"password":payload["password"]}).json()["access_token"]
    other=auth_headers(client,token)
    assert client.get(url,headers=other).status_code==404
    assert client.patch(f'/api/v1/editor/journal/status?journal_id={journal["id"]}',headers=headers,json={"status":"Published"}).status_code==200
    assert client.get(url).status_code==200

def test_article_edit_can_assign_move_and_remove_same_journal_volume(client,setup):
    import base64
    headers=auth_headers(client,authenticate(client,setup))
    template=client.get("/api/v1/templates",headers=headers).json()[0]["id"]
    body={"name":"Volume assignment","template_id":template,"new_pages":[{"title":"Home","slug":"home","content_html":"<p>Home</p>"}]}
    journal=client.post("/api/v1/editor/journal",headers=headers,json=body).json()
    other=client.post("/api/v1/editor/journal",headers=headers,json={**body,"name":"Another journal"}).json()
    suffix=f'?journal_id={journal["id"]}'
    def volume(title,journal_id):
        response=client.post(f'/api/v1/editor/volumes?journal_id={journal_id}',headers=headers,json={"title":title,"volume":title})
        assert response.status_code==201
        return response.json()
    first=volume("One",journal["id"]); second=volume("Two",journal["id"]); foreign=volume("Foreign",other["id"])
    data={"title":"Article","authors":["Author"],"status":"UnPublished","abstract":"Research abstract"}
    pdf=base64.b64encode(b"%PDF-1.4\n1 0 obj<</Type/Catalog>>endobj\n%%EOF").decode()
    article=client.post("/api/v1/editor/articles"+suffix,headers=headers,json={**data,"pdf_base64":pdf,"volume_id":first["id"]}).json()
    assert article["volume_id"]==first["id"]
    existing=client.post("/api/v1/editor/articles"+suffix,headers=headers,json={**data,"title":"Already assigned","pdf_base64":pdf,"volume_id":second["id"]}).json()
    url=f'/api/v1/editor/articles/{article["id"]}'+suffix
    moved=client.patch(url,headers=headers,json={**data,"volume_id":second["id"]})
    assert moved.status_code==200 and moved.json()["volume_id"]==second["id"]
    listed=client.get("/api/v1/editor/volumes"+suffix,headers=headers).json()
    assert next(item for item in listed if item["id"]==first["id"])["article_ids"]==[]
    assert next(item for item in listed if item["id"]==second["id"])["article_ids"]==[existing["id"],article["id"]]
    assert client.patch(url,headers=headers,json=data).json()["volume_id"]==second["id"]
    assert client.patch(url,headers=headers,json={**data,"volume_id":foreign["id"]}).status_code==404
    for value in (0,-1,True,"1"):
        assert client.patch(url,headers=headers,json={**data,"volume_id":value}).status_code==422
    assert client.patch(url,headers=headers,json={**data,"volume_id":None}).json()["volume_id"] is None
    assert client.patch(url,headers=headers,json={**data,"volume_id":first["id"]}).json()["volume_id"]==first["id"]
