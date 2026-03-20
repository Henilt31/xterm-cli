"""AI-powered feed digest for twitter-cli.

Summarises a list of tweets into a concise daily briefing using
the Anthropic Claude API. No account needed for the AI part —
only the tweet data (fetched via cookie auth) is required.

Usage (via CLI):
    twitter digest              # digest today's For You feed
    twitter digest -t following # digest following feed
    twitter digest --max 50     # digest up to 50 tweets

Environment:
    ANTHROPIC_API_KEY   Required. Your Anthropic API key.
"""

from __future__ import annotations

import json
import os
import urllib.request
from typing import Any, Dict, List, Sequence

from .models import Tweet


_API_URL = "https://api.anthropic.com/v1/messages"
_MODEL = "claude-sonnet-4-20250514"
_MAX_TOKENS = 1024


def _build_prompt(tweets: Sequence[Tweet]) -> str:
    """Serialise tweets into a compact text block for the prompt."""
    lines: List[str] = []
    for i, t in enumerate(tweets, 1):
        score_part = f"  [score={t.score:.0f}]" if t.score is not None else ""
        lines.append(
            f"{i}. @{t.author.screen_name}: {t.text.strip()}"
            f"  (❤️{t.metrics.likes} 🔁{t.metrics.retweets} 💬{t.metrics.replies}){score_part}"
        )
    tweet_block = "\n".join(lines)
    return (
        "You are a concise tech-savvy analyst. Below is a list of tweets from a user's Twitter/X feed.\n\n"
        "Produce a **Daily Feed Digest** with these sections — keep it short and punchy:\n\n"
        "1. **Top Topics** (3-5 bullet points of the dominant themes/discussions)\n"
        "2. **Must-Read Tweets** (pick 3 standout tweets, quote the handle and a key phrase)\n"
        "3. **Sentiment Pulse** (one sentence: overall mood of the feed — positive/negative/mixed and why)\n"
        "4. **Worth Your Time** (one actionable takeaway or interesting thread to dig into)\n\n"
        "Be direct. No fluff. Use plain text, no markdown headers with ##.\n\n"
        f"TWEETS:\n{tweet_block}"
    )


def generate_digest(tweets: Sequence[Tweet], api_key: str | None = None) -> str:
    """Call Claude API and return the digest as a string.

    Args:
        tweets: List of Tweet objects to summarise.
        api_key: Anthropic API key. Falls back to ANTHROPIC_API_KEY env var.

    Returns:
        Digest text string.

    Raises:
        RuntimeError: If the API key is missing or the request fails.
    """
    key = api_key or os.environ.get("ANTHROPIC_API_KEY", "")
    if not key:
        raise RuntimeError(
            "ANTHROPIC_API_KEY is not set. "
            "Export it: export ANTHROPIC_API_KEY=sk-ant-..."
        )

    if not tweets:
        return "No tweets to digest."

    prompt = _build_prompt(tweets)
    payload: Dict[str, Any] = {
        "model": _MODEL,
        "max_tokens": _MAX_TOKENS,
        "messages": [{"role": "user", "content": prompt}],
    }
    data = json.dumps(payload).encode()
    headers = {
        "Content-Type": "application/json",
        "x-api-key": key,
        "anthropic-version": "2023-06-01",
    }

    req = urllib.request.Request(_API_URL, data=data, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            body = json.loads(resp.read())
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode(errors="replace")
        raise RuntimeError(f"Anthropic API error {exc.code}: {detail}") from exc
    except Exception as exc:
        raise RuntimeError(f"Request failed: {exc}") from exc

    # Extract text from response
    for block in body.get("content", []):
        if block.get("type") == "text":
            return block["text"].strip()

    raise RuntimeError(f"Unexpected response shape: {body}")
