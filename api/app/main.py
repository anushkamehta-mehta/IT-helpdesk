from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.core.config import get_settings
from app.routers import auth, categories, health, tickets, users

app = FastAPI(title="IT Helpdesk API", version="1.0.0")

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
        allow_methods=["GET", "POST", "PATCH"],
        allow_headers=["Content-Type", "X-Requested-With"],
    )

# All API routes live under /api so Nginx can route /api/* to this service.
for r in (health.router, auth.router, categories.router, users.router, tickets.router):
    app.include_router(r, prefix="/api")
