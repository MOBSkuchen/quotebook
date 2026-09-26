import os
from pathlib import Path

# src/backend/app/config.py -> parents: app, backend, src, <repo root>
REPO_ROOT = Path(__file__).resolve().parents[3]

DATA_DIR = REPO_ROOT / "data"
DATA_QUOTES_DIR = DATA_DIR / "quotes"
DATA_MEDIA_DIR = DATA_DIR / "media"

FRONTEND_DIR = REPO_ROOT / "src" / "frontend"

VAR_DIR = Path(__file__).resolve().parents[1] / "var"
VAR_DIR.mkdir(exist_ok=True)
DB_PATH = VAR_DIR / "quotebook.db"

# "local" reads data/ directly off disk (used before a GitHub remote
# exists). "github" fetches from QUOTEBOOK_GITHUB_OWNER/QUOTEBOOK_GITHUB_REPO.
SYNC_SOURCE = os.environ.get("QUOTEBOOK_SYNC_SOURCE", "local")

GITHUB_OWNER = os.environ.get("QUOTEBOOK_GITHUB_OWNER", "")
GITHUB_REPO = os.environ.get("QUOTEBOOK_GITHUB_REPO", "")
GITHUB_BRANCH = os.environ.get("QUOTEBOOK_GITHUB_BRANCH", "main")
GITHUB_TOKEN = os.environ.get("QUOTEBOOK_GITHUB_TOKEN") or None

SYNC_INTERVAL_SECONDS = int(os.environ.get("QUOTEBOOK_SYNC_INTERVAL", "300"))
