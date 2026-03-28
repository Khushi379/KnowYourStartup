from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.engine import build_assessment
from app.schemas import InnovationInput, InnovationResponse

app = FastAPI(
    title="ForgeLink AI API",
    description="Open Innovation assessment API for Track 6 demo.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

frontend_dist = Path(__file__).resolve().parents[2] / "frontend" / "dist"


@app.get("/healthz")
def healthcheck() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/api/analyze", response_model=InnovationResponse)
def analyze_opportunity(payload: InnovationInput) -> InnovationResponse:
    return build_assessment(payload)


if frontend_dist.exists():
    assets_dir = frontend_dist / "assets"
    if assets_dir.exists():
        app.mount("/assets", StaticFiles(directory=assets_dir), name="assets")

    @app.get("/")
    def serve_frontend_root() -> FileResponse:
        return FileResponse(frontend_dist / "index.html")

    @app.get("/{full_path:path}")
    def serve_frontend(full_path: str) -> FileResponse:
        requested = frontend_dist / full_path
        if full_path and requested.exists() and requested.is_file():
            return FileResponse(requested)
        return FileResponse(frontend_dist / "index.html")
else:
    @app.get("/")
    def root() -> dict[str, str]:
        return {
            "message": "ForgeLink AI backend is running.",
            "docs": "/docs",
        }
