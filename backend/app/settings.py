import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent.parent
STATIC_DIR = BASE_DIR / "frontend" / "static"
REPORTS_DIR = BASE_DIR / "backend" / "data" / "reports"
TEMPLATES_DIR = BASE_DIR / "frontend" / "templates"