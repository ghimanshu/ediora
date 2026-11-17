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
from app.models import Editor, Verification, Session, Contact, WebsiteTemplateSelection, WebPage, EditorJournal, EditorJournalPage
from app import routes
from app.security import digest

@pytest.fixture(autouse=True)
def setup(monkeypatch):
    command.upgrade(Config('alembic.ini'), 'head')
    with SessionLocal() as db:
        for model in (EditorJournalPage, EditorJournal, WebPage, WebsiteTemplateSelection, Session, Verification, Contact, Editor):
            db.execute(delete(model))
        db.commit()
    messages = []
    monkeypatch.setattr(routes, 'send_email', lambda to, subject, body: messages.append((to, subject, body)))
    yield messages

@pytest.fixture
def client():
    with TestClient(app) as c:
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

def test_full_auth_flow(client, setup):
    token = register(client, setup)
    credentials = {k: payload[k] for k in ('email', 'password')}
    assert client.post('/api/v1/auth/login', json=credentials).status_code == 403
    assert client.post('/api/v1/auth/verify-email', json={'token': token}).status_code == 200
    assert client.post('/api/v1/auth/verify-email', json={'token': token}).status_code == 400
    session = client.post('/api/v1/auth/login', json=credentials).json()['access_token']
    headers = {'Authorization': f'Bearer {session}'}
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
    assert client.get('/api/v1/auth/me', headers={'Authorization': f'Bearer {token}'}).status_code == 401

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
    user_headers = {"Authorization": f"Bearer {user_token}"}
    assert client.get("/api/v1/admin/users").status_code == 401
    assert client.get("/api/v1/admin/users", headers=user_headers).status_code == 403
    token = client.post("/api/v1/auth/login", json={"email": "admin@example.com", "password": "admin-password-1234"}).json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
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
    admin = {"Authorization": f"Bearer {token}"}
    user = {"Authorization": f"Bearer {authenticate(client, setup)}"}
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
    admin = {"Authorization": f"Bearer {token}"}
    user = {"Authorization": f"Bearer {authenticate(client, setup)}"}
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
    headers = {"Authorization": f"Bearer {token}"}
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
    admin = {"Authorization": f"Bearer {admin_token}"}
    first = {"Authorization": f"Bearer {authenticate(client, setup)}"}
    second_data = {**payload, "email": "second-editor@example.com"}
    assert client.post("/api/v1/auth/register", json=second_data).status_code == 202
    verification = re.search(r'token=([^\s]+)', setup[-1][2]).group(1)
    client.post("/api/v1/auth/verify-email", json={"token": verification})
    second_token = client.post("/api/v1/auth/login", json={"email": second_data["email"], "password": payload["password"]}).json()["access_token"]
    second = {"Authorization": f"Bearer {second_token}"}
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
    assert [page["slug"] for page in client.get(public_url).json()["pages"]] == [page["slug"] for page in reordered.json()["pages"]]
    assert client.get("/api/v1/editor/journal", headers=second).json()["pages"] == two["pages"]
    with SessionLocal() as db:
        editor_id = db.scalar(select(Editor).where(Editor.email == payload["email"])).id
    assert client.delete(f"/api/v1/admin/users/{editor_id}", headers=admin).status_code == 204
    with SessionLocal() as db:
        assert db.get(EditorJournal, one["id"]) is None
        assert db.scalars(select(EditorJournalPage).where(EditorJournalPage.journal_id == one["id"])).all() == []
        assert db.get(EditorJournal, two["id"]) is not None


def test_journal_with_only_new_pages_and_invalid_drafts(client, setup):
    headers = {"Authorization": f"Bearer {authenticate(client, setup)}"}
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
    public_response = client.get(public_url)
    assert public_response.status_code == 200
    public = public_response.json()
    assert public["name"] == "Custom Journal"
    assert public["template_layout"] == journal["template_layout"]
    assert public["pages"][0]["content_html"] == "<h2>My research</h2><p>Private article</p>"
    assert set(public) == {"name", "slug", "editor_code", "template_layout", "pages"}
    assert set(public["pages"][0]) == {"title", "slug", "content_html"}
    assert payload["email"] not in public_response.text
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
    assert client.get(public_url).json()["pages"][0]["content_html"] == "<p>Updated private text</p>"
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
