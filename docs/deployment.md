# Deployment

## Environment variables

| Variable | Default | Purpose |
|---|---|---|
| `QUOTEBOOK_SYNC_SOURCE` | `local` | `local` reads `data/` off disk; `github` fetches from a GitHub repo. |
| `QUOTEBOOK_GITHUB_OWNER` | _(empty)_ | GitHub org/user, required for `github` mode. |
| `QUOTEBOOK_GITHUB_REPO` | _(empty)_ | Repo name, required for `github` mode. |
| `QUOTEBOOK_GITHUB_BRANCH` | `main` | Branch to sync from. |
| `QUOTEBOOK_GITHUB_TOKEN` | _(unset)_ | Optional PAT, only needed to raise the GitHub API rate limit or read a private repo. Only used for the `git/refs` and `git/trees` API calls; quote/media files are fetched from `raw.githubusercontent.com`, which isn't subject to the same limit. |
| `QUOTEBOOK_SYNC_INTERVAL` | `300` | Seconds between sync attempts once deployed. |

## Steps

1. Push this repository to GitHub (once you've decided on an org/repo name).
2. Deploy `src/backend` (a plain ASGI app, `app.main:app`) anywhere that can
   run a long-lived Python process — a small VPS, Render, Fly.io, etc. It
   needs no external database; SQLite lives on local disk
   (`src/backend/var/quotebook.db`), so use a host with persistent (not
   ephemeral) storage, or accept that the search index rebuilds from GitHub
   on cold start.
3. Set `QUOTEBOOK_SYNC_SOURCE=github`, `QUOTEBOOK_GITHUB_OWNER`, and
   `QUOTEBOOK_GITHUB_REPO`.
4. Set `SUBMIT_QUOTE_URL` in `src/frontend/js/config.js` to wherever you want
   "Submit a quote" contributions to go (e.g. a GitHub issue template or a
   `data/quotes/` PR template) — this is still a placeholder.
5. Fill in the About page content in `src/frontend/about.html` — currently a
   placeholder.

No CORS configuration is needed since the frontend and API are served from
the same origin.
