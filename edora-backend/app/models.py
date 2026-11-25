from datetime import datetime, timezone
import secrets
import string
from sqlalchemy import String, DateTime, Boolean, ForeignKey, Text, JSON, UniqueConstraint, CheckConstraint, ForeignKeyConstraint, LargeBinary
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base

def now():
    return datetime.now(timezone.utc)

def new_editor_code():
    return "".join(secrets.choice(string.ascii_lowercase + string.digits) for _ in range(8))

class Editor(Base):
    __tablename__ = "editors"
    id: Mapped[int] = mapped_column(primary_key=True)
    public_code: Mapped[str] = mapped_column(String(8), unique=True, default=new_editor_code)
    first_name: Mapped[str] = mapped_column(String(80))
    last_name: Mapped[str] = mapped_column(String(80))
    phone: Mapped[str] = mapped_column(String(25))
    gender: Mapped[str] = mapped_column(String(30))
    email: Mapped[str] = mapped_column(String(254), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    role: Mapped[str] = mapped_column(String(20), default="editor")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)

class Verification(Base):
    __tablename__ = "verifications"
    token_hash: Mapped[str] = mapped_column(String(64), primary_key=True)
    editor_id: Mapped[int] = mapped_column(ForeignKey("editors.id", ondelete="CASCADE"), index=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))

class Session(Base):
    __tablename__ = "sessions"
    token_hash: Mapped[str] = mapped_column(String(64), primary_key=True)
    editor_id: Mapped[int] = mapped_column(ForeignKey("editors.id", ondelete="CASCADE"), index=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))

class Contact(Base):
    __tablename__ = "contacts"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100))
    email: Mapped[str] = mapped_column(String(254))
    message: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class WebsiteTemplate(Base):
    __tablename__ = "website_templates"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100), unique=True)
    description: Mapped[str] = mapped_column(String(500), default="")
    layout: Mapped[dict] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now, onupdate=now)

class WebsiteTemplateSelection(Base):
    __tablename__ = "website_template_selections"
    editor_id: Mapped[int] = mapped_column(ForeignKey("editors.id", ondelete="CASCADE"), primary_key=True)
    template_id: Mapped[int] = mapped_column(ForeignKey("website_templates.id"), index=True)


class WebPage(Base):
    __tablename__ = "web_pages"
    menu_group: Mapped[str] = mapped_column(String(40), default="", server_default="")
    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(150))
    slug: Mapped[str] = mapped_column(String(150), unique=True)
    content_html: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now, onupdate=now)


class EditorJournal(Base):
    __tablename__ = "editor_journals"
    __table_args__ = (
        UniqueConstraint("editor_id", "slug", name="uq_editor_journal_slug"),
        CheckConstraint("status IN ('Draft', 'Published', 'NotPublished')", name="ck_journal_status"),
    )
    id: Mapped[int] = mapped_column(primary_key=True)
    editor_id: Mapped[int] = mapped_column(ForeignKey("editors.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(150))
    slug: Mapped[str] = mapped_column(String(150))
    status: Mapped[str] = mapped_column(String(20), default="Draft", server_default="Draft")
    menu_order: Mapped[list] = mapped_column(JSON, default=list, server_default="[]")
    journal_info: Mapped[dict] = mapped_column(JSON, default=dict, server_default="{}")
    template_name: Mapped[str] = mapped_column(String(100))
    template_description: Mapped[str] = mapped_column(String(500))
    template_layout: Mapped[dict] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now, onupdate=now)

class EditorJournalPage(Base):
    __tablename__ = "editor_journal_pages"
    __table_args__ = (UniqueConstraint("journal_id", "slug", name="uq_journal_page_slug"),)
    source_type: Mapped[str] = mapped_column(String(10), default="editor", server_default="editor")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true")
    menu_group: Mapped[str] = mapped_column(String(40), default="", server_default="")
    id: Mapped[int] = mapped_column(primary_key=True)
    journal_id: Mapped[int] = mapped_column(ForeignKey("editor_journals.id", ondelete="CASCADE"), index=True)
    title: Mapped[str] = mapped_column(String(150))
    slug: Mapped[str] = mapped_column(String(150))
    content_html: Mapped[str] = mapped_column(Text)
    position: Mapped[int] = mapped_column()
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now, onupdate=now)


