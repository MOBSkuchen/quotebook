# Architecture

## Overview

Two processes, in production:

- **`run.py`** (`src/backend/run.py`) — a stdlib-only launcher. It runs the
  app as a child process, periodically pulls the latest commit from GitHub,
  and restarts the child when the checkout changes. See "Self-update" below.
- **The app** (`app.main:app`, run by `run.py` via `uvicorn`) — serves
  everything on a single origin:
  - `GET /`, `/all`, `/about` — the three HTML pages (plain HTML/CSS/JS, no
    build step).
  - `/css/*`, `/js/*`, `/media/*` — static frontend assets and quote
    portraits, read straight off local disk.
  - `/api/*` — the JSON API, backed by a local SQLite database.

Serving everything from one origin avoids CORS entirely and means the
frontend can just call relative `/api/...` URLs.

For local development you can skip `run.py` entirely and just run
`uvicorn app.main:app --reload` — the app itself has no git dependency.

## Data flow

1. Quotes live as JSON files in `data/quotes/`, one file per quote, with
   portraits in `data/media/`. See `docs/data-schema.md`.
2. On startup, and then on a timer (`QUOTEBOOK_SYNC_INTERVAL`, default 300s),
   the app reads `data/quotes/*.json` off local disk, validates each file,
   and rebuilds the whole `quotes` table (and its FTS index) in a single
   SQLite transaction (`src/backend/var/quotebook.db`, gitignored).
   Rebuilding fully (rather than upserting) is what makes deleted/renamed
   quote files disappear from search correctly. Invalid quote files are
   logged and skipped rather than failing the whole reindex, so one bad file
   (e.g. from a community PR) can't take the site down.
3. Getting new commits (and therefore new quote files) onto disk in the
   first place is entirely `run.py`'s job — see "Self-update" below. The app
   itself never talks to GitHub.

## Self-update (`run.py`)

`run.py` is deliberately simple and never imports the `app` package, so a
push that breaks the app (bad import, a dependency missing from the venv)
can only kill the child process, not the launcher responsible for pulling
the fix. On an interval (`QUOTEBOOK_UPDATE_INTERVAL`, default 300s) it:

1. Refuses to touch anything if the checkout has uncommitted local changes
   (`git status --porcelain`), so it never fights a developer running it
   locally.
2. Runs `git fetch origin <branch>` (`QUOTEBOOK_GIT_BRANCH`, default
   `master`) and compares `HEAD` against `origin/<branch>`.
3. If they differ: `git reset --hard origin/<branch>`; reinstalls
   dependencies if `requirements.txt` changed; gracefully stops the child
   (`SIGTERM`, then `SIGKILL` after 30s) and starts a new one.
4. If there was no update, but the child process has died on its own (e.g.
   a runtime crash unrelated to any deploy), it's restarted anyway.

The update check always runs first, on every tick, regardless of whether
the child is currently alive or crash-looping. This matters: if a bad push
crashes the child, every restart attempt fails again immediately with the
same error until a *newer* commit is pulled. Checking git unconditionally
- rather than only checking it when the child is healthy - is what lets a
pushed fix actually get noticed and recover the site, instead of the
crash-restart branch forever respawning the same broken code.

## Quote of the day

"Today's Quotes" on the landing page shows a single curated pick, not
quotes filtered by their `added` date. `GET /api/quotes/today` calls
`db.get_daily_quote()`, which:

1. Looks up today's date in the `daily_quote` table
   (`date TEXT PRIMARY KEY, quote_id TEXT`). If found and that quote still
   exists, returns it - so the same pick is served all day, across
   restarts, since this table lives in the same gitignored SQLite file as
   the search index and isn't touched by reindexing or `run.py`'s resets.
2. Otherwise (first request of a new day, or the previous pick's quote was
   since removed from `data/`), picks a random row from `quotes`
   (`ORDER BY RANDOM() LIMIT 1`), records it for today, and returns it.

## Search

Quotes are indexed into a SQLite FTS5 virtual table (`quotes_fts`) covering
the author name, media caption, and every stored translation. User search
input is tokenized down to `\w+` tokens and turned into a
`tok1* AND tok2*` prefix query, so punctuation the user types (`"`, `-`,
parentheses, etc.) can never produce an invalid FTS5 query string.

## Security notes

Quote content originates from a public GitHub repo and must be treated as
untrusted: the frontend renders all quote text via `textContent`/DOM APIs,
never `innerHTML` interpolation, and only renders an author link as a
clickable `<a>` if it matches `^https?://`. `media.image` can likewise be an
absolute `http(s)://` URL (used as-is as an `<img src>`) instead of a local
filename - same trust level as `author.link`, since both come from the same
data files.
