from datetime import datetime
from html import unescape
import re
import nh3
from pydantic import BaseModel, ConfigDict, Field, field_validator

class PageInput(BaseModel):
    title: str = Field(min_length=1, max_length=150)
    slug: str = Field(min_length=1, max_length=150, pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
    content_html: str = Field(min_length=1, max_length=100000)
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    @field_validator("content_html")
    @classmethod
    def sanitize_html(cls, value):
        cleaned = nh3.clean(value,
            tags={"p", "h1", "h2", "h3", "h4", "h5", "h6", "strong", "b", "em", "i", "u", "s", "strike", "ul", "ol", "li", "blockquote", "pre", "code", "br", "hr", "a"},
            attributes={"a": {"href", "title", "target"}, "ol": {"start"}},
            url_schemes={"http", "https", "mailto", "tel"},
            clean_content_tags={"script", "style", "iframe", "object", "svg", "math"})
        text = unescape(re.sub(r"<[^>]*>", "", cleaned)).replace("\u200b", "").strip()
        if not text:
            raise ValueError("Page content must contain text")
        if len(cleaned) > 100000:
            raise ValueError("Page content exceeds 100000 characters after sanitization")
        return cleaned

class PageSummary(BaseModel):
    id: int
    title: str
    slug: str
    created_at: datetime
    updated_at: datetime
    model_config = ConfigDict(from_attributes=True)

class PageOutput(PageSummary):
    content_html: str
