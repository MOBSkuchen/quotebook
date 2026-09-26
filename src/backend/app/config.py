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

# Reindexes data/ off local disk into SQLite on this interval. Getting new
# commits (and therefore new data) onto disk in the first place is run.py's
# job, not this app's - see src/backend/run.py.
SYNC_INTERVAL_SECONDS = int(os.environ.get("QUOTEBOOK_SYNC_INTERVAL", "300"))
