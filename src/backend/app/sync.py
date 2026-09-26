import logging
import re
from typing import Optional

from pydantic import ValidationError

from . import config, db
from .models import QuoteFile

logger = logging.getLogger("quotebook.sync")

_ABSOLUTE_URL_RE = re.compile(r"^https?://", re.IGNORECASE)


def _media_url(image: str) -> str:
    if _ABSOLUTE_URL_RE.match(image):
        return image
    return f"/media/{image}"


def _load_quotes() -> list[tuple[QuoteFile, Optional[str]]]:
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

        media_url = _media_url(qf.media.image) if qf.media else None
        results.append((qf, media_url))
    return results


def run_sync() -> None:
    try:
        quotes = _load_quotes()
        db.rebuild(quotes)
        logger.info("Reindexed %d quotes", len(quotes))
    except Exception:
        logger.exception("Reindex failed; keeping previous index")
