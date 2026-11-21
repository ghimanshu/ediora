"""Remove external EEL links from master content and editor copies."""
import re
from html import unescape
from urllib.parse import urlsplit
from alembic import op
import sqlalchemy as sa
revision = "0016"
down_revision = "0015"
branch_labels = None
depends_on = None

def is_eelet(value):
    try:
        value = unescape(value.strip())
        host = (urlsplit(value if "://" in value or value.startswith("//") else "//" + value).hostname or "").lower()
        return any(host == domain or host.endswith("." + domain) for domain in ("eelet.org", "eelet.org.uk"))
    except ValueError:
        return False

def clean_text(value):
    value = re.sub(r"<li\b[^>]*>[^<]*[A-Z0-9._%+-]+@(?:[A-Z0-9-]+\.)*eelet\.org(?:\.uk)?[^<]*</li>", "", value, flags=re.I)
    value = re.sub(r"[A-Z0-9._%+-]+@(?:[A-Z0-9-]+\.)*eelet\.org(?:\.uk)?\b", "", value, flags=re.I)
    def anchor(match):
        attrs, content = match.group(1), match.group(2)
        href = re.search(r"\bhref\s*=\s*(?:\"([^\"]*)\"|'([^']*)'|([^\s>]+))", attrs, re.I)
        if href and is_eelet(next(group for group in href.groups() if group is not None)):
            return content
        return match.group(0)
    value = re.sub(r"<a\b([^>]*)>([\s\S]*?)</a\s*>", anchor, value, flags=re.I)
    # Plain-text template sections may contain URLs without anchor tags.
    return re.sub(r"(?:https?://|//|www\.)[^\s<>\"']+", lambda m: "" if is_eelet(m.group(0)) else m.group(0), value, flags=re.I)

def clean(value):
    if isinstance(value, str):
        return clean_text(value)
    if isinstance(value, list):
        return [clean(item) for item in value]
    if isinstance(value, dict):
        return {key: clean(item) for key, item in value.items()}
    return value

def upgrade():
    db = op.get_bind()
    specs = [("website_templates", {"description": sa.String(), "layout": sa.JSON()}), ("web_pages", {"content_html": sa.Text()}), ("editor_journals", {"template_description": sa.String(), "template_layout": sa.JSON(), "journal_info": sa.JSON()}), ("editor_journal_pages", {"content_html": sa.Text()}), ("journal_articles", {"abstract": sa.Text(), "article_url": sa.String()})]
    for name, fields in specs:
        table = sa.table(name, sa.column("id", sa.Integer()), *(sa.column(key, kind) for key, kind in fields.items()))
        for row in db.execute(sa.select(table)).mappings():
            changes = {key: clean(row[key]) for key in fields if clean(row[key]) != row[key]}
            if changes:
                db.execute(table.update().where(table.c.id == row["id"]).values(**changes))

def downgrade():
    # External links are deliberately not restored into edited content.
    pass
