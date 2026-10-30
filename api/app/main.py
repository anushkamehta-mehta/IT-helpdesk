import logging

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from app.core.config import get_settings
from app.routers import admin, auth, categories, health, pages, tickets, users

app = FastAPI(title="IT Helpdesk API", version="1.0.0")

# Printed in the server terminal at startup so it is always clear which database is in use.
logging.getLogger("uvicorn.error").info("Database: %s", get_settings().database_label)

SAFE_METHODS = {"GET", "HEAD", "OPTIONS"}


@app.middleware("http")
async def csrf_guard(request: Request, call_next):
    """CSRF defence for cookie auth: state-changing requests must carry a custom header.

    Browsers cannot add custom headers cross-site without a CORS preflight, which our
    CORS policy refuses for unknown origins. Combined with SameSite=Lax cookies this
    blocks cross-site form posts.
    """
    if request.method not in SAFE_METHODS and request.headers.get("x-requested-with") != "fetch":
        return JSONResponse({"detail": "Missing X-Requested-With header"}, status_code=403)
    return await call_next(request)


# Added after csrf_guard so CORS is the outermost layer (CORS headers also on 403s).
origins = get_settings().cors_origin_list
if origins:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PATCH", "DELETE"],
        allow_headers=["Content-Type", "X-Requested-With"],
    )

# All API routes live under /api; the HTML pages and static files are served by the same app.
for r in (health.router, auth.router, categories.router, users.router, tickets.router, admin.router):
    app.include_router(r, prefix="/api")

class RevalidatedStaticFiles(StaticFiles):
    """Make browsers re-check static files on every load (cheap 304 via ETag) so JS/CSS updates show at once."""

    def file_response(self, *args, **kwargs):
        response = super().file_response(*args, **kwargs)
        response.headers["Cache-Control"] = "no-cache"
        return response


app.include_router(pages.router)
app.mount("/static", RevalidatedStaticFiles(directory=pages.STATIC_DIR), name="static")
