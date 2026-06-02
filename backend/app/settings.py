import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent.parent
STATIC_DIR = BASE_DIR / "frontend" / "static"
REPORTS_DIR = BASE_DIR / "backend" / "data" / "reports"
REPORTS_URL = "http://127.0.0.1:8000/reports"
TEMPLATES_DIR = BASE_DIR / "frontend" / "templates"