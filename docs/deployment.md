# Deployment

## Environment variables

| Variable | Default | Purpose |
|---|---|---|
| `QUOTEBOOK_GIT_BRANCH` | `master` | Branch `run.py` tracks for self-update. |
| `QUOTEBOOK_UPDATE_INTERVAL` | `300` | Seconds between `run.py` update checks. |
| `QUOTEBOOK_SYNC_INTERVAL` | `300` | Seconds between the app's own reindex-from-disk ticks. |

## Steps

1. **Deploy with `git clone`, not a downloaded archive.** `run.py` needs
   `.git` present and an `origin` remote configured, since it works by
   running real `git` commands against the checkout:
   ```
   git clone https://github.com/<owner>/<repo>.git
   cd <repo>/src/backend
   python -m venv .venv
   .venv/bin/pip install -r requirements.txt   # .venv\Scripts\pip on Windows
   ```
2. The host needs `git` on `PATH`. If the process runs as a user that
   doesn't own the checkout, git will refuse with "dubious ownership" -
   run `git config --global --add safe.directory <path-to-repo>` as that
   user. Without it, `run.py` logs a warning on every check and the site
   silently never updates.
3. Run the launcher from `src/backend`, using the venv's Python:
   ```
   .venv/bin/python run.py --host 0.0.0.0 --port 8000
   ```
   Any extra arguments after `run.py` are forwarded straight to `uvicorn`.
   This needs no external database; SQLite lives on local disk
   (`src/backend/var/quotebook.db`), so use a host with persistent (not
   ephemeral) storage.
4. `run.py` itself just needs to keep running - it isn't a systemd service,
   Docker container, etc. by itself. Wrapping it in one (`Restart=always` in
   a systemd unit, or a Docker restart policy) is optional but recommended
   so the launcher itself comes back after a host reboot or an out-of-memory
   kill; it is not required for picking up new commits, which `run.py`
   already handles on its own.
5. On a host with native git-push deploys (Render, Fly.io, etc.), prefer
   that over `run.py`'s polling - just run `uvicorn app.main:app` directly
   and let the platform redeploy on push.
6. Set `SUBMIT_QUOTE_URL` in `src/frontend/js/config.js` to wherever you want
   "Submit a quote" contributions to go (e.g. a GitHub issue template or a
   `data/quotes/` PR template).
7. Fill in the About page content in `src/frontend/about.html` — currently a
   placeholder.

No CORS configuration is needed since the frontend and API are served from
the same origin.

## Self-update caveats

- `run.py` refuses to update (and just logs a warning) if the checkout has
  uncommitted local changes. This is a safety net, not something to rely
  on - the deployed checkout should never be hand-edited.
- A restart drops any requests in flight to the old process; `run.py` sends
  `SIGTERM` first (uvicorn finishes in-flight requests on Linux before
  exiting) and only force-kills after a 30s grace period, but there is no
  zero-downtime handoff between old and new processes.
- If a pushed commit breaks the app (bad import, missing dependency), the
  child process dies but `run.py` keeps running and keeps checking for
  updates, so pushing a fix recovers the site automatically - see
  `docs/architecture.md`.
