"""Run with python -m app.seed_admin after migrations. Never overwrites existing accounts."""
from sqlalchemy import select
from pydantic import EmailStr, TypeAdapter
from app.config import settings
from app.database import SessionLocal
from app.models import Editor
from app.security import password_hasher

def seed_admin():
    email = str(TypeAdapter(EmailStr).validate_python(settings.super_admin_email)).lower()
    password = settings.super_admin_password
    if not 12 <= len(password) <= 128:
        raise ValueError("SUPER_ADMIN_PASSWORD must contain 12 to 128 characters")
    with SessionLocal() as db:
        existing = db.scalar(select(Editor).where(Editor.email == email))
        if existing:
            if existing.role != "super_admin":
                raise ValueError("Email belongs to an existing editor; choose a different admin email")
            return False
        db.add(Editor(email=email, password_hash=password_hasher.hash(password),
                      first_name="Super", last_name="Admin", phone="", gender="Prefer not to say",
                      role="super_admin", is_active=True, is_verified=True))
        db.commit()
        return True

if __name__ == "__main__":
    print("Super admin created." if seed_admin() else "Super admin already exists; unchanged.")
