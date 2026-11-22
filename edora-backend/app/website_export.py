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

CSS = """.journal-volume-header{padding-bottom:20px;border-bottom:2px solid currentColor}.journal-volume-header h2{margin:0 0 8px;font-size:28px}.journal-volume-header p{margin:0;font-size:17px;font-weight:600}.journal-article-row{display:flex;justify-content:space-between;align-items:center;gap:24px}.journal-article-row>div{min-width:0}.journal-article-authors{margin:6px 0 0;opacity:.75;font-size:14px}.journal-pdf-link{display:inline-flex;gap:8px;align-items:center;flex-shrink:0;padding:8px 14px;border:1px solid currentColor;border-radius:4px;text-decoration:none!important;font-size:13px;font-weight:600}.journal-pdf-link:hover{background:#00000008}@media(max-width:500px){.journal-article-row{align-items:flex-start;gap:12px}.journal-volume-header h2{font-size:23px}}*{box-sizing:border-box}body{margin:0;font:15px/1.75 system-ui,-apple-system,sans-serif;color:#243b36;background:#fff;overflow-wrap:anywhere}.site{display:grid;grid-template-columns:var(--columns);min-height:100vh;align-content:start}.section{min-width:0;padding:30px clamp(20px,4vw,64px)}.section-content{min-height:60vh}h1{font-size:clamp(28px,3.5vw,42px);line-height:1.25}h2{font-size:24px;line-height:1.3}p{color:inherit}.section-text{white-space:pre-wrap}.section-menu{padding:22px}.navigation{display:flex;flex-wrap:wrap;gap:8px 24px;font-size:14px}.navigation a{color:inherit;text-decoration:none;padding:5px 0;border-bottom:2px solid transparent}.navigation a:hover{text-decoration:underline}.navigation a[aria-current=page]{font-weight:600;border-bottom-color:currentColor}.sidebar .navigation{flex-direction:column;gap:6px}article a{color:inherit;text-decoration:underline}pre{white-space:pre-wrap;padding:18px;background:#00000008}blockquote{border-left:3px solid currentColor;padding-left:20px;margin-left:0}.empty{padding:32px 0;opacity:.75}@media(max-width:650px){.site{display:flex;flex-direction:column}.section{padding:22px}.sidebar .navigation{flex-direction:row;gap:8px 18px}}.journal-publication-feed,.journal-live-feed{font-family:system-ui,-apple-system,sans-serif;font-size:13px;line-height:1.5}.journal-publication-feed .journal-volume,.journal-live-feed .journal-feed-issue{margin:12px 0 20px}.journal-volume-header{display:block;padding:12px 16px;border:1px solid #0000001f;border-radius:8px;background:#00000003}.journal-volume-header h2{font-family:inherit;font-size:12px;line-height:1.4;font-weight:700;text-transform:uppercase;letter-spacing:.1em;margin:0 0 5px;opacity:.65}.journal-volume-summary{display:flex;align-items:baseline;justify-content:space-between;gap:16px;flex-wrap:wrap}.journal-volume-summary h3{font-family:inherit;font-size:19px;line-height:1.35;font-weight:600;margin:0}.journal-volume-summary p{font-size:14px;line-height:1.5;font-weight:600;margin:0}.journal-volume-header .journal-volume-date{font-size:12px;font-weight:400;margin:4px 0 0;opacity:.65}.journal-articles-heading{display:flex;justify-content:space-between;align-items:center;gap:12px;margin:16px 0 0;padding-bottom:8px;border-bottom:1px solid #00000024}.journal-articles-heading h3{font-family:inherit;font-size:16px;line-height:1.4;font-weight:600;margin:0}.journal-articles-heading span{font-size:12px;opacity:.65}.journal-publication-feed .journal-article-row,.journal-live-feed .journal-article-row{display:flex;align-items:center;justify-content:space-between;gap:16px;padding:10px 0;border-top:0;border-bottom:1px solid #00000014}.journal-article-row h4{font-family:inherit;font-size:14px;line-height:1.4;font-weight:600;margin:0 0 3px}.journal-article-row .journal-article-authors{font-size:12px;line-height:1.5;margin:0;opacity:.7}.journal-article-row .journal-pdf-link{padding:5px 9px;font-size:12px;line-height:1.5;border-color:#00000040;border-radius:5px}.journal-website-content>h1{font-size:25px;line-height:1.25;margin:0 0 14px}@media(max-width:500px){.journal-volume-header{padding:10px 12px}.journal-volume-summary h3{font-size:18px}.journal-publication-feed .journal-article-row,.journal-live-feed .journal-article-row{gap:12px;align-items:flex-start}}
.journal-publication-feed,.journal-live-feed{margin-top:12px}.journal-live-feed .journal-feed-article h4{font-size:14px;margin:0 0 3px}.journal-live-feed .journal-feed-article p{margin:0}.journal-volume-header .journal-volume-summary p{font-size:13px}.journal-list-header{display:flex;align-items:center;justify-content:space-between;gap:12px;padding:10px 0;border-bottom:1px solid #00000025;overflow-x:auto}.journal-list-header h2{font-family:inherit;font-size:16px;line-height:1.5;font-weight:600;margin:0;white-space:nowrap}.journal-list-header h2 span{font-size:12px;font-weight:400;opacity:.6}.journal-volume-inline{display:flex;align-items:center;gap:12px;white-space:nowrap;margin-left:auto;font-size:12px;line-height:1.5}.journal-volume-inline strong{font-weight:600}.journal-volume-inline>span{padding:3px 8px;border:1px solid #00000018;border-radius:4px;background:#00000003}.journal-volume-inline time{opacity:.65}@media(max-width:500px){.journal-volume-inline{gap:8px;font-size:11px}.journal-list-header{gap:16px}}.journal-page-heading{display:flex;align-items:center;justify-content:space-between;gap:20px;padding:0 0 12px;overflow-x:auto}.journal-page-heading h1,.journal-feed-title{font-family:inherit;font-size:25px;line-height:1.3;font-weight:600;margin:0;white-space:nowrap}.journal-page-heading h2{font-family:inherit;font-size:18px;margin:0}.journal-page-heading+.journal-list-header{padding-top:4px}.journal-page-heading .journal-volume-inline{flex-shrink:0}.journal-publication-feed .journal-volume:first-of-type,.journal-live-feed .journal-feed-issue:first-of-type{margin-top:0}.journal-content-with-info{display:grid;grid-template-columns:minmax(0,1fr) 230px;gap:28px;align-items:start}.journal-main-content{min-width:0}.journal-information-sidebar{padding:16px;border:1px solid #00000018;border-top:3px solid currentColor;border-radius:6px;background:#00000003;font:12px/1.5 system-ui,-apple-system,sans-serif;min-width:0;overflow-wrap:anywhere}.journal-information-sidebar h2{font-family:inherit;font-size:14px;font-weight:650;margin:0 0 12px;line-height:1.4}.journal-information-sidebar dl{margin:0}.journal-information-sidebar dl>div{padding:7px 0;border-bottom:1px solid #0000000d}.journal-information-sidebar dl>div:last-child{border-bottom:0;padding-bottom:0}.journal-information-sidebar dt{font-size:10px;font-weight:600;opacity:.6;margin-bottom:2px}.journal-information-sidebar dd{margin:0;font-size:12px}.journal-information-sidebar p{font-size:12px;margin:0;opacity:.65}.template-info-preview{grid-template-columns:minmax(0,1fr) minmax(110px,35%);gap:10px}.template-preview .journal-information-sidebar{padding:8px;font-size:9px}.template-preview .journal-information-sidebar h2{font-size:10px;margin:0 0 5px}.template-preview .journal-information-sidebar dt,.template-preview .journal-information-sidebar dd{font-size:9px}.template-preview .journal-information-sidebar dl>div{padding:3px 0}.template-preview .journal-information-sidebar dd{margin:0}@media(max-width:1050px){.journal-website .journal-content-with-info{grid-template-columns:minmax(0,1fr) 200px;gap:18px}}@media(max-width:800px){.journal-website .journal-content-with-info,.site .journal-content-with-info{grid-template-columns:1fr}.journal-information-sidebar dl{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:0 16px}}.journal-right-panels{min-width:0;display:grid;gap:14px}.journal-submissions-box{padding:16px;border:1px solid #00000018;border-radius:6px;background:#00000003;font:12px/1.5 system-ui,-apple-system,sans-serif;overflow-wrap:anywhere}.journal-submissions-box h2{font:650 14px/1.4 system-ui,-apple-system,sans-serif;margin:0 0 8px}.journal-submissions-box p{font-size:12px;margin:0 0 8px;opacity:.7}.journal-editor-email{display:block;font-size:11px;text-decoration:underline;margin-bottom:12px}.journal-submit-button{display:flex;align-items:center;justify-content:center;gap:8px;padding:8px 10px;border:1px solid currentColor;border-radius:4px;font-size:11px;font-weight:600;text-decoration:none!important}.journal-submit-button:hover{background:#00000008}.journal-information-sidebar dl{display:block;margin:0}.journal-information-sidebar dl>div{display:block;padding:4px 0;border:0;line-height:1.5}.journal-information-sidebar dt,.journal-information-sidebar dd{display:inline;margin:0;font-size:12px;line-height:1.5}.journal-information-sidebar dt{font-weight:600;opacity:.8}.journal-information-sidebar dt::after{content:": ";}.journal-information-sidebar dd{font-weight:400}.journal-information-sidebar{padding:12px 14px}.journal-information-sidebar h2{font-size:13px;margin:0 0 8px}.journal-submission-form{font:13px/1.5 system-ui,-apple-system,sans-serif;margin:16px 0;max-width:760px}.journal-submission-form fieldset{border:0;padding:0;margin:0;min-width:0}.submission-fields{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:12px 16px}.journal-submission-form label{display:flex;flex-direction:column;gap:5px;font-size:12px;font-weight:600;margin:0}.submission-wide{grid-column:1/-1}.journal-submission-form input,.journal-submission-form textarea{box-sizing:border-box;width:100%;font:13px/1.5 system-ui,sans-serif;padding:9px 10px;border:1px solid #00000030;border-radius:5px;background:#fff;color:#243b36}.journal-submission-form textarea{min-height:90px;resize:vertical}.submission-captcha{display:flex;align-items:center;gap:12px;flex-wrap:wrap;margin:18px 0}.submission-captcha img{border:1px solid #00000020;border-radius:4px}.submission-captcha label{flex:1;min-width:150px}.journal-submission-form button{font:600 12px/1.5 system-ui,sans-serif;padding:9px 14px;border:1px solid #214d3e;border-radius:5px;background:#214d3e;color:white;cursor:pointer}.journal-submission-form button:disabled{opacity:.6;cursor:wait}.journal-submission-form button.secondary{background:transparent;color:inherit;margin:0}.submission-status{font-size:12px;overflow-wrap:anywhere}.submission-status[role=alert]{color:#a23e36}@media(max-width:550px){.submission-fields{grid-template-columns:1fr}.journal-submission-form input,.journal-submission-form textarea{font-size:16px}}.article-citation{margin-top:7px;font:12px/1.5 system-ui,-apple-system,sans-serif}.article-citation summary{cursor:pointer;font-size:11px;font-weight:600;text-decoration:underline;text-underline-offset:2px;opacity:.8}.article-citation p{font-size:12px;line-height:1.6;margin:7px 0 0;padding:9px 11px;background:#00000004;border:1px solid #00000012;border-radius:5px;white-space:pre-wrap;overflow-wrap:anywhere}.article-citation summary:focus-visible{outline:2px solid #629d7c;outline-offset:3px}.journal-site-header{display:flex;align-items:center;justify-content:space-between;gap:28px}.journal-site-brand{min-width:0;flex:1}.journal-site-brand h2{margin:0 0 12px}.journal-site-brand p{color:inherit}.journal-header-chief{display:flex;align-items:baseline;justify-content:flex-end;gap:7px;max-width:40%;font:14px/1.5 system-ui,-apple-system,sans-serif;overflow-wrap:anywhere}.journal-header-chief strong{font-weight:650;white-space:nowrap}.journal-header-chief[hidden]{display:none}@media(max-width:650px){.journal-site-header{align-items:flex-start;flex-direction:column;gap:16px}.journal-header-chief{max-width:100%;justify-content:flex-start;font-size:12px}}.journal-downloads-box{padding:14px;border:1px solid #00000018;border-radius:6px;background:#00000003;font:12px/1.5 system-ui,-apple-system,sans-serif;overflow-wrap:anywhere}.journal-downloads-box h2{font:650 14px/1.4 system-ui,-apple-system,sans-serif;margin:0 0 10px}.journal-downloads-box a{display:block;padding:7px 0;text-decoration:underline;text-underline-offset:3px;border-bottom:1px solid #0000000d}.journal-downloads-box a:last-child{border-bottom:0}.template-preview .journal-downloads-box{padding:8px}.template-preview .journal-downloads-box h2{font-size:10px;margin:0 0 4px}.template-preview .journal-downloads-box a{font-size:9px;padding:4px 0}.journal-menu-group{position:relative}.journal-menu-group summary{cursor:pointer;padding:5px 0;list-style:none;display:flex;align-items:center;gap:8px;font:inherit}.journal-menu-group summary::-webkit-details-marker{display:none}.journal-menu-group summary::after{content:"";width:6px;height:6px;border-right:1.5px solid currentColor;border-bottom:1.5px solid currentColor;transform:rotate(45deg);margin-top:-3px}.journal-menu-group[data-active=true]>summary{font-weight:650}.journal-menu-group[open]>summary::after{transform:rotate(225deg);margin-top:3px}.journal-menu-children{position:absolute;top:100%;left:0;z-index:20;min-width:250px;max-width:300px;padding:8px;background:#fff;color:#243b36;border:1px solid #dfe7e2;border-radius:6px;box-shadow:0 8px 24px #183c361a}.journal-menu-group[open]>.journal-menu-children{display:flex;flex-direction:column;gap:0}.journal-menu-children a{display:block;padding:8px 10px!important;border:0!important;font-size:12px;line-height:1.5;text-decoration:none}.journal-menu-children a:hover,.journal-menu-children a[aria-current=page]{background:#f0f5f2;border-radius:4px}.menu-left .journal-menu-children,.menu-right .journal-menu-children,.sidebar .journal-menu-children{position:static;min-width:0;max-width:none;margin-top:6px;box-shadow:none}.journal-menu-group summary:focus-visible{outline:2px solid #629d7c;outline-offset:3px}.journal-contact-email{font-size:14px;margin-top:24px}.journal-contact-email a{text-decoration:underline}.page-menu-tabs{display:flex;gap:6px;flex-wrap:wrap;margin-bottom:16px}.admin-shell .page-menu-tabs button{margin:0}.page-menu-tabs button[aria-pressed=true]{background:#eaf2ed;color:#214d3e;border-color:#91b49f}@media(max-width:650px){.journal-menu-children{min-width:210px;max-width:min(280px,80vw)}}"""

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


