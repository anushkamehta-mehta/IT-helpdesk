"""Vercel entry point: exposes the FastAPI app that lives in api/app/.

Locally, keep running it from api/:  uvicorn app.main:app --reload --port 8000
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "api"))

from app.main import app  # noqa: E402,F401
