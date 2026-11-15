# Edora — two-project starter

Two independently runnable projects: `edora-frontend` (Next.js + TypeScript) and `edora-backend` (Python + FastAPI + PostgreSQL).

## Fastest local start
Install Docker Desktop with Compose v2 and Node.js 22 LTS (22.9+). Start Docker Desktop.

Terminal 1:
```sh
cd edora-backend
docker compose up --build
```
The API container waits for PostgreSQL, runs Alembic migrations, and starts FastAPI.

Terminal 2:
```sh
cd edora-frontend
npm ci
npm run dev
```
Open http://localhost:3000. Register, open the captured email at http://localhost:8025, click its verification link, click **Verify my email**, then log in. Local Mailpit captures messages; it never delivers them to a real inbox.

Detailed native Python setup, Windows instructions, configuration, API documentation, migrations, troubleshooting, and test commands are in each project's README.

## Architecture
Browser → Next.js pages and `/api/*` internal routes → FastAPI `/api/v1/*` → PostgreSQL and SMTP.

Python belongs to the backend. Next.js runs on Node.js with TypeScript; embedding another Python server in the frontend is unnecessary. The internal API is a restricted backend-for-frontend proxy. Browser JavaScript does not receive session tokens: the Next.js server sets an HttpOnly cookie and passes its value to FastAPI. The dashboard validates the session server-side.

## Scope
Four public pages: Home, About us, For editors, Contact us. Account pages: registration, login, verification, resend verification, and protected editor profile. Registration includes the requested five fields plus password and password confirmation. All registered users are editors. No admin, article review, payment, or password-reset workflow is included.

## Directory map
| Project path | Responsibility |
|---|---|
| `edora-frontend/src/app` | Public/account pages, layout, styling |
| `edora-frontend/src/app/api/[...path]/route.ts` | Allowlisted internal API, cookies, origin validation |
| `edora-frontend/src/components` | Navigation and reusable account/contact forms |
| `edora-frontend/src/lib/api.ts` | Browser API client and validation errors |
| `edora-backend/app/main.py` | FastAPI bootstrap and health endpoint |
| `edora-backend/app/routes.py` | Authentication, verification, profile, contact endpoints |
| `edora-backend/app/models.py` | SQLAlchemy entities |
| `edora-backend/app/schemas.py` | Request validation and public response schemas |
| `edora-backend/app/security.py` | Argon2 password hashing and opaque token hashing |
| `edora-backend/app/emails.py` | SMTP delivery |
| `edora-backend/app/database.py` | Database sessions and model base |
| `edora-backend/migrations` | Alembic migration environment and revisions |
| `edora-backend/tests` | Authentication and contact integration tests |
| `edora-backend/compose.yaml` | Local PostgreSQL, Mailpit, and API |

## Local starter boundaries
This is a functional local starter, not a production deployment. Before public hosting, add distributed rate limiting for login, registration, resend and contact; durable email retries/outbox; password recovery; session/token cleanup; monitoring; backup/restore; privacy/retention policy; HTTPS and secure cookies. Compose credentials are local development values only. SMTP delivery is synchronous with a 10-second timeout; verification send failures retain the account for resend, contact failures retain the database message. Email delivery is not guaranteed by the registration acknowledgement.

Framework references: https://nextjs.org/docs/app/getting-started/route-handlers and https://fastapi.tiangolo.com/tutorial/security/oauth2-jwt/ . This starter uses revocable opaque sessions, not JWTs.
