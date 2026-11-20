from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.auth import router as auth_router
from app.api.incidents import router as incidents_router
from app.api.platform import router as platform_router
from app.api.websites import router as websites_router
from app.core.config import get_settings
from app.core.logging import configure_logging

configure_logging()
settings = get_settings()

app = FastAPI(
    title="AI-Based Incident Prediction and Root Cause Analysis",
    version="1.0.0",
    description="Monitor public websites, detect incidents, explain evidence, and keep simulation separate from live data.",
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(Exception)
async def unhandled(_request: Request, exc: Exception) -> JSONResponse:
    if isinstance(exc, HTTPException):
        return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})
    return JSONResponse(status_code=500, content={"detail": "Unexpected server error", "type": exc.__class__.__name__})


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "service": settings.app_name}


@app.get("/health/live")
def live() -> dict:
    return {"status": "live"}


app.include_router(auth_router, prefix=settings.api_v1_prefix)
app.include_router(websites_router, prefix=settings.api_v1_prefix)
app.include_router(incidents_router, prefix=settings.api_v1_prefix)
app.include_router(platform_router, prefix=settings.api_v1_prefix)
