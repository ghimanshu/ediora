from datetime import datetime, timezone
import secrets
import string
from sqlalchemy import String, DateTime, Boolean, ForeignKey, Text, JSON, UniqueConstraint, CheckConstraint
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
    template_name: Mapped[str] = mapped_column(String(100))
    template_description: Mapped[str] = mapped_column(String(500))
    template_layout: Mapped[dict] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now, onupdate=now)

class EditorJournalPage(Base):
    __tablename__ = "editor_journal_pages"
    __table_args__ = (UniqueConstraint("journal_id", "slug", name="uq_journal_page_slug"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    journal_id: Mapped[int] = mapped_column(ForeignKey("editor_journals.id", ondelete="CASCADE"), index=True)
    title: Mapped[str] = mapped_column(String(150))
    slug: Mapped[str] = mapped_column(String(150))
    content_html: Mapped[str] = mapped_column(Text)
    position: Mapped[int] = mapped_column()
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now, onupdate=now)
