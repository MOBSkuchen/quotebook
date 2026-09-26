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

CREATE TABLE IF NOT EXISTS daily_quote (
    date TEXT PRIMARY KEY,
    quote_id TEXT NOT NULL
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


def rebuild(quotes) -> None:
    """Replace the entire quotes table + FTS index in one transaction.

    `quotes` is an iterable of (models.QuoteFile, media_url) pairs, where
    media_url is already fully resolved (a local /media/... path), or None
    if the quote has no media.
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


def get_daily_quote() -> Optional[dict]:
    """Returns today's curated quote, picking and persisting a new random
    one the first time it's asked for on a given day.

    Once picked, the same quote is returned all day (from `daily_quote`),
    regardless of how many times this is called or how many times the app
    restarts in between - the pick lives in the same SQLite file as the
    quote index, untouched by reindexing or by run.py's git resets.
    """
    conn = get_conn()
    try:
        today = date.today().isoformat()

        picked = conn.execute(
            "SELECT quote_id FROM daily_quote WHERE date = ?", (today,)
        ).fetchone()
        if picked is not None:
            row = conn.execute(
                "SELECT * FROM quotes WHERE id = ?", (picked["quote_id"],)
            ).fetchone()
            if row is not None:
                return _row_to_dict(row)
            # The picked quote no longer exists (e.g. removed from data/);
            # fall through and pick a fresh one for today instead.

        row = conn.execute("SELECT * FROM quotes ORDER BY RANDOM() LIMIT 1").fetchone()
        if row is None:
            return None

        with conn:
            conn.execute(
                """
                INSERT INTO daily_quote (date, quote_id) VALUES (?, ?)
                ON CONFLICT(date) DO UPDATE SET quote_id = excluded.quote_id
                """,
                (today, row["id"]),
            )
        return _row_to_dict(row)
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
