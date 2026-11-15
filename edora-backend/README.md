# Edora backend

Python 3.12+, FastAPI, SQLAlchemy, PostgreSQL, Alembic migrations, Argon2 password hashes, SMTP emails, and revocable opaque sessions.

## Option A — simplest start (Docker)
Install Docker Desktop with Compose v2, then run:
```sh
docker compose up --build
```
No local Python or PostgreSQL installation is needed for this option. PostgreSQL starts first; the API automatically applies migrations before listening.

| Service | URL |
|---|---|
| API | http://localhost:8000 |
| Swagger/OpenAPI UI | http://localhost:8000/docs |
| Health | http://localhost:8000/health |
| Local email inbox | http://localhost:8025 |
| PostgreSQL | localhost:5432; database/user/password: edora |

Leave this terminal open, and start the separate frontend. Mailpit captures all emails locally; no real SMTP account is required.

```sh
docker compose down        # stop; preserve database volume
docker compose logs api    # API logs
```
`docker compose down -v` permanently deletes the local database volume. Use it only when intentionally resetting development data.

## Option B — Python development with Docker dependencies
Start only PostgreSQL and Mailpit:
```sh
docker compose up -d db mailpit
python -m venv .venv
```
Windows PowerShell:
```powershell
.venv\Scripts\Activate.ps1
Copy-Item .env.example .env
```
macOS/Linux:
```sh
source .venv/bin/activate
cp .env.example .env
```
Then on either platform:
```sh
python -m pip install -r requirements.txt
alembic upgrade head
uvicorn app.main:app --reload --port 8000
```
If activation is restricted in PowerShell, invoke `.venv\Scripts\python.exe -m pip ...`, `.venv\Scripts\alembic.exe upgrade head`, and `.venv\Scripts\python.exe -m uvicorn app.main:app --reload --port 8000` directly.

Do not run the Docker API and native API simultaneously on port 8000. Stop the container with `docker compose stop api` before native development.

## Option C — fully native dependencies
Install PostgreSQL 16+ and Mailpit separately. Create the database using psql as your database administrator:
```sql
CREATE USER edora WITH PASSWORD 'edora';
CREATE DATABASE edora OWNER edora;
```
Start Mailpit (its defaults are SMTP 1025, UI 8025), or configure a real SMTP provider. Follow the virtual-environment, install, migrate, and uvicorn steps from Option B without its Docker command.

## Configuration
Copy `.env.example` to `.env`. All commands must run from this project directory. Native mode reads `.env`; Docker Compose explicitly configures container service addresses in compose.yaml and does not use your native `.env` values for those fields.

| Variable | Purpose |
|---|---|
| DATABASE_URL | SQLAlchemy URL: `postgresql+psycopg://user:password@host:5432/database` |
| FRONTEND_URL | Verification link origin; default http://localhost:3000 |
| SMTP_HOST / SMTP_PORT | Mailpit localhost:1025 or provider STARTTLS endpoint |
| SMTP_USERNAME / SMTP_PASSWORD | Optional SMTP authentication |
| SMTP_STARTTLS | true for provider STARTTLS; false for local Mailpit |
| EMAIL_FROM | Sender address; use a verified sender with real providers |
| CONTACT_TO | Recipient of contact notifications |
| SESSION_HOURS | Session lifetime, default 24 hours |
| VERIFICATION_MINUTES | Verification link lifetime, default 60 minutes |

SMTP uses plain SMTP or STARTTLS, not implicit TLS on port 465. Configure a provider's STARTTLS port, commonly 587. Never commit real `.env` credentials. Docker service ports are bound to loopback for local use.

## Database migrations
```sh
alembic upgrade head
alembic current
alembic revision --autogenerate -m "describe schema change"
# Review the generated migration, then:
alembic upgrade head
```
`alembic downgrade -1` reverses one revision and can destroy data; use only deliberately on disposable development data. No automatic `create_all()` runs in the app: migrations own the schema. To execute commands inside Docker, prefix them with `docker compose exec api`.

Tables: `editors`, `verifications`, `sessions`, `contacts`. Passwords use Argon2 hashes. Session and verification tokens use SHA-256 hashes in the database; raw tokens are issued only to the authenticated caller or email recipient. Verification links are single-use and expire. Resending invalidates previous links. Email addresses are normalized to lowercase and enforced unique by PostgreSQL.

## API endpoints
All application endpoints are prefixed `/api/v1`.

| Method | Path | Input / result |
|---|---|---|
| POST | `/auth/register` | first_name, last_name, phone, gender, email, password → 202 |
| POST | `/auth/resend-verification` | email → 202 |
| POST | `/auth/verify-email` | token → confirmation |
| POST | `/auth/login` | email, password → bearer token, expiry |
| GET | `/auth/me` | bearer token → editor profile |
| POST | `/auth/logout` | bearer token → 204, revoked session |
| POST | `/contact` | name, email, message → persisted message acknowledgement |
| GET | `/health` | process liveness only; does not probe DB/SMTP |

Use Swagger at `/docs` for request schemas. After login, paste access_token into Swagger's Authorize dialog. Password is at least 12 characters at registration. Gender values: Male, Female, Other, Prefer not to say. Phone accepts an optional leading + and 7–25 digits/spaces/parentheses/hyphens.

Registration and resend use generic acknowledgements to avoid explicitly revealing whether an email exists. An SMTP failure does not delete the account: fix SMTP and resend. Contact messages remain saved even if notification delivery fails. Logs omit token/email body content.

## Tests
```sh
python -m pytest -q
```
Default tests use a temporary SQLite database to exercise endpoint behavior and mocked SMTP without external services. To validate the same tests and migrations against PostgreSQL, create a dedicated disposable test database:
```sh
docker compose exec db createdb -U edora edora_test
```
Then set `TEST_DATABASE_URL=postgresql+psycopg://edora:edora@localhost:5432/edora_test` in your shell and run pytest. PowerShell: `$env:TEST_DATABASE_URL="postgresql+psycopg://edora:edora@localhost:5432/edora_test"`. POSIX: `export TEST_DATABASE_URL='postgresql+psycopg://edora:edora@localhost:5432/edora_test'`.

The integration fixture applies Alembic revisions and deletes test records before each test. Never point TEST_DATABASE_URL at a database with data you want to keep.

## Production boundaries
Add distributed rate limiting, durable email queue/retries, password reset, expired-token cleanup, HTTPS, secure cookies, monitoring and database backups before public deployment. Cookie/CSRF controls live in the Next.js internal API; direct API clients use Authorization bearer headers. Configure production origins and SMTP explicitly. Docker startup migrations are convenient locally; production should use one controlled migration job.

The exact tested dependency set is in `requirements-lock.txt`. For reproducible Python 3.12 installs, use `python -m pip install -r requirements-lock.txt`.
