"""Seed four rewritten journal pages without replacing existing content.

Sources reviewed 2026-11-15; no network calls run during migration.
Downgrade intentionally retains content to protect subsequent editorial changes.
"""
from datetime import datetime, timezone
from alembic import op
import sqlalchemy as sa

revision = "0005"
down_revision = "0004"
branch_labels = None
depends_on = None

PAGES = (
    {
        "title": "Home",
        "slug": "home",
        "content_html": """<h1>European Economic Letters</h1>
<p>European Economic Letters (EEL) shares economic research with an international readership through peer-reviewed, openly accessible articles.</p>
<h2>Research with practical relevance</h2>
<p>The journal welcomes theoretical studies, evidence-based analysis, and policy research concerning Europe and the wider world. Its interests include macroeconomics, development and growth, econometrics, finance, international trade, public policy, and the economics of health and education.</p>
<h2>Editorial assessment</h2>
<p>Submissions receive an initial editorial assessment before independent specialists evaluate their originality, research quality, and relevance. Review follows a single-blind model.</p>
<h2>Responsible scholarship</h2>
<p>Clear methods, sound evidence, and ethical research underpin the journal's approach. EEL opposes plagiarism and manipulation of research findings.</p>
<h2>Journal information</h2>
<ul><li>ISSN and ISSN-L: 2323-5233</li><li>Publisher: European Economics Letters Group</li><li>Editorial contact: <a href="mailto:editor@eelet.org.uk">editor@eelet.org.uk</a></li></ul>
<p><a href="https://www.eelet.org.uk/index.php/journal/issue/current">Explore the current issue</a> or <a href="https://www.eelet.org.uk/index.php/journal/issue/archive">browse earlier issues</a>.</p>
<p>Adapted from the <a href="https://www.eelet.org.uk/index.php/journal/index">journal homepage</a>; reviewed 15 November 2026.</p>""",
    },
    {
        "title": "About the Journal",
        "slug": "about-the-journal",
        "content_html": """<h1>About the Journal</h1>
<p>European Economic Letters connects researchers and policymakers through economic scholarship that considers regional, national, and international questions, including European and comparative perspectives.</p>
<h2>Subjects and contributions</h2>
<p>Original articles, brief research communications, and policy notes are welcome. Topics span microeconomics, macroeconomics, trade, development, banking, behavioural research, environmental resources, public policy, digital markets, and emerging economies.</p>
<h2>How manuscripts are assessed</h2>
<ol><li>Editors assess suitability, research quality, and ethical compliance.</li><li>At least two independent specialists review the manuscript under a single-blind process.</li><li>The editorial decision considers those assessments.</li></ol>
<h2>Integrity and access</h2>
<p>The journal describes its ethics framework as informed by COPE guidance. Its policies address originality, authorship, competing interests, and correction of the research record. An international editorial board supports these standards.</p>
<p>Articles are freely available online. The journal states that authors retain copyright; readers should consult each article's licensing terms before reuse.</p>
<p>Adapted from <a href="https://www.eelet.org.uk/index.php/journal/about">About the Journal</a>; reviewed 15 November 2026.</p>""",
    },
    {
        "title": "Editorial Team",
        "slug": "editorial-team",
        "content_html": """<h1>Editorial Team</h1>
<p>The journal lists the following contributors to its editorial team. Affiliations are presented as reported by the source.</p>
<ul>
<li><strong>Narjess Aloui</strong> — Assistant professor, Carthage Business School, University of Tunis Carthage, Tunisia.</li>
<li><strong>Stephen Pembi, Ph.D.</strong> — Lecturer in Business Administration, Adamawa State University, Nigeria.</li>
<li><strong>Amer Shebl Zaya</strong> — Retired; previously an assistant director at Iraq's Ministry of Culture.</li>
<li><strong>Ahmad Khilji</strong> — NCBAE Lahore, Pakistan.</li>
<li><strong>Muhammad Umar Riaz Abbasi</strong> — Lecturer, National University of Modern Languages, Islamabad, Pakistan.</li>
<li><strong>Daud Abdul</strong> — School of Economics and Management, Nanjing University of Science and Technology, China.</li>
<li><strong>Magdy Ali</strong> — IGSR, Egypt.</li>
<li><strong>Wegayehu Enbeyle</strong> — Director of International Relationships and Partnership, Mizan-Tepi University, Ethiopia.</li>
<li><strong>Sajid Ali Khan</strong> — Green Hills Postgraduate College, Rawalakot, Poonch AJK, Pakistan.</li>
</ul>
<p>Adapted from the <a href="https://www.eelet.org.uk/index.php/journal/about/editorialTeam">editorial team directory</a>; reviewed 15 November 2026. A repeated entry has been consolidated.</p>""",
    },
    {
        "title": "Submissions",
        "slug": "submissions",
        "content_html": """<h1>Submissions</h1>
<p>Authors submit manuscripts through the journal's online system. <a href="https://www.eelet.org.uk/index.php/journal/login">Sign in</a> or <a href="https://www.eelet.org.uk/index.php/journal/user/register">create an account</a> to begin.</p>
<h2>Before sending your manuscript</h2>
<ul>
<li>Confirm that the work has not appeared elsewhere and is not being considered by another journal. Explain any exception to the editor.</li>
<li>Prepare the file using OpenOffice, Microsoft Word, or RTF.</li>
<li>Add web addresses for references whenever available.</li>
<li>Use single spacing and a 12-point type size. Prefer italics to underlining, apart from web addresses.</li>
<li>Place figures, illustrations, and tables next to the relevant discussion rather than collecting them at the end.</li>
<li>Follow the journal's Author Guidelines for presentation and references.</li>
</ul>
<p>Check every requirement before submission. Manuscripts that do not meet the stated conditions may be returned for revision.</p>
<p>Adapted from the <a href="https://www.eelet.org.uk/index.php/journal/about/submissions">submission instructions</a>; reviewed 15 November 2026.</p>""",
    },
)


def upgrade():
    pages = sa.table("web_pages",
        sa.column("title", sa.String(150)),
        sa.column("slug", sa.String(150)),
        sa.column("content_html", sa.Text()),
        sa.column("created_at", sa.DateTime(timezone=True)),
        sa.column("updated_at", sa.DateTime(timezone=True)))
    connection = op.get_bind()
    timestamp = datetime.now(timezone.utc)
    for page in PAGES:
        existing = connection.execute(sa.select(pages.c.slug).where(pages.c.slug == page["slug"])).first()
        if existing is None:
            connection.execute(pages.insert().values(**page, created_at=timestamp, updated_at=timestamp))


def downgrade():
    # Seeded pages may have been edited or selected for use. Keep all editorial content.
    pass
