"""Export static HTML/CSS plus client-side Current/Archives feeds; generation makes no network calls."""
from html import escape
from html.parser import HTMLParser
from io import BytesIO
import json
from pathlib import Path
import re
from urllib.parse import urlsplit, unquote
from zipfile import ZipFile, ZIP_DEFLATED
from app.page_schemas import PageInput
from app.template_schemas import TemplateLayout

CSS = """*{box-sizing:border-box}body{margin:0;font:15px/1.75 system-ui,-apple-system,sans-serif;color:#243b36;background:#fff;overflow-wrap:anywhere}.site{display:grid;grid-template-columns:var(--columns);min-height:100vh;align-content:start}.section{min-width:0;padding:30px clamp(20px,4vw,64px)}.section-content{min-height:60vh}h1{font-size:clamp(28px,3.5vw,42px);line-height:1.25}h2{font-size:24px;line-height:1.3}p{color:inherit}.section-text{white-space:pre-wrap}.section-menu{padding:22px}.navigation{display:flex;flex-wrap:wrap;gap:8px 24px;font-size:14px}.navigation a{color:inherit;text-decoration:none;padding:5px 0;border-bottom:2px solid transparent}.navigation a:hover{text-decoration:underline}.navigation a[aria-current=page]{font-weight:600;border-bottom-color:currentColor}.sidebar .navigation{flex-direction:column;gap:6px}article a{color:inherit;text-decoration:underline}pre{white-space:pre-wrap;padding:18px;background:#00000008}blockquote{border-left:3px solid currentColor;padding-left:20px;margin-left:0}.empty{padding:32px 0;opacity:.75}@media(max-width:650px){.site{display:flex;flex-direction:column}.section{padding:22px}.sidebar .navigation{flex-direction:row;gap:8px 18px}}"""

class LinkRewriter(HTMLParser):
    def __init__(self, files, prefix):
        super().__init__(convert_charrefs=False)
        self.files, self.prefix, self.parts = files, prefix, []

    def href(self, value):
        url = urlsplit(value)
        if url.scheme and url.scheme not in {"http", "https"}:
            return value
        path = unquote(url.path)
        if path.startswith(self.prefix + "/"):
            path = path[len(self.prefix) + 1:]
        elif url.netloc:
            return value
        else:
            path = path.lstrip("/")
        if path.endswith(".html"):
            path = path[:-5]
        if path in self.files:
            return self.files[path] + ("?" + url.query if url.query else "") + ("#" + url.fragment if url.fragment else "")
        return value

    def handle_starttag(self, tag, attrs):
        attributes = []
        for name, value in attrs:
            if value is None:
                attributes.append(name)
            else:
                if tag == "a" and name == "href":
                    value = self.href(value)
                attributes.append(f'{name}="{escape(value, quote=True)}"')
        self.parts.append("<" + tag + (" " + " ".join(attributes) if attributes else "") + ">")

    def handle_startendtag(self, tag, attrs):
        self.handle_starttag(tag, attrs)

    def handle_endtag(self, tag):
        self.parts.append(f"</{tag}>")

    def handle_data(self, data):
        self.parts.append(escape(data, quote=False))

    def handle_entityref(self, name):
        self.parts.append(f"&{name};")

    def handle_charref(self, name):
        self.parts.append(f"&#{name};")


