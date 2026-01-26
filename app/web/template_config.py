"""Jinja2 template configuration."""

from pathlib import Path

from fastapi.templating import Jinja2Templates

# Template directory is at app/templates/
BASE_DIR = Path(__file__).resolve().parent.parent
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))