def build_website_zip(journal, pages, editor_code, api_origin="http://localhost:3000", editor_email=""):
    origin = urlsplit(api_origin)
    if origin.scheme not in {"http", "https"} or not origin.netloc or origin.username or origin.password:
        raise ValueError("Configure a valid frontend API origin before export")
    api_origin = f"{origin.scheme}://{origin.netloc}"
    layout = TemplateLayout.model_validate(journal.template_layout)
    if not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", journal.slug):
        raise ValueError("Journal has an invalid website slug")
    inactive_slugs = {p.slug for p in pages if not getattr(p,"is_active",True)}
    copied = [PageInput(title=p.title, slug=p.slug, content_html=p.content_html) for p in pages if getattr(p,"is_active",True)]
    entries = [{"slug": p.slug, "title": "Current" if p.slug == "current" else "Archives" if p.slug == "archives" else p.title,
                "html": p.content_html, "menu_group": next((getattr(original,"menu_group","") for original in pages if original.slug==p.slug),"")} for p in copied]
    for slug, title in (("current", "Current"), ("archives", "Archives")):
        if slug not in inactive_slugs and not any(p["slug"] == slug for p in entries):
            entries.append({"slug": slug, "title": title, "html": f"<h1>{title}</h1>"})
    if not inactive_slugs.intersection({"submission","submissions"}) and not any(p["slug"] in {"submission", "submissions"} for p in entries):
        contact = escape(editor_email)
        target = escape("mailto:" + editor_email + "?subject=Manuscript%20submission", quote=True)
        entries.append({"slug": "submission", "title": "Submission", "html": '<h1>Submission</h1><h2>Submit your manuscript</h2><p>Send original research, author details and a cover letter to the editor.</p><p><a href="' + target + '">Submit manuscript to ' + contact + '</a></p>'})
    saved_order = getattr(journal, "menu_order", None) or []
    entries.sort(key=lambda entry: saved_order.index(entry["slug"]) if entry["slug"] in saved_order else len(saved_order))
    if not entries:
        raise ValueError("Activate at least one page before exporting")
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
        archive.writestr(f"{folder}/assets/journal-submission.js", (Path(__file__).parent / "static/journal-submission.js").read_text(encoding="utf-8"))
        archive.writestr(f"{folder}/assets/journal-info.js", (Path(__file__).parent / "static/journal-info.js").read_text(encoding="utf-8"))
        if layout.show_downloads:
            for filename in ("copyright-form.pdf", "Sample-Manuscript.pdf"):
                source = Path(__file__).parent / "static" / "downloads" / filename
                if not source.is_file():
                    raise ValueError("A required download PDF is missing")
                archive.writestr(f"{folder}/downloads/{filename}", source.read_bytes())
        for page in entries:
            rewrite = LinkRewriter(files, prefix)
            rewrite.feed(page["html"])
            rewrite.close()
            content = "".join(rewrite.parts)
            scripts = '<script src="assets/journal-config.js"></script><script defer src="assets/journal-info.js"></script>'
            if page["slug"] in {"current", "archives"}:
                content = re.sub(r"^\s*<h1\b[^>]*>[\s\S]*?</h1>", "", content, count=1, flags=re.IGNORECASE)
                content += f'<section class="journal-live-feed" data-journal-feed="{page["slug"]}" aria-label="Published issues and articles"><noscript>Enable JavaScript to load published issues and articles.</noscript></section>'
                scripts += '<script defer src="assets/journal-feed.js"></script>'
            if page["slug"] in {"submission", "submissions"}:
                content = re.sub(r'<a\b[^>]*href="mailto:[^"]*"[^>]*>[\s\S]*?</a>', "", content, flags=re.IGNORECASE)
                content += '<section data-journal-submission><noscript>Enable JavaScript to submit your manuscript.</noscript></section>'
                scripts += '<script defer src="assets/journal-submission.js"></script>'
            if page["slug"] == "contact-us" and editor_email:
                content += '<p class="journal-contact-email"><strong>Editorial office:</strong> <a href="mailto:' + escape(editor_email,quote=True) + '">' + escape(editor_email) + '</a></p>'
            sections = []
            for section in layout.sections:
                if section.type == "menu":
                    links = []
                    nodes = []
                    groups = {}
                    for item in entries:
                        group = item.get("menu_group", "")
                        if group:
                            if group not in groups:
                                groups[group] = []
                                nodes.append((group, groups[group]))
                            groups[group].append(item)
                        else:
                            nodes.append(("", [item]))
                    for group, children in nodes:
                        child_links = []
                        for item in children:
                            current = ' aria-current="page"' if item["slug"] == page["slug"] else ""
                            child_links.append(f'<a href="{escape(files[item["slug"]], quote=True)}"{current}>{escape(item["title"])}</a>')
                        if group:
                            active = "true" if any(item["slug"] == page["slug"] for item in children) else "false"
                            links.append('<details class="journal-menu-group" data-active="' + active + '"' + (' open' if active == 'true' else '') + '><summary>' + escape(group) + '</summary><div class="journal-menu-children">' + "".join(child_links) + '</div></details>')
                        else:
                            links.extend(child_links)
                    body = '<nav class="navigation" aria-label="Journal pages">' + "".join(links) + "</nav>"
                elif section.type == "content":
                    body = '<article class="journal-main-content">' + content + "</article>"
                    show_submissions = layout.show_submissions if layout.show_submissions is not None else layout.show_journal_info
                    if layout.show_journal_info or show_submissions or layout.show_downloads:
                        labels = [("editor_in_chief", "EiC"), ("frequency", "Frequency"), ("final_decision", "Final decision"), ("acceptance_rate", "Acceptance rate"), ("plagiarism", "Plagiarism"), ("language", "Language"), ("review_process", "Review process"), ("open_access", "Open access"), ("copyright", "Copyright"), ("eissn", "eISSN")]
                        info = journal.journal_info or {}
                        rows = "".join(f"<div><dt>{escape(label)}</dt><dd>{escape(str(info[key]))}</dd></div>" for key, label in labels if info.get(key))
                        details = "<dl>" + rows + "</dl>" if rows else "<p>Journal details will appear here.</p>"
                        submission = ""
                        if editor_email and show_submissions and not inactive_slugs.intersection({"submission","submissions"}):
                            from urllib.parse import quote
                            email = escape(editor_email)
                            target = escape("mailto:" + quote(editor_email, safe="@.+") + "?subject=Journal%20manuscript%20submission", quote=True)
                            submission_file = files.get("submissions", files.get("submission", "submission.html"))
                            submission = '<aside class="journal-submissions-box" aria-label="Journal submissions"><h2>Submissions</h2><p>Send your manuscript to the editor.</p><a class="journal-editor-email" data-journal-editor-email href="' + target + '">' + email + '</a><a class="journal-submit-button" href="' + escape(submission_file, quote=True) + '">Submit manuscript</a></aside>'
                        information = '<aside class="journal-information-sidebar" data-journal-info aria-label="Journal information"><h2>Journal information</h2><div data-journal-info-fields>' + details + '</div></aside>' if layout.show_journal_info else ""
                        downloads = '<aside class="journal-downloads-box" aria-label="Journal downloads"><h2>Downloads</h2><a href="downloads/copyright-form.pdf" download="copyright-form.pdf">Copyright Form</a><a href="downloads/Sample-Manuscript.pdf" download="Sample-Manuscript.pdf">Sample Manuscript</a></aside>' if layout.show_downloads else ""
                        body = '<div class="journal-content-with-info">' + body + '<div class="journal-right-panels">' + information + submission + downloads + '</div></div>'
                elif section.type == "header":
                    chief = ""
                    if page["slug"] == home["slug"]:
                        name = str((journal.journal_info or {}).get("editor_in_chief", "")).strip()
                        hidden = "" if name else " hidden"
                        chief = '<div class="journal-header-chief" data-editor-in-chief' + hidden + '><strong>Editor-in-Chief:</strong><span data-editor-in-chief-value>' + escape(name) + '</span></div>'
                    body = '<div class="journal-site-header"><div class="journal-site-brand"><h2>' + escape(section.title) + '</h2><p class="section-text">' + escape(section.content) + '</p></div>' + chief + '</div>'
                else:
                    body = f'<h2>{escape(section.title)}</h2><p class="section-text">{escape(section.content)}</p>'
                sections.append(f'<section class="section section-{section.type}">{body}</section>')
            title = escape(f'{page["title"]} | {journal.name}')
            document = f'<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>{title}</title><link rel="stylesheet" href="assets/styles.css"></head><body><div class="site {"sidebar" if sidebar else "horizontal"}">{"".join(sections)}</div>{scripts}</body></html>'
            total_bytes += len(document.encode("utf-8"))
            if total_bytes > 64000000:
                raise ValueError("Website exceeds the 64 MB uncompressed export limit")
            archive.writestr(f'{folder}/{files[page["slug"]]}', document)
        archive.writestr(f"{folder}/README.txt", "Open index.html in a browser after extracting this entire folder.\nUpload the contents of this folder to your website document root to host it.\nThis is a snapshot of saved journal content; later changes require a new export.\nJournal information is loaded through /api/journal/info and cached in localStorage for five minutes, keyed by API origin, editor code and journal slug. Navigating between pages reuses this cache. If browser storage is unavailable, each page fetches its own data. An exported snapshot remains as an offline fallback.\nCurrent and Archives load live published issues/articles from the frontend APIs using JavaScript. They require internet access and the frontend/backend services to be running. Edit assets/journal-config.js if the frontend origin changes.\nExternal reference links still require internet access. Submissions use the live manuscript form and CAPTCHA service.\n")
    return output.getvalue()
