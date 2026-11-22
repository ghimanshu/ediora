from datetime import datetime
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

class TemplateSection(BaseModel):
    type: Literal["header", "menu", "content", "footer"]
    title: str = Field(min_length=1, max_length=100)
    content: str = Field(default="", max_length=2000)
    background_color: str | None = Field(default=None, pattern=r"^#[0-9a-fA-F]{6}$")
    text_color: str | None = Field(default=None, pattern=r"^#[0-9a-fA-F]{6}$")
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    @model_validator(mode="after")
    def default_colors(self):
        defaults = {
            "header": ("#244c40", "#ffffff"),
            "menu": ("#e9e4d9", "#6b604a"),
            "content": ("#ffffff", "#243b36"),
            "footer": ("#dfe9e3", "#496453"),
        }
        background, text = defaults[self.type]
        self.background_color = (self.background_color or background).lower()
        self.text_color = (self.text_color or text).lower()
        return self

class TemplateLayout(BaseModel):
    show_downloads: bool = True
    show_journal_info: bool = True
    show_submissions: bool | None = None
    menu_position: Literal["top", "left", "right"]
    sections: list[TemplateSection] = Field(min_length=4, max_length=4)
    model_config = ConfigDict(extra="forbid")

    @field_validator("sections")
    @classmethod
    def complete_sections(cls, sections):
        if {s.type for s in sections} != {"header", "menu", "content", "footer"}:
            raise ValueError("Include exactly one header, menu, content, and footer")
        return sections

class TemplateInput(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    description: str = Field(default="", max_length=500)
    layout: TemplateLayout
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

class TemplateOutput(TemplateInput):
    id: int
    created_at: datetime
    updated_at: datetime
    model_config = ConfigDict(from_attributes=True)

class TemplateChoice(BaseModel):
    template_id: int = Field(gt=0)
    model_config = ConfigDict(extra="forbid")
