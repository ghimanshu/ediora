from io import BytesIO
from types import SimpleNamespace
from zipfile import ZipFile
from html.parser import HTMLParser
from app.website_export import build_website_zip

class Links(HTMLParser):
    def __init__(self):
        super().__init__()
        self.values = []
    def handle_starttag(self, tag, attrs):
        for name, value in attrs:
            if name in {"href", "src"}:
                self.values.append(value)

def test_offline_zip_files_links_and_saved_design():
    sections = [{"type": kind, "title": "Hidden menu heading" if kind == "menu" else kind.title(), "content": "Saved text", "background_color": "#123ABC", "text_color": "#FFFFFF"} for kind in ("header", "menu", "content", "footer")]
    journal = SimpleNamespace(journal_info={}, slug="my-journal", name="My <Journal>", template_layout={"menu_position": "right", "sections": sections})
    pages = [SimpleNamespace(title="About", slug="about", content_html='<h2>About our work</h2><a href="/ab12cd34/my-journal/home">Home</a><a href="/current">Current</a><a href="https://example.com/reference">Reference</a>'),
             SimpleNamespace(title="Home", slug="home", content_html='<p onclick="bad()">Welcome</p><script>bad()</script>'),
             SimpleNamespace(title="Index", slug="index", content_html="<p>Index page</p>"),
             SimpleNamespace(title="Index One", slug="index-1", content_html="<p>Another page</p>")]
    data = build_website_zip(journal, pages, "ab12cd34")
    with ZipFile(BytesIO(data)) as archive:
        names = archive.namelist()
        assert len(names) == len(set(names))
        assert "my-journal/index.html" in names
        assert "my-journal/about.html" in names
        assert "my-journal/current.html" in names and "my-journal/archives.html" in names
        assert "my-journal/assets/styles.css" in names
        assert all(name.startswith("my-journal/") and ".." not in name for name in names)
        css = archive.read("my-journal/assets/styles.css").decode()
        assert "#123abc" in css and "#ffffff" in css
        assert "grid-template-columns" in css and "@media" in css
        home = archive.read("my-journal/index.html").decode()
        assert "Welcome" in home and "onclick" not in home and "<script>bad()" not in home
        assert "My &lt;Journal&gt;" in home
        assert "Hidden menu heading" not in home
        about = archive.read("my-journal/about.html").decode()
        assert '<a href="index.html"' in about
        assert '<a href="current.html"' in about
        assert '<a href="https://example.com/reference"' in about
        assert about.index('href="about.html"') < about.index('href="index.html"')
        for name in names:
            if name.endswith(".html"):
                html = archive.read(name).decode()
                assert "_next/" not in html and "/api/" not in html
                parser = Links()
                parser.feed(html)
                for href in parser.values:
                    if href and not href.startswith(("https://", "http://", "mailto:", "tel:", "#")):
                        assert "my-journal/" + href.split("#")[0].split("?")[0] in names

def test_existing_current_and_archives_pages_are_exported_once():
    layout = {"menu_position": "top", "sections": [{"type": kind, "title": kind, "content": ""} for kind in ("header", "menu", "content", "footer")]}
    journal = SimpleNamespace(journal_info={}, slug="research", name="Research", template_layout=layout)
    pages = [SimpleNamespace(title=kind.title(), slug=kind, content_html=f"<p>Saved {kind}</p>") for kind in ("home", "current", "archives")]
    with ZipFile(BytesIO(build_website_zip(journal, pages, "1234abcd"))) as archive:
        assert len([name for name in archive.namelist() if name.endswith(".html")]) == 4
        assert "Saved current" in archive.read("research/current.html").decode()
        assert "No current issue yet" not in archive.read("research/current.html").decode()


