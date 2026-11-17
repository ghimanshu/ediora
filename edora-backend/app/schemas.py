from typing import Literal
from pydantic import BaseModel, EmailStr, Field, ConfigDict, field_validator

class EmailInput(BaseModel):
    email: EmailStr = Field(max_length=254)
    @field_validator("email")
    @classmethod
    def normalize(cls, value):
        return value.lower()

class ProfileFields(EmailInput):
    first_name: str = Field(min_length=1, max_length=80)
    last_name: str = Field(min_length=1, max_length=80)
    phone: str = Field(pattern=r"^\+?[0-9 ()-]{7,25}$")
    gender: Literal["Male", "Female", "Other", "Prefer not to say"]
    @field_validator("first_name", "last_name")
    @classmethod
    def nonblank(cls, value):
        if not value.strip():
            raise ValueError("Name cannot be blank")
        return value.strip()

class Register(ProfileFields):
    password: str = Field(min_length=12, max_length=128)

class EditorProfileInput(ProfileFields):
    model_config = ConfigDict(extra="forbid")

class Login(EmailInput):
    password: str = Field(min_length=1, max_length=128)

class TokenInput(BaseModel):
    token: str = Field(min_length=20, max_length=200)

class EditorOutput(EmailInput):
    id: int
    first_name: str
    last_name: str
    phone: str
    gender: str
    role: Literal["editor", "super_admin"]
    is_active: bool
    is_verified: bool
    model_config = ConfigDict(from_attributes=True)

class ContactInput(EmailInput):
    name: str = Field(min_length=1, max_length=100)
    message: str = Field(min_length=10, max_length=5000)

class AdminUserUpdate(Register):
    # All editable profile fields are required; passwords and roles cannot be changed here.
    password: None = None
    is_active: bool
    model_config = ConfigDict(extra="forbid")

class UserList(BaseModel):
    items: list[EditorOutput]
    total: int
