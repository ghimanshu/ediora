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
    journal = SimpleNamespace(slug="my-journal", name="My <Journal>", template_layout={"menu_position": "right", "sections": sections})
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
        assert "Welcome" in home and "onclick" not in home and "<script" not in home
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
    journal = SimpleNamespace(slug="research", name="Research", template_layout=layout)
    pages = [SimpleNamespace(title=kind.title(), slug=kind, content_html=f"<p>Saved {kind}</p>") for kind in ("home", "current", "archives")]
    with ZipFile(BytesIO(build_website_zip(journal, pages, "1234abcd"))) as archive:
        assert len([name for name in archive.namelist() if name.endswith(".html")]) == 3
        assert "Saved current" in archive.read("research/current.html").decode()
        assert "No current issue yet" not in archive.read("research/current.html").decode()


def test_export_wires_live_current_and_archives_javascript():
    import json
    layout = {"menu_position": "top", "sections": [{"type": kind, "title": kind, "content": ""} for kind in ("header", "menu", "content", "footer")]}
    journal = SimpleNamespace(slug="journal", name="Journal", template_layout=layout)
    pages = [SimpleNamespace(title="Home", slug="home", content_html="<p>Welcome</p>")]
    with ZipFile(BytesIO(build_website_zip(journal, pages, "1234abcd", "https://portal.example.com"))) as archive:
        config = archive.read("journal/assets/journal-config.js").decode()
        assert '"api_origin": "https://portal.example.com"' in config
        assert '"editor_code": "1234abcd"' in config and '"journal_slug": "journal"' in config
        runtime = archive.read("journal/assets/journal-feed.js").decode()
        assert '/api/journal/' in runtime and 'credentials: "omit"' in runtime
        assert 'url.searchParams.set("editor_code"' in runtime and 'url.searchParams.set("journal_slug"' in runtime
        assert '.innerHTML' not in runtime
        for kind in ("current", "archives"):
            html = archive.read(f"journal/{kind}.html").decode()
            assert f'data-journal-feed="{kind}"' in html
            assert 'src="assets/journal-config.js"' in html and 'src="assets/journal-feed.js"' in html
        assert 'journal-feed.js' not in archive.read("journal/index.html").decode()
