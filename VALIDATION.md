# Validation results

Validated on 14 November 2026 using Node.js 24 and Python 3.12.

- Next.js production build: passed.
- TypeScript type checking: passed.
- Six FastAPI integration tests: passed, using a temporary SQLite database and mocked SMTP.
- PostgreSQL-dialect migration SQL generation: passed.
- Live HTTP smoke test across Next.js and FastAPI: passed. Covered eight public/account page responses, protected dashboard redirect, registration, verification, login, profile, contact, logout, session revocation, HttpOnly cookie, no token in internal login response, rejected cross-origin mutation, and rejected non-allowlisted route.
- Dependency locks included: package-lock.json and requirements-lock.txt.

Limits: Docker Compose, live PostgreSQL, real SMTP delivery, browser interaction/visual layout, and Windows execution were not tested here. The live HTTP smoke test used SQLite and a captured email function. Follow the README smoke-test steps to verify Mailpit and PostgreSQL locally. One upstream Starlette/httpx deprecation warning occurred; tests passed.