def test_export_wires_live_current_and_archives_javascript():
    import json
    layout = {"menu_position": "top", "sections": [{"type": kind, "title": kind, "content": ""} for kind in ("header", "menu", "content", "footer")]}
    journal = SimpleNamespace(journal_info={}, slug="journal", name="Journal", template_layout=layout)
    pages = [SimpleNamespace(title="Home", slug="home", content_html="<p>Welcome</p>")]
    with ZipFile(BytesIO(build_website_zip(journal, pages, "1234abcd", "https://portal.example.com"))) as archive:
        config = archive.read("journal/assets/journal-config.js").decode()
        assert '"api_origin": "https://portal.example.com"' in config
        assert '"editor_code": "1234abcd"' in config and '"journal_slug": "journal"' in config
        runtime = archive.read("journal/assets/journal-feed.js").decode()
        assert '/api/journal/' in runtime and 'credentials: "omit"' in runtime
        assert 'url.searchParams.set("editor_code"' in runtime and 'url.searchParams.set("journal_slug"' in runtime
        assert '.innerHTML' not in runtime
        assert "article.how_to_cite" in runtime and "How to Cite" in runtime
        for kind in ("current", "archives"):
            html = archive.read(f"journal/{kind}.html").decode()
            assert f'data-journal-feed="{kind}"' in html
            assert 'src="assets/journal-config.js"' in html and 'src="assets/journal-feed.js"' in html
        assert 'journal-feed.js' not in archive.read("journal/index.html").decode()

def test_journal_information_sidebar_in_both_template_styles():
    for position in ("top", "left"):
        layout = {"menu_position": position, "sections": [{"type": kind, "title": kind, "content": ""} for kind in ("header", "menu", "content", "footer")]}
        journal = SimpleNamespace(slug="sidebar", name="Sidebar", template_layout=layout, journal_info={"editor_in_chief": "Editor <One>", "language": "English", "plagiarism": "<10%", "eissn": "2323-5233"})
        pages = [SimpleNamespace(title="Home", slug="home", content_html="<p>Main content</p>")]
        with ZipFile(BytesIO(build_website_zip(journal, pages, "1234abcd", editor_email="editor@example.com"))) as archive:
            for page in ("index", "current", "archives"):
                html = archive.read(f"sidebar/{page}.html").decode()
                assert 'class="journal-content-with-info"' in html
                assert 'aria-label="Journal information"' in html
                assert "Editor &lt;One&gt;" in html and "&lt;10%" in html
                assert "English" in html and "2323-5233" in html
                assert 'aria-label="Journal submissions"' in html and "mailto:editor@example.com" in html
                assert "<dt>Frequency</dt>" not in html
        layout["show_journal_info"] = False
        with ZipFile(BytesIO(build_website_zip(journal, pages, "1234abcd"))) as archive:
            assert 'aria-label="Journal information"' not in archive.read("sidebar/index.html").decode()

def test_optional_journal_panels_are_independent():
    layout = {"menu_position": "top", "sections": [{"type": kind, "title": kind, "content": ""} for kind in ("header", "menu", "content", "footer")]}
    journal = SimpleNamespace(slug="panels", name="Panels", template_layout=layout, journal_info={"language": "English"})
    pages = [SimpleNamespace(title="Home", slug="home", content_html="<p>Home</p>")]
    for show_info, show_submissions in [(True, False), (False, True), (False, False), (True, True)]:
        layout.update(show_journal_info=show_info, show_submissions=show_submissions)
        with ZipFile(BytesIO(build_website_zip(journal, pages, "1234abcd", editor_email="editor@example.com"))) as archive:
            html = archive.read("panels/index.html").decode()
            assert ('aria-label="Journal information"' in html) == show_info
            assert ('aria-label="Journal submissions"' in html) == show_submissions
            assert ('mailto:editor@example.com' in html) == show_submissions

def test_builtin_pages_follow_saved_menu_order_in_export():
    layout = {"menu_position": "top", "sections": [{"type": kind, "title": kind, "content": ""} for kind in ("header", "menu", "content", "footer")]}
    journal = SimpleNamespace(slug="ordered", name="Ordered", template_layout=layout, journal_info={}, menu_order=["archives", "submission", "home", "current"])
    pages = [SimpleNamespace(title="Home", slug="home", content_html="<p>Welcome</p>")]
    with ZipFile(BytesIO(build_website_zip(journal, pages, "1234abcd", editor_email="editor@example.com"))) as archive:
        html = archive.read("ordered/index.html").decode()
        nav = html.split('<nav class="navigation"')[1].split('</nav>')[0]
        assert nav.index('href="archives.html"') < nav.index('href="submission.html"') < nav.index('href="index.html"') < nav.index('href="current.html"')
        assert "mailto:editor@example.com" in archive.read("ordered/submission.html").decode()

