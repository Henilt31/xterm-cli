"""Local tweet scheduler for twitter-cli.

Schedules tweets to be sent at a future time using a plain JSON
job file (~/.twitter_cli/schedule.json) and a lightweight daemon
loop. No third-party service or system cron required.

Usage (via CLI):
    twitter schedule "Hello world" --at "2026-03-21 09:00"
    twitter schedule "Hello world" --in 2h30m
    twitter schedule list          # view pending jobs
    twitter schedule cancel <id>   # remove a job
    twitter schedule run           # start the daemon (blocks; run in bg)

Job file schema (each entry):
    {
        "id":         "<uuid4>",
        "text":       "tweet text",
        "reply_to":   null | "tweet_id",
        "scheduled":  "2026-03-21T09:00:00+00:00",   # ISO-8601 UTC
        "status":     "pending" | "sent" | "failed",
        "sent_at":    null | "ISO-8601",
        "error":      null | "message"
    }
"""

from __future__ import annotations

import json
import os
import re
import time
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional


# ---------------------------------------------------------------------------
# Storage
# ---------------------------------------------------------------------------

def _schedule_path() -> Path:
    base = Path(os.environ.get("TWITTER_ARCHIVE_PATH", str(Path.home() / ".twitter_cli")))
    base = base.parent if base.suffix == ".db" else base
    base.mkdir(parents=True, exist_ok=True)
    return base / "schedule.json"


def _load() -> List[Dict[str, Any]]:
    p = _schedule_path()
    if not p.exists():
        return []
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return []


def _save(jobs: List[Dict[str, Any]]) -> None:
    _schedule_path().write_text(
        json.dumps(jobs, indent=2, ensure_ascii=False), encoding="utf-8"
    )


# ---------------------------------------------------------------------------
# Time parsing
# ---------------------------------------------------------------------------

def parse_schedule_time(value: str) -> datetime:
    """Parse a human-readable schedule string into a UTC datetime.

    Accepts:
        "2026-03-21 09:00"          absolute local time
        "2026-03-21T09:00:00Z"      ISO-8601
        "2h30m"  /  "90m"  / "1h"  relative offset from now
        "30s"                        (for testing)
    """
    value = value.strip()

    # Relative: e.g. "2h30m", "90m", "1h", "30s"
    rel = re.fullmatch(r"(?:(\d+)h)?(?:(\d+)m)?(?:(\d+)s)?", value)
    if rel and any(rel.groups()):
        hours = int(rel.group(1) or 0)
        minutes = int(rel.group(2) or 0)
        seconds = int(rel.group(3) or 0)
        delta = timedelta(hours=hours, minutes=minutes, seconds=seconds)
        if delta.total_seconds() <= 0:
            raise ValueError(f"Relative time '{value}' resolves to zero duration.")
        return datetime.now(timezone.utc) + delta

    # Absolute without timezone — treat as local
    for fmt in ("%Y-%m-%d %H:%M", "%Y-%m-%dT%H:%M", "%Y-%m-%dT%H:%M:%S"):
        try:
            naive = datetime.strptime(value, fmt)
            return naive.astimezone(timezone.utc)
        except ValueError:
            pass

    # ISO-8601 with Z or offset
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        pass

    raise ValueError(
        f"Cannot parse schedule time: '{value}'. "
        "Use 'YYYY-MM-DD HH:MM', '2h30m', '90m', etc."
    )


# ---------------------------------------------------------------------------
# Job management
# ---------------------------------------------------------------------------

def add_job(text: str, scheduled: datetime, reply_to: Optional[str] = None) -> Dict[str, Any]:
    """Create and persist a new scheduled tweet job.

    Args:
        text:      Tweet body.
        scheduled: UTC datetime to send at.
        reply_to:  Optional tweet ID to reply to.

    Returns:
        The created job dict.
    """
    job: Dict[str, Any] = {
        "id": str(uuid.uuid4())[:8],
        "text": text,
        "reply_to": reply_to,
        "scheduled": scheduled.isoformat(),
        "status": "pending",
        "sent_at": None,
        "error": None,
    }
    jobs = _load()
    jobs.append(job)
    _save(jobs)
    return job


def list_jobs(status: Optional[str] = None) -> List[Dict[str, Any]]:
    """Return jobs, optionally filtered by status."""
    jobs = _load()
    if status:
        jobs = [j for j in jobs if j.get("status") == status]
    return sorted(jobs, key=lambda j: j.get("scheduled", ""))


def cancel_job(job_id: str) -> bool:
    """Remove a pending job by ID. Returns True if found and removed."""
    jobs = _load()
    before = len(jobs)
    jobs = [j for j in jobs if j["id"] != job_id or j["status"] != "pending"]
    _save(jobs)
    return len(jobs) < before


def run_daemon(post_fn: Any, poll_interval: int = 30) -> None:
    """Block and periodically check for due jobs, then post them.

    Args:
        post_fn:       Callable(text, reply_to) → None. Wraps the twitter post command.
        poll_interval: Seconds between checks (default 30).
    """
    import logging
    log = logging.getLogger(__name__)
    log.info("Scheduler daemon started. Checking every %ds. Ctrl+C to stop.", poll_interval)

    while True:
        try:
            now = datetime.now(timezone.utc)
            jobs = _load()
            changed = False

            for job in jobs:
                if job["status"] != "pending":
                    continue
                try:
                    due = datetime.fromisoformat(job["scheduled"])
                except ValueError:
                    continue
                if due > now:
                    continue

                log.info("Firing job %s: %s", job["id"], job["text"][:60])
                try:
                    post_fn(job["text"], job.get("reply_to"))
                    job["status"] = "sent"
                    job["sent_at"] = now.isoformat()
                except Exception as exc:
                    job["status"] = "failed"
                    job["error"] = str(exc)
                    log.error("Job %s failed: %s", job["id"], exc)
                changed = True

            if changed:
                _save(jobs)

        except Exception as exc:  # noqa: BLE001
            log.error("Daemon loop error: %s", exc)

        time.sleep(poll_interval)
