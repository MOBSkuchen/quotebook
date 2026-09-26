import logging
from pathlib import Path
from typing import Optional

import requests
from pydantic import ValidationError

from . import config, db
from .models import QuoteFile

logger = logging.getLogger("quotebook.sync")


def _local_media_url(image: str) -> str:
    return f"/media/{image}"


def _load_local_quotes() -> list[tuple[QuoteFile, Optional[str]]]:
    results = []
    seen_ids: set[str] = set()
    for path in sorted(config.DATA_QUOTES_DIR.glob("*.json")):
        try:
            raw = path.read_text(encoding="utf-8")
            qf = QuoteFile.model_validate_json(raw)
        except (ValidationError, ValueError) as exc:
            logger.warning("Skipping invalid quote file %s: %s", path.name, exc)
            continue

        if not path.stem.startswith(qf.filename_prefix()):
            logger.warning(
                "Skipping %s: filename date prefix does not match added=%s",
                path.name,
                qf.added,
            )
            continue

        if qf.id in seen_ids:
            logger.warning("Skipping %s: duplicate id %s", path.name, qf.id)
            continue
        seen_ids.add(qf.id)

        media_url = _local_media_url(qf.media.image) if qf.media else None
        results.append((qf, media_url))
    return results


def _github_headers() -> dict:
    headers = {"Accept": "application/vnd.github+json"}
    if config.GITHUB_TOKEN:
        headers["Authorization"] = f"Bearer {config.GITHUB_TOKEN}"
    return headers


def _fetch_branch_head_sha() -> str:
    url = (
        f"https://api.github.com/repos/{config.GITHUB_OWNER}/{config.GITHUB_REPO}"
        f"/git/refs/heads/{config.GITHUB_BRANCH}"
    )
    resp = requests.get(url, headers=_github_headers(), timeout=10)
    resp.raise_for_status()
    return resp.json()["object"]["sha"]


def _fetch_tree(sha: str) -> list[dict]:
    url = (
        f"https://api.github.com/repos/{config.GITHUB_OWNER}/{config.GITHUB_REPO}"
        f"/git/trees/{sha}?recursive=1"
    )
    resp = requests.get(url, headers=_github_headers(), timeout=20)
    resp.raise_for_status()
    return resp.json()["tree"]


def _github_media_url(image: str) -> str:
    # Media can stay pinned to the branch (not the commit): a stale portrait
    # for a moment after a push is harmless, unlike stale quote text.
    return (
        f"https://raw.githubusercontent.com/{config.GITHUB_OWNER}/"
        f"{config.GITHUB_REPO}/{config.GITHUB_BRANCH}/data/media/{image}"
    )


def _load_github_quotes() -> Optional[tuple[list[tuple[QuoteFile, Optional[str]]], str]]:
    """Returns None if the repo hasn't changed since the last successful sync.

    Otherwise returns (quotes, head_sha). The caller is responsible for
    recording head_sha as the last synced SHA only after a successful
    rebuild, so a failed rebuild is retried in full next time rather than
    silently skipped forever.
    """
    head_sha = _fetch_branch_head_sha()
    if db.get_sync_state("last_sha") == head_sha:
        return None

    tree = _fetch_tree(head_sha)
    quote_paths = [
        item["path"]
        for item in tree
        if item.get("type") == "blob"
        and item["path"].startswith("data/quotes/")
        and item["path"].endswith(".json")
    ]

    results = []
    seen_ids: set[str] = set()
    for path in quote_paths:
        # Fetched by commit SHA, not branch name: raw.githubusercontent.com
        # caches branch-name URLs, which could otherwise serve a stale (or
        # momentarily 404ing) file for a commit we're about to mark synced.
        raw_url = (
            f"https://raw.githubusercontent.com/{config.GITHUB_OWNER}/"
            f"{config.GITHUB_REPO}/{head_sha}/{path}"
        )
        # A network/HTTP failure here is not caught: it propagates out of
        # run_sync's try/except, which leaves the previous index and
        # last_sha untouched so this whole sync is retried next tick,
        # rather than silently publishing an index missing that quote.
        resp = requests.get(raw_url, timeout=10)
        resp.raise_for_status()

        try:
            qf = QuoteFile.model_validate_json(resp.content)
        except (ValidationError, ValueError) as exc:
            logger.warning("Skipping invalid quote %s: %s", path, exc)
            continue

        stem = Path(path).stem
        if not stem.startswith(qf.filename_prefix()):
            logger.warning(
                "Skipping %s: filename date prefix does not match added=%s",
                path,
                qf.added,
            )
            continue

        if qf.id in seen_ids:
            logger.warning("Skipping %s: duplicate id %s", path, qf.id)
            continue
        seen_ids.add(qf.id)

        media_url = _github_media_url(qf.media.image) if qf.media else None
        results.append((qf, media_url))

    return results, head_sha


def run_sync() -> None:
    try:
        if config.SYNC_SOURCE == "github":
            loaded = _load_github_quotes()
            if loaded is None:
                logger.info("GitHub repo unchanged since last sync, skipping rebuild")
                return
            quotes, head_sha = loaded
        else:
            quotes = _load_local_quotes()
            head_sha = None

        db.rebuild(quotes)
        if head_sha is not None:
            db.set_sync_state("last_sha", head_sha)
        logger.info("Sync complete: %d quotes indexed", len(quotes))
    except Exception:
        logger.exception("Sync failed; keeping previous index")