def test_export_submission_form_uses_internal_website_api():
    layout={"menu_position":"top","sections":[{"type":kind,"title":kind,"content":""} for kind in ("header","menu","content","footer")]}
    journal=SimpleNamespace(slug="submit",name="Submit",template_layout=layout,journal_info={})
    pages=[SimpleNamespace(title="Home",slug="home",content_html="<p>Home</p>")]
    with ZipFile(BytesIO(build_website_zip(journal,pages,"1234abcd",editor_email="editor@example.com"))) as archive:
        html=archive.read("submit/submission.html").decode()
        assert "data-journal-submission" in html and "assets/journal-submission.js" in html
        script=archive.read("submit/assets/journal-submission.js").decode()
        assert "/api/journal/submission" in script and "captcha_answer" in script
        assert "pdf_base64" in script and '.innerHTML' not in script
        assert "how_to_cite" in script and "How to Cite (optional)" in script
        assert 'href="submission.html"' in archive.read("submit/index.html").decode()

def test_all_exported_pages_load_cached_live_journal_information():
    layout={"menu_position":"top","sections":[{"type":kind,"title":kind,"content":""} for kind in ("header","menu","content","footer")]}
    journal=SimpleNamespace(slug="metadata",name="Metadata",template_layout=layout,journal_info={"language":"English"})
    pages=[SimpleNamespace(title="Home",slug="home",content_html="<p>Home</p>"),SimpleNamespace(title="About",slug="about",content_html="<p>About</p>")]
    with ZipFile(BytesIO(build_website_zip(journal,pages,"1234abcd",editor_email="editor@example.com"))) as archive:
        for filename in archive.namelist():
            if filename.endswith(".html"):
                html=archive.read(filename).decode()
                assert html.count('src="assets/journal-config.js"')==1
                assert 'src="assets/journal-info.js"' in html
                assert 'data-journal-info-fields' in html
                assert 'data-journal-editor-email' in html
        runtime=archive.read("metadata/assets/journal-info.js").decode()
        assert '/api/journal/info' in runtime and 'localStorage' in runtime
        assert '.innerHTML' not in runtime and 'credentials: "omit"' in runtime

def test_editor_in_chief_header_only_on_home_with_live_update_hook():
    layout={"menu_position":"top","sections":[{"type":kind,"title":kind,"content":""} for kind in ("header","menu","content","footer")]}
    journal=SimpleNamespace(slug="chief",name="Chief",template_layout=layout,journal_info={"editor_in_chief":"Dr. <Example>"})
    pages=[SimpleNamespace(title="Home",slug="home",content_html="<p>Home</p>"),SimpleNamespace(title="About",slug="about",content_html="<p>About</p>")]
    with ZipFile(BytesIO(build_website_zip(journal,pages,"1234abcd"))) as archive:
        home=archive.read("chief/index.html").decode()
        assert 'data-editor-in-chief' in home and 'Editor-in-Chief:' in home and 'Dr. &lt;Example&gt;' in home
        assert 'data-editor-in-chief' not in archive.read("chief/about.html").decode()
        assert 'data-editor-in-chief' not in archive.read("chief/current.html").decode()
    journal.journal_info={}
    with ZipFile(BytesIO(build_website_zip(journal,pages,"1234abcd"))) as archive:
        assert 'data-editor-in-chief hidden' in archive.read("chief/index.html").decode()