class JournalIssue(Base):
    __tablename__ = "journal_issues"
    __table_args__ = (UniqueConstraint("id", "journal_id", name="uq_issue_journal"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    journal_id: Mapped[int] = mapped_column(ForeignKey("editor_journals.id", ondelete="CASCADE"), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    title: Mapped[str] = mapped_column(String(200))
    volume: Mapped[str] = mapped_column(String(40), default="")
    number: Mapped[str] = mapped_column(String(40), default="")
    is_archived: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")
    is_published: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

class JournalArticle(Base):
    __tablename__ = "journal_articles"
    __table_args__ = (
        ForeignKeyConstraint(["issue_id", "journal_id"], ["journal_issues.id", "journal_issues.journal_id"], name="fk_article_volume_journal"),
        CheckConstraint("pdf_size >= 0 AND pdf_size <= 10485760", name="ck_article_pdf_size"),
    )
    status: Mapped[str] = mapped_column(String(20), default=lambda context: "Published" if context.get_current_parameters().get("is_published") else "UnPublished", server_default="UnPublished")
    submitter_name: Mapped[str] = mapped_column(String(150), default="", server_default="")
    submitter_email: Mapped[str] = mapped_column(String(254), default="", server_default="")
    notification_sent: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")
    source_submission_id: Mapped[int | None] = mapped_column(nullable=True, unique=True)
    id: Mapped[int] = mapped_column(primary_key=True)
    journal_id: Mapped[int] = mapped_column(ForeignKey("editor_journals.id", ondelete="CASCADE"), index=True)
    issue_id: Mapped[int | None] = mapped_column(nullable=True, index=True)
    pdf_content: Mapped[bytes | None] = mapped_column(LargeBinary, nullable=True, deferred=True)
    pdf_filename: Mapped[str | None] = mapped_column(String(255), nullable=True)
    pdf_size: Mapped[int] = mapped_column(default=0, server_default="0")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now, onupdate=now)
    title: Mapped[str] = mapped_column(String(300))
    authors: Mapped[list] = mapped_column(JSON, default=list)
    how_to_cite: Mapped[str] = mapped_column(Text, default="", server_default="")
    abstract: Mapped[str] = mapped_column(Text, default="")
    article_url: Mapped[str] = mapped_column(String(2048), default="")
    position: Mapped[int] = mapped_column(default=0)
    is_published: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")

class SubmissionCaptcha(Base):
    __tablename__ = "submission_captchas"
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    journal_id: Mapped[int] = mapped_column(ForeignKey("editor_journals.id", ondelete="CASCADE"), index=True)
    answer_hash: Mapped[str] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))

class ManuscriptSubmission(Base):
    __tablename__ = "manuscript_submissions"
    id: Mapped[int] = mapped_column(primary_key=True)
    journal_id: Mapped[int] = mapped_column(ForeignKey("editor_journals.id", ondelete="CASCADE"), index=True)
    full_name: Mapped[str] = mapped_column(String(150))
    email: Mapped[str] = mapped_column(String(254))
    title: Mapped[str] = mapped_column(String(300))
    authors: Mapped[str] = mapped_column(String(2000))
    abstract: Mapped[str] = mapped_column(Text)
    pdf_content: Mapped[bytes] = mapped_column(LargeBinary, deferred=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    notification_sent: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")


class JournalDeployment(Base):
    __tablename__ = "journal_deployments"
    __table_args__ = (UniqueConstraint("journal_id", "version", name="uq_journal_deployment_version"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    journal_id: Mapped[int] = mapped_column(ForeignKey("editor_journals.id", ondelete="CASCADE"), index=True)
    version: Mapped[int] = mapped_column()
    page_count: Mapped[int] = mapped_column()
    snapshot: Mapped[dict] = mapped_column(JSON)
    website_zip: Mapped[bytes] = mapped_column(LargeBinary, deferred=True)
    requested_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
