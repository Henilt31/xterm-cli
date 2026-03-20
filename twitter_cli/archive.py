"""Local SQLite archive for twitter-cli.

Persists fetched tweets to a local SQLite database so you can
search your history offline without hitting the Twitter API.

Database location (in order of preference):
    $TWITTER_ARCHIVE_PATH   — explicit env override
    ~/.twitter_cli/archive.db  — default

Usage (via CLI):
    twitter archive list            # list all archived fetch sessions
    twitter archive search "AI"     # full-text search across archived tweets
    twitter archive stats           # show row counts and top authors
    twitter archive clear           # delete all archived data (with confirmation)

The module also exposes helpers used internally by feed/search commands
when --archive flag is passed.
"""

from __future__ import annotations

import os
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence

from .models import Tweet
from .serialization import tweet_to_dict


# ---------------------------------------------------------------------------
# DB location
# ---------------------------------------------------------------------------

def _db_path() -> Path:
    explicit = os.environ.get("TWITTER_ARCHIVE_PATH", "")
    if explicit:
        return Path(explicit)
    base = Path.home() / ".twitter_cli"
    base.mkdir(parents=True, exist_ok=True)
    return base / "archive.db"


# ---------------------------------------------------------------------------
# Schema
# ---------------------------------------------------------------------------

_DDL = """
CREATE TABLE IF NOT EXISTS tweets (
    id          TEXT PRIMARY KEY,
    author      TEXT NOT NULL,
    screen_name TEXT NOT NULL,
    text        TEXT NOT NULL,
    lang        TEXT,
    likes       INTEGER DEFAULT 0,
    retweets    INTEGER DEFAULT 0,
    replies     INTEGER DEFAULT 0,
    views       INTEGER DEFAULT 0,
    score       REAL,
    created_at  TEXT,
    fetched_at  TEXT NOT NULL,
    source      TEXT,
    raw_json    TEXT
);

CREATE VIRTUAL TABLE IF NOT EXISTS tweets_fts
    USING fts5(id UNINDEXED, text, author, screen_name, content='tweets', content_rowid='rowid');

CREATE TRIGGER IF NOT EXISTS tweets_ai AFTER INSERT ON tweets BEGIN
    INSERT INTO tweets_fts(rowid, id, text, author, screen_name)
    VALUES (new.rowid, new.id, new.text, new.author, new.screen_name);
END;

CREATE TRIGGER IF NOT EXISTS tweets_ad AFTER DELETE ON tweets BEGIN
    INSERT INTO tweets_fts(tweets_fts, rowid, id, text, author, screen_name)
    VALUES ('delete', old.rowid, old.id, old.text, old.author, old.screen_name);
END;
"""


def _connect() -> sqlite3.Connection:
    conn = sqlite3.connect(str(_db_path()))
    conn.row_factory = sqlite3.Row
    conn.executescript(_DDL)
    conn.commit()
    return conn


# ---------------------------------------------------------------------------
# Write helpers
# ---------------------------------------------------------------------------

def save_tweets(tweets: Sequence[Tweet], source: str = "feed") -> int:
    """Persist tweets to the local archive.

    Args:
        tweets: Tweets to save.
        source: Label for where they came from (e.g. "feed", "search:AI").

    Returns:
        Number of new rows inserted (duplicates are ignored via INSERT OR IGNORE).
    """
    if not tweets:
        return 0
    fetched_at = datetime.now(timezone.utc).isoformat()
    rows = []
    for t in tweets:
        raw = tweet_to_dict(t)
        import json as _json
        rows.append((
            t.id,
            t.author.name,
            t.author.screen_name,
            t.text,
            t.lang,
            t.metrics.likes,
            t.metrics.retweets,
            t.metrics.replies,
            t.metrics.views,
            t.score,
            t.created_at,
            fetched_at,
            source,
            _json.dumps(raw, ensure_ascii=False),
        ))
    with _connect() as conn:
        cur = conn.executemany(
            """
            INSERT OR IGNORE INTO tweets
              (id, author, screen_name, text, lang,
               likes, retweets, replies, views, score,
               created_at, fetched_at, source, raw_json)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            """,
            rows,
        )
        conn.commit()
        return cur.rowcount


# ---------------------------------------------------------------------------
# Read helpers
# ---------------------------------------------------------------------------

def search_archive(query: str, limit: int = 50) -> List[Dict[str, Any]]:
    """Full-text search over archived tweet text, author, screen_name.

    Args:
        query: FTS5 query string (supports AND, OR, phrase "..." etc.).
        limit: Max results to return.

    Returns:
        List of row dicts ordered by FTS rank.
    """
    with _connect() as conn:
        rows = conn.execute(
            """
            SELECT t.id, t.author, t.screen_name, t.text,
                   t.likes, t.retweets, t.replies, t.views,
                   t.score, t.created_at, t.fetched_at, t.source
            FROM tweets t
            JOIN tweets_fts f ON f.rowid = t.rowid
            WHERE tweets_fts MATCH ?
            ORDER BY rank
            LIMIT ?
            """,
            (query, limit),
        ).fetchall()
    return [dict(r) for r in rows]


def list_sessions(limit: int = 20) -> List[Dict[str, Any]]:
    """Return the most recent fetch sessions with row counts."""
    with _connect() as conn:
        rows = conn.execute(
            """
            SELECT source,
                   MIN(fetched_at) AS first_fetch,
                   MAX(fetched_at) AS last_fetch,
                   COUNT(*)        AS tweet_count
            FROM tweets
            GROUP BY source, DATE(fetched_at)
            ORDER BY last_fetch DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()
    return [dict(r) for r in rows]


def archive_stats() -> Dict[str, Any]:
    """Return aggregate statistics about the archive."""
    with _connect() as conn:
        total = conn.execute("SELECT COUNT(*) FROM tweets").fetchone()[0]
        top_authors = conn.execute(
            """
            SELECT screen_name, COUNT(*) AS n
            FROM tweets GROUP BY screen_name
            ORDER BY n DESC LIMIT 5
            """
        ).fetchall()
        oldest = conn.execute("SELECT MIN(created_at) FROM tweets").fetchone()[0]
        newest = conn.execute("SELECT MAX(created_at) FROM tweets").fetchone()[0]
    return {
        "total_tweets": total,
        "oldest_tweet": oldest,
        "newest_tweet": newest,
        "top_authors": [dict(r) for r in top_authors],
        "db_path": str(_db_path()),
    }


def clear_archive() -> int:
    """Delete all rows. Returns number of deleted rows."""
    with _connect() as conn:
        n = conn.execute("SELECT COUNT(*) FROM tweets").fetchone()[0]
        conn.execute("DELETE FROM tweets")
        conn.execute("INSERT INTO tweets_fts(tweets_fts) VALUES('rebuild')")
        conn.commit()
    return n
