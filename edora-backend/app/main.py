import hmac
from fastapi import Request
from fastapi.responses import JSONResponse
from app.config import settings
from fastapi import FastAPI
from app.routes import router
from app.template_routes import router as template_router

from app.page_routes import router as page_router

from app.journal_routes import router as journal_router

from app.public_journal_routes import router as public_journal_router

from app.admin_journal_routes import router as admin_journal_router

from app.journal_feed_routes import router as journal_feed_router

from app.article_volume_routes import router as article_volume_router

from app.submission_routes import router as submission_router


app = FastAPI(title="Edora API", version="1.0.0")
@app.middleware("http")
async def require_internal_gateway(request: Request, call_next):
    if request.method not in {"GET", "HEAD", "OPTIONS"}:
        if not settings.internal_api_key:
            return JSONResponse({"detail": "Internal API gateway is not configured"},status_code=503)
        supplied=request.headers.get("x-internal-api-key", "")
        if not hmac.compare_digest(supplied,settings.internal_api_key):
            return JSONResponse({"detail": "Use the website internal API"},status_code=403)
    return await call_next(request)

app.include_router(router)
app.include_router(template_router)
app.include_router(page_router)
app.include_router(journal_router)
app.include_router(public_journal_router)
app.include_router(admin_journal_router)
app.include_router(journal_feed_router)
app.include_router(article_volume_router)
app.include_router(submission_router)

@app.get("/health")
def health():
    return {"status": "ok"}
