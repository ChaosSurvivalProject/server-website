"""Entry point for running the FastAPI server with uvicorn.

Usage:
    cd backend && python3 run.py
    # or
    python3 backend/run.py
"""
import os
import sys
from pathlib import Path

# Ensure the backend/ directory is on sys.path so `app.main:app` resolves
BACKEND_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BACKEND_DIR))

import uvicorn

if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=5000,
        reload=True,
        reload_dirs=[str(BACKEND_DIR / "app")],
    )