def test_downloads_panel_contains_offline_pdf_assets_and_can_be_disabled():
    from pathlib import Path
    layout={"menu_position":"top","show_journal_info":False,"show_submissions":False,"show_downloads":True,"sections":[{"type":kind,"title":kind,"content":""} for kind in ("header","menu","content","footer")]}
    journal=SimpleNamespace(slug="downloads",name="Downloads",template_layout=layout,journal_info={})
    pages=[SimpleNamespace(title="Home",slug="home",content_html="<p>Home</p>")]
    with ZipFile(BytesIO(build_website_zip(journal,pages,"1234abcd"))) as archive:
        for page in ("index","current","archives","submission"):
            html=archive.read(f"downloads/{page}.html").decode()
            assert 'aria-label="Journal downloads"' in html
            assert 'href="downloads/copyright-form.pdf" download="copyright-form.pdf"' in html
            assert 'href="downloads/Sample-Manuscript.pdf" download="Sample-Manuscript.pdf"' in html
        for filename in ("copyright-form.pdf","Sample-Manuscript.pdf"):
            content=archive.read(f"downloads/downloads/{filename}")
            assert content.startswith(b"%PDF-")
            assert content==(Path(__file__).resolve().parents[1]/"app/static/downloads"/filename).read_bytes()
    layout["show_downloads"]=False
    with ZipFile(BytesIO(build_website_zip(journal,pages,"1234abcd"))) as archive:
        assert not any(name.endswith(".pdf") for name in archive.namelist())
        assert 'aria-label="Journal downloads"' not in archive.read("downloads/index.html").decode()

def test_inactive_pages_are_excluded_from_export_and_not_regenerated():
    layout={"menu_position":"top","sections":[{"type":kind,"title":kind,"content":""} for kind in ("header","menu","content","footer")]}
    journal=SimpleNamespace(slug="visibility",name="Visibility",template_layout=layout,journal_info={})
    pages=[SimpleNamespace(title="Home",slug="home",content_html="<p>Home</p>",is_active=True),SimpleNamespace(title="Admin About",slug="about",content_html="<p>Hidden content</p>",is_active=False),SimpleNamespace(title="Current",slug="current",content_html="<p>Hidden current</p>",is_active=False),SimpleNamespace(title="Submissions",slug="submissions",content_html="<p>Hidden submission</p>",is_active=False)]
    with ZipFile(BytesIO(build_website_zip(journal,pages,"1234abcd",editor_email="editor@example.com"))) as archive:
        names=archive.namelist()
        assert "visibility/about.html" not in names and "visibility/current.html" not in names
        assert "visibility/submissions.html" not in names and "visibility/submission.html" not in names
        html=archive.read("visibility/index.html").decode()
        assert "Hidden content" not in html
        assert 'href="about.html"' not in html and 'aria-label="Journal submissions"' not in html


def test_export_groups_policy_pages_and_keeps_contact_in_main_menu():
    journal=SimpleNamespace(journal_info={},slug="policies",name="Policies",template_layout={"menu_position":"top","sections":[{"type":kind,"title":kind,"content":""} for kind in ("header","menu","content","footer")]})
    pages=[SimpleNamespace(title=title,slug=slug,menu_group=group,content_html="<p>Policy text</p>") for title,slug,group in [("Home","home",""),("Ethics policy","ethics-policy","Ethics"),("AI policy","ai-policy","Ethics"),("Guidelines","guidelines","For Authors"),("Contact Us","contact-us","")]]
    with ZipFile(BytesIO(build_website_zip(journal,pages,"ab12cd34",editor_email="editor@example.com"))) as archive:
        html=archive.read("policies/contact-us.html").decode()
        assert html.count("<summary>Ethics</summary>")==1
        assert html.count("<summary>For Authors</summary>")==1
        assert 'href="ethics-policy.html"' in html and 'href="ai-policy.html"' in html
        assert 'href="contact-us.html"' in html
        assert 'mailto:editor@example.com' in html


def test_active_policy_submenu_stays_expanded_on_exported_pages():
    journal=SimpleNamespace(journal_info={},slug="menus",name="Menus",template_layout={"menu_position":"top","sections":[{"type":kind,"title":kind,"content":""} for kind in ("header","menu","content","footer")]})
    pages=[SimpleNamespace(title=slug,slug=slug,menu_group=group,content_html="<p>Content</p>") for slug,group in [("home",""),("ethics","Ethics"),("ai","Ethics"),("guidelines","For Authors")]]
    with ZipFile(BytesIO(build_website_zip(journal,pages,"ab12cd34"))) as archive:
        for slug in ("ethics","ai"):
            html=archive.read(f"menus/{slug}.html").decode()
            assert '<details class="journal-menu-group" data-active="true" open><summary>Ethics</summary>' in html
            assert '<details class="journal-menu-group" data-active="false"><summary>For Authors</summary>' in html
        home=archive.read("menus/index.html").decode()
        assert 'data-active="true" open' not in home
