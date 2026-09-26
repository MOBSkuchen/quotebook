# QuoteBook

A minimalist, Wikipedia-styled site for browsing quotes. A SonVogel subsidiary.

- `data/` — the quote data itself (JSON files) and portrait media. This is the
  content that gets synced into the search database.
- `src/frontend/` — plain HTML/CSS/JS pages served by the backend.
- `src/backend/` — a FastAPI app that serves the frontend, exposes a small
  JSON API, and periodically reindexes `data/` into a local SQLite database
  for fast search. `run.py` is a standalone launcher for production that
  pulls the latest commit from GitHub and restarts the app when it changes.
- `docs/` — architecture, data schema, and deployment notes.

## Quick start (local development)

```
cd src/backend
python -m venv .venv
.venv\Scripts\activate      # Windows
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Then open http://127.0.0.1:8000/.

The app always reads quotes straight from the local `data/` folder - it has
no git dependency itself. See `docs/deployment.md` for `run.py`, the
standalone launcher that pulls new commits from GitHub and restarts the app
in production.

See `docs/data-schema.md` for how to add a new quote.
