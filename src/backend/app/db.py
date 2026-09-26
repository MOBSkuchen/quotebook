import json
import re
import sqlite3
from datetime import date
from typing import Optional

from . import config

SCHEMA = """
CREATE TABLE IF NOT EXISTS quotes (
    id TEXT PRIMARY KEY,
    added TEXT NOT NULL,
    display_date TEXT NOT NULL,
    original_language TEXT NOT NULL,
    translations_json TEXT NOT NULL,
    author_name TEXT NOT NULL,
    author_link TEXT,
    media_url TEXT,
    media_caption TEXT
);

CREATE VIRTUAL TABLE IF NOT EXISTS quotes_fts USING fts5(
    id UNINDEXED,
    author_name,
    media_caption,
    translations_text,
    tokenize = 'unicode61 remove_diacritics 2'
);

CREATE TABLE IF NOT EXISTS sync_state (
    key TEXT PRIMARY KEY,
    value TEXT
);
"""


def get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(config.DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    conn = get_conn()
    try:
        with conn:
            conn.executescript(SCHEMA)
    finally:
        conn.close()


def get_sync_state(key: str) -> Optional[str]:
    conn = get_conn()
    try:
        row = conn.execute(
            "SELECT value FROM sync_state WHERE key = ?", (key,)
        ).fetchone()
        return row["value"] if row else None
    finally:
        conn.close()


def set_sync_state(key: str, value: str) -> None:
    conn = get_conn()
    try:
        with conn:
            conn.execute(
                """
                INSERT INTO sync_state (key, value) VALUES (?, ?)
                ON CONFLICT(key) DO UPDATE SET value = excluded.value
                """,
                (key, value),
            )
    finally:
        conn.close()


def rebuild(quotes) -> None:
    """Replace the entire quotes table + FTS index in one transaction.

    `quotes` is an iterable of (models.QuoteFile, media_url) pairs, where
    media_url is already fully resolved (a local /media/... path or an
    absolute raw.githubusercontent.com URL), or None if the quote has no
    media.
    """
    conn = get_conn()
    try:
        with conn:
            conn.execute("DELETE FROM quotes")
            conn.execute("DELETE FROM quotes_fts")
            for qf, media_url in quotes:
                media_caption = qf.media.caption if qf.media else None
                conn.execute(
                    """
                    INSERT INTO quotes (
                        id, added, display_date, original_language,
                        translations_json, author_name, author_link,
                        media_url, media_caption
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        qf.id,
                        qf.added,
                        qf.date,
                        qf.original_language,
                        json.dumps(qf.translations, ensure_ascii=False),
                        qf.author.name,
                        qf.author.link,
                        media_url,
                        media_caption,
                    ),
                )
                translations_text = " ".join(qf.translations.values())
                conn.execute(
                    """
                    INSERT INTO quotes_fts (id, author_name, media_caption, translations_text)
                    VALUES (?, ?, ?, ?)
                    """,
                    (qf.id, qf.author.name, media_caption or "", translations_text),
                )
    finally:
        conn.close()


def _row_to_dict(row: sqlite3.Row) -> dict:
    return {
        "id": row["id"],
        "added": row["added"],
        "date": row["display_date"],
        "original_language": row["original_language"],
        "translations": json.loads(row["translations_json"]),
        "author": {"name": row["author_name"], "link": row["author_link"]},
        "media": (
            {"url": row["media_url"], "caption": row["media_caption"]}
            if row["media_url"]
            else None
        ),
    }


def query_today() -> tuple[str, bool, list[dict]]:
    conn = get_conn()
    try:
        today = date.today().isoformat()
        rows = conn.execute(
            "SELECT * FROM quotes WHERE added = ? ORDER BY id", (today,)
        ).fetchall()
        used_date = today
        is_fallback = False
        if not rows:
            latest = conn.execute("SELECT MAX(added) AS m FROM quotes").fetchone()
            if latest and latest["m"]:
                used_date = latest["m"]
                is_fallback = True
                rows = conn.execute(
                    "SELECT * FROM quotes WHERE added = ? ORDER BY id", (used_date,)
                ).fetchall()
        return used_date, is_fallback, [_row_to_dict(r) for r in rows]
    finally:
        conn.close()


def sanitize_fts_query(q: str) -> Optional[str]:
    tokens = re.findall(r"\w+", q, re.UNICODE)
    if not tokens:
        return None
    # Tokens are quoted (not bare) so that a token which happens to match an
    # FTS5 keyword (AND, OR, NOT) is treated as a search term rather than as
    # that operator, which would otherwise raise a syntax error.
    return " AND ".join(f'"{t}"*' for t in tokens)


def query_quotes(q: Optional[str], page: int, page_size: int) -> tuple[list[dict], int]:
    conn = get_conn()
    try:
        offset = (page - 1) * page_size
        if q:
            safe_q = sanitize_fts_query(q)
            if not safe_q:
                return [], 0
            rows = conn.execute(
                """
                SELECT quotes.* FROM quotes
                JOIN quotes_fts ON quotes.id = quotes_fts.id
                WHERE quotes_fts MATCH ?
                ORDER BY quotes.added DESC, quotes.id DESC
                LIMIT ? OFFSET ?
                """,
                (safe_q, page_size, offset),
            ).fetchall()
            total = conn.execute(
                "SELECT COUNT(*) AS c FROM quotes_fts WHERE quotes_fts MATCH ?",
                (safe_q,),
            ).fetchone()["c"]
        else:
            rows = conn.execute(
                "SELECT * FROM quotes ORDER BY added DESC, id DESC LIMIT ? OFFSET ?",
                (page_size, offset),
            ).fetchall()
            total = conn.execute("SELECT COUNT(*) AS c FROM quotes").fetchone()["c"]
        return [_row_to_dict(r) for r in rows], total
    finally:
        conn.close()
