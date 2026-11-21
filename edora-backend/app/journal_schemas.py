from datetime import datetime
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field, StrictInt, field_validator, model_validator
from app.page_schemas import PageInput, PageOutput
from app.template_schemas import TemplateLayout

JournalStatus = Literal["Draft", "Published", "NotPublished"]

class JournalStatusUpdate(BaseModel):
    status: JournalStatus
    model_config = ConfigDict(extra="forbid")

class JournalInfo(BaseModel):
    editor_in_chief: str = Field(default="", max_length=150)
    frequency: str = Field(default="", max_length=150)
    final_decision: str = Field(default="", max_length=150)
    acceptance_rate: str = Field(default="", max_length=150)
    plagiarism: str = Field(default="", max_length=150)
    language: str = Field(default="", max_length=150)
    review_process: str = Field(default="", max_length=150)
    open_access: str = Field(default="", max_length=150)
    copyright: str = Field(default="", max_length=150)
    eissn: str = Field(default="", max_length=150)
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

class JournalCreate(BaseModel):
    name: str = Field(min_length=1, max_length=150)
    template_id: int = Field(gt=0)
    page_ids: list[int] = Field(default_factory=list, max_length=100)
    new_pages: list[PageInput] = Field(default_factory=list, max_length=100)
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    @field_validator("page_ids")
    @classmethod
    def unique_pages(cls, values):
        if any(isinstance(value, int) and value <= 0 for value in values) or len(set(values)) != len(values):
            raise ValueError("Choose distinct valid pages")
        return values

    @model_validator(mode="after")
    def validate_pages(self):
        if not 1 <= len(self.page_ids) + len(self.new_pages) <= 100:
            raise ValueError("Include between 1 and 100 pages in total")
        slugs = [page.slug for page in self.new_pages]
        if len(slugs) != len(set(slugs)):
            raise ValueError("New pages must have different URL slugs")
        if sum(len(page.content_html) for page in self.new_pages) > 1000000:
            raise ValueError("Combined new page HTML must not exceed 1000000 characters")
        return self

class JournalOutput(BaseModel):
    menu_order: list[str] = Field(default_factory=list)
    journal_info: JournalInfo = Field(default_factory=JournalInfo)
    status: JournalStatus
    editor_code: str
    slug: str
    preview_path: str
    id: int
    name: str
    template_name: str
    template_description: str
    template_layout: TemplateLayout
    pages: list[PageOutput]
    created_at: datetime
    updated_at: datetime


class PublicJournalPage(BaseModel):
    title: str
    slug: str
    content_html: str

class PublicJournal(BaseModel):
    menu_order: list[str] = Field(default_factory=list)
    editor_email: str
    journal_info: JournalInfo = Field(default_factory=JournalInfo)
    name: str
    slug: str
    editor_code: str
    template_layout: TemplateLayout
    pages: list[PublicJournalPage]


class JournalPageOrder(BaseModel):
    page_ids: list[StrictInt | Literal["current", "archives", "submission"]] = Field(min_length=1, max_length=103)
    model_config = ConfigDict(extra="forbid")

    @field_validator("page_ids")
    @classmethod
    def unique_positive_ids(cls, values):
        if any(isinstance(value, int) and value <= 0 for value in values) or len(values) != len(set(values)):
            raise ValueError("Include each journal page exactly once")
        return values


class JournalSummary(BaseModel):
    status: JournalStatus
    id: int
    name: str
    slug: str
    template_name: str
    page_count: int
    created_at: datetime
    updated_at: datetime
