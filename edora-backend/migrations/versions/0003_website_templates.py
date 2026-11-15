"""Persist website templates and account selections, with two initial layouts."""
from datetime import datetime, timezone
from alembic import op
import sqlalchemy as sa
revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None

def upgrade():
    templates = op.create_table("website_templates",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(100), unique=True, nullable=False),
        sa.Column("description", sa.String(500), nullable=False),
        sa.Column("layout", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False))
    op.create_table("website_template_selections",
        sa.Column("editor_id", sa.Integer(), sa.ForeignKey("editors.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("template_id", sa.Integer(), sa.ForeignKey("website_templates.id"), nullable=False))
    op.create_index("ix_website_template_selections_template_id", "website_template_selections", ["template_id"])
    timestamp = datetime.now(timezone.utc)
    sections = [
        {"type": "header", "title": "Your website", "content": "A place for your ideas."},
        {"type": "menu", "title": "Explore", "content": "Home\nAbout\nArticles\nContact"},
        {"type": "content", "title": "Welcome to your website", "content": "Share your stories, showcase your work, and connect with your readers."},
        {"type": "footer", "title": "Stay connected", "content": "Your website. All rights reserved."}]
    op.bulk_insert(templates, [
        {"name": "Classic Journal", "description": "A full-width header, horizontal menu, central content, and footer.", "layout": {"menu_position": "top", "sections": sections}, "created_at": timestamp, "updated_at": timestamp},
        {"name": "Sidebar Studio", "description": "A full-width header and footer frame a left-hand menu beside the content.", "layout": {"menu_position": "left", "sections": sections}, "created_at": timestamp, "updated_at": timestamp}])

def downgrade():
    op.drop_table("website_template_selections")
    op.drop_table("website_templates")
