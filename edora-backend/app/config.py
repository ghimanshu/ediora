from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    super_admin_email: str = ""
    super_admin_password: str = ""
    database_url: str = "postgresql+psycopg://edora:edora@localhost:5432/edora"
    frontend_url: str = "http://localhost:3000"
    smtp_host: str = "localhost"
    smtp_port: int = 1025
    smtp_username: str = ""
    smtp_password: str = ""
    smtp_starttls: bool = False
    email_from: str = "noreply@edora.local"
    contact_to: str = "support@edora.local"
    session_hours: int = 24
    verification_minutes: int = 60
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

settings = Settings()
