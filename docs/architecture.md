# Architecture

## Overview

One FastAPI process serves everything on a single origin:

- `GET /`, `/all`, `/about` — the three HTML pages (plain HTML/CSS/JS, no
  build step).
- `/css/*`, `/js/*` — static frontend assets.
- `/media/*` — local quote portraits (only used when `QUOTEBOOK_SYNC_SOURCE=local`;
  in `github` mode the API returns absolute `raw.githubusercontent.com` URLs
  instead).
- `/api/*` — the JSON API, backed by a local SQLite database.

Serving everything from one origin avoids CORS entirely and means the
frontend can just call relative `/api/...` URLs.

## Data flow

1. Quotes live as JSON files in `data/quotes/`, one file per quote, with
   portraits in `data/media/`. See `docs/data-schema.md`.
2. On startup, and then on a timer (`QUOTEBOOK_SYNC_INTERVAL`, default 300s),
   the backend syncs this data into a SQLite database
   (`src/backend/var/quotebook.db`, gitignored):
   - In `local` mode it reads the files directly off disk (used for
     development, before the repo has a public GitHub remote).
   - In `github` mode it fetches the branch head commit SHA first; if it
     hasn't changed since the last sync, nothing else happens. Otherwise it
     fetches the full file tree in one recursive `git/trees` call, downloads
     each `data/quotes/*.json` file from `raw.githubusercontent.com`,
     validates it, and rebuilds the whole `quotes` table in a single
     transaction. Rebuilding fully (rather than upserting) is what makes
     deleted/renamed quote files disappear from search correctly.
   - Invalid quote files are logged and skipped rather than failing the
     whole sync, so one bad file (e.g. from a community PR) can't take the
     site down.
3. The API reads only from SQLite, never from `data/` directly, so a page
   load never depends on GitHub being reachable.

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
clickable `<a>` if it matches `^https?://`.