def build_website_zip(journal, pages, editor_code, api_origin="http://localhost:3000"):
    origin = urlsplit(api_origin)
    if origin.scheme not in {"http", "https"} or not origin.netloc or origin.username or origin.password:
        raise ValueError("Configure a valid frontend API origin before export")
    api_origin = f"{origin.scheme}://{origin.netloc}"
    layout = TemplateLayout.model_validate(journal.template_layout)
    if not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", journal.slug):
        raise ValueError("Journal has an invalid website slug")
    copied = [PageInput(title=p.title, slug=p.slug, content_html=p.content_html) for p in pages]
    if not copied:
        raise ValueError("Add at least one page before exporting")
    entries = [{"slug": p.slug, "title": "Current" if p.slug == "current" else "Archives" if p.slug == "archives" else p.title,
                "html": p.content_html} for p in copied]
    for slug, title in (("current", "Current"), ("archives", "Archives")):
        if not any(p["slug"] == slug for p in entries):
            entries.append({"slug": slug, "title": title, "html": f"<h1>{title}</h1>"})
    home = next((p for p in entries if p["slug"] == "home"), entries[0])
    files = {home["slug"]: "index.html"}
    used = {"index.html"}
    for page in entries:
        if page["slug"] in files:
            continue
        filename = page["slug"] + ".html"
        suffix = 1
        while filename in used:
            filename = f'{page["slug"]}-{suffix}.html'
            suffix += 1
        files[page["slug"]] = filename
        used.add(filename)
    prefix = f"/{editor_code}/{journal.slug}"
    sidebar = layout.menu_position != "top"
    columns = "220px minmax(0,1fr)" if layout.menu_position == "left" else "minmax(0,1fr) 220px" if sidebar else "minmax(0,1fr)"
    styles = [CSS + ".journal-live-feed{margin-top:24px}.journal-feed-issue{margin:24px 0}.journal-feed-article{padding:16px 0;border-top:1px solid #00000020}.journal-feed-article h4{font-size:18px;margin:0 0 8px}.journal-feed-controls{display:flex;gap:10px}.journal-feed-controls button{font:inherit;padding:8px 14px;border:1px solid currentColor;border-radius:4px;background:transparent;color:inherit;cursor:pointer}", f".site{{--columns:{columns}}}"]
    main = [section for section in layout.sections if section.type != "menu"]
    content_row = next(i + 1 for i, section in enumerate(main) if section.type == "content")
    for index, section in enumerate(layout.sections):
        row = index + 1 if not sidebar else content_row if section.type == "menu" else main.index(section) + 1
        column = "1 / -1" if not sidebar or section.type not in {"menu", "content"} else "1" if (section.type == "menu") == (layout.menu_position == "left") else "2"
        styles.append(f".section-{section.type}{{grid-row:{row};grid-column:{column};background:{section.background_color};color:{section.text_color}}}")
    folder = journal.slug
    output = BytesIO()
    total_bytes = 0
    with ZipFile(output, "w", compression=ZIP_DEFLATED) as archive:
        archive.writestr(f"{folder}/assets/styles.css", "\n".join(styles))
        config = {"api_origin": api_origin, "editor_code": editor_code, "journal_slug": journal.slug}
        archive.writestr(f"{folder}/assets/journal-config.js", "// Set api_origin to your running frontend application's HTTPS origin.\nwindow.EDORA_JOURNAL = Object.freeze(" + json.dumps(config) + ");\n")
        archive.writestr(f"{folder}/assets/journal-feed.js", (Path(__file__).parent / "static/journal-feed.js").read_text(encoding="utf-8"))
        for page in entries:
            rewrite = LinkRewriter(files, prefix)
            rewrite.feed(page["html"])
            rewrite.close()
            content = "".join(rewrite.parts)
            scripts = ""
            if page["slug"] in {"current", "archives"}:
                content += f'<section class="journal-live-feed" data-journal-feed="{page["slug"]}" aria-label="Published issues and articles"><noscript>Enable JavaScript to load published issues and articles.</noscript></section>'
                scripts = '<script src="assets/journal-config.js"></script><script defer src="assets/journal-feed.js"></script>' 
            sections = []
            for section in layout.sections:
                if section.type == "menu":
                    links = []
                    for item in entries:
                        current = ' aria-current="page"' if item["slug"] == page["slug"] else ""
                        links.append(f'<a href="{escape(files[item["slug"]], quote=True)}"{current}>{escape(item["title"])}</a>')
                    body = '<nav class="navigation" aria-label="Journal pages">' + "".join(links) + "</nav>"
                elif section.type == "content":
                    body = "<article>" + content + "</article>"
                else:
                    body = f'<h2>{escape(section.title)}</h2><p class="section-text">{escape(section.content)}</p>'
                sections.append(f'<section class="section section-{section.type}">{body}</section>')
            title = escape(f'{page["title"]} | {journal.name}')
            document = f'<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>{title}</title><link rel="stylesheet" href="assets/styles.css"></head><body><div class="site {"sidebar" if sidebar else "horizontal"}">{"".join(sections)}</div>{scripts}</body></html>'
            total_bytes += len(document.encode("utf-8"))
            if total_bytes > 64000000:
                raise ValueError("Website exceeds the 64 MB uncompressed export limit")
            archive.writestr(f'{folder}/{files[page["slug"]]}', document)
        archive.writestr(f"{folder}/README.txt", "Open index.html in a browser after extracting this entire folder.\nUpload the contents of this folder to your website document root to host it.\nThis is a snapshot of saved journal content; later changes require a new export.\nCurrent and Archives load live published issues/articles from the frontend APIs using JavaScript. They require internet access and the frontend/backend services to be running. Edit assets/journal-config.js if the frontend origin changes.\nExternal reference links still require internet access. Images, embeds, forms and publishing services are not included.\n")
    return output.getvalue()
