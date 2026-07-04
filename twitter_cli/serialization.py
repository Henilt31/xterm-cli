"""Serialization helpers for Tweet and UserProfile models."""

from __future__ import annotations

import json
from typing import Any, Dict, Iterable, List, Optional

from .models import Author, Metrics, Tweet, TweetMedia, UserProfile
from .timeutil import format_local_time


def tweet_to_dict(tweet: Tweet) -> Dict[str, Any]:
    """Convert a Tweet dataclass into a JSON-safe dict."""
    data = {
        "id": tweet.id,
        "text": tweet.text,
        "author": {
            "id": tweet.author.id,
            "name": tweet.author.name,
            "screenName": tweet.author.screen_name,
            "profileImageUrl": tweet.author.profile_image_url,
            "verified": tweet.author.verified,
        },
        "metrics": {
            "likes": tweet.metrics.likes,
            "retweets": tweet.metrics.retweets,
            "replies": tweet.metrics.replies,
            "quotes": tweet.metrics.quotes,
            "views": tweet.metrics.views,
            "bookmarks": tweet.metrics.bookmarks,
        },
        "createdAt": tweet.created_at,
        "createdAtLocal": format_local_time(tweet.created_at),
        "media": [
            {
                "type": media.type,
                "url": media.url,
                "width": media.width,
                "height": media.height,
            }
            for media in tweet.media
        ],
        "urls": list(tweet.urls),
        "isRetweet": tweet.is_retweet,
        "retweetedBy": tweet.retweeted_by,
        "lang": tweet.lang,
        "score": tweet.score,
    }
    if tweet.article_title is not None:
        data["articleTitle"] = tweet.article_title
    if tweet.article_text is not None:
        data["articleText"] = tweet.article_text
    if tweet.quoted_tweet:
        data["quotedTweet"] = {
            "id": tweet.quoted_tweet.id,
            "text": tweet.quoted_tweet.text,
            "author": {
                "screenName": tweet.quoted_tweet.author.screen_name,
                "name": tweet.quoted_tweet.author.name,
            },
        }
    return data


def tweet_from_dict(data: Dict[str, Any]) -> Tweet:
    """Convert a dict into a Tweet dataclass."""
    data = _normalize_tweet_payload(data)
    author_data = data.get("author") or {}
    metrics_data = data.get("metrics") or {}
    media_data = data.get("media") or []
    quoted_data = data.get("quotedTweet")

    quoted_tweet = None  # type: Optional[Tweet]
    if isinstance(quoted_data, dict):
        quoted_author = quoted_data.get("author") or {}
        quoted_tweet = Tweet(
            id=str(quoted_data.get("id") or ""),
            text=str(quoted_data.get("text") or ""),
            author=Author(
                id="",
                name=str(quoted_author.get("name") or ""),
                screen_name=str(quoted_author.get("screenName") or ""),
            ),
            metrics=Metrics(),
            created_at="",
        )

    return Tweet(
        id=str(data.get("id") or ""),
        text=str(data.get("text") or ""),
        author=Author(
            id=str(author_data.get("id") or ""),
            name=str(author_data.get("name") or ""),
            screen_name=str(author_data.get("screenName") or ""),
            profile_image_url=str(author_data.get("profileImageUrl") or ""),
            verified=bool(author_data.get("verified", False)),
        ),
        metrics=Metrics(
            likes=int(metrics_data.get("likes") or 0),
            retweets=int(metrics_data.get("retweets") or 0),
            replies=int(metrics_data.get("replies") or 0),
            quotes=int(metrics_data.get("quotes") or 0),
            views=int(metrics_data.get("views") or 0),
            bookmarks=int(metrics_data.get("bookmarks") or 0),
        ),
        created_at=str(data.get("createdAt") or ""),
        media=[
            TweetMedia(
                type=str(item.get("type") or ""),
                url=str(item.get("url") or ""),
                width=_optional_int(item.get("width")),
                height=_optional_int(item.get("height")),
            )
            for item in media_data
            if isinstance(item, dict)
        ],
        urls=[str(url) for url in (data.get("urls") or [])],
        is_retweet=bool(data.get("isRetweet", False)),
        lang=str(data.get("lang") or ""),
        retweeted_by=_optional_str(data.get("retweetedBy")),
        quoted_tweet=quoted_tweet,
        score=float(data["score"]) if data.get("score") is not None else None,
        article_title=_optional_str(data.get("articleTitle")),
        article_text=_optional_str(data.get("articleText")),
    )


def tweets_from_json(raw: str) -> List[Tweet]:
    """Parse a JSON string into Tweet objects."""
    raw = raw.strip()
    if not raw:
        raise ValueError("Tweet JSON payload is empty")
    if _looks_like_jsonl(raw):
        return [tweet_from_dict(item) for item in _jsonl_records(raw)]
    payload = json.loads(raw)
    payload = _unwrap_tweet_collection(payload)
    if not isinstance(payload, list):
        raise ValueError("Tweet JSON payload must be a list")
    return [tweet_from_dict(item) for item in payload if isinstance(item, dict)]


def tweets_to_json(tweets: Iterable[Tweet]) -> str:
    """Serialize Tweet objects to pretty JSON."""
    return json.dumps([tweet_to_dict(tweet) for tweet in tweets], ensure_ascii=False, indent=2)


def tweets_to_data(tweets: Iterable[Tweet]) -> List[Dict[str, Any]]:
    """Serialize Tweet objects to Python dicts."""
    return [tweet_to_dict(tweet) for tweet in tweets]


def tweet_to_compact_dict(tweet: Tweet) -> Dict[str, Any]:
    """Convert a Tweet into a compact dict with minimal fields for LLM consumption."""
    text = tweet.text.replace("\n", " ").strip()
    if len(text) > 140:
        text = text[:137] + "..."
    # Short time: "Mar 07 05:51" from "Sat Mar 07 05:51:02 +0000 2026"
    parts = tweet.created_at.split()
    if len(parts) >= 4:
        time_str = "%s %s %s" % (parts[1], parts[2], parts[3][:5])
    else:
        time_str = tweet.created_at
    return {
        "id": tweet.id,
        "author": "@%s" % tweet.author.screen_name,
        "text": text,
        "likes": tweet.metrics.likes,
        "rts": tweet.metrics.retweets,
        "time": time_str,
    }


def tweets_to_compact_json(tweets: Iterable[Tweet]) -> str:
    """Serialize Tweet objects to compact JSON (minimal fields for LLM/pipe usage)."""
    return json.dumps(
        [tweet_to_compact_dict(tweet) for tweet in tweets],
        ensure_ascii=False,
        indent=2,
    )


def user_profile_to_dict(user: UserProfile) -> Dict[str, Any]:
    """Convert a UserProfile dataclass into a JSON-safe dict."""
    return {
        "id": user.id,
        "name": user.name,
        "screenName": user.screen_name,
        "bio": user.bio,
        "location": user.location,
        "url": user.url,
        "followers": user.followers_count,
        "following": user.following_count,
        "tweets": user.tweets_count,
        "likes": user.likes_count,
        "verified": user.verified,
        "profileImageUrl": user.profile_image_url,
        "createdAt": user.created_at,
    }


def users_to_json(users: Iterable[UserProfile]) -> str:
    """Serialize UserProfile objects to pretty JSON."""
    return json.dumps(
        [user_profile_to_dict(user) for user in users],
        ensure_ascii=False,
        indent=2,
    )


def users_to_data(users: Iterable[UserProfile]) -> List[Dict[str, Any]]:
    """Serialize UserProfile objects to Python dicts."""
    return [user_profile_to_dict(user) for user in users]


def _looks_like_jsonl(raw: str) -> bool:
    """Return True when input is newline-delimited JSON records."""
    lines = [line.strip() for line in raw.splitlines() if line.strip()]
    return len(lines) > 1 and all(line.startswith("{") for line in lines)


def _jsonl_records(raw: str) -> List[Dict[str, Any]]:
    """Parse JSONL records and keep dict-like tweet entries."""
    records = []
    for line_number, line in enumerate(raw.splitlines(), start=1):
        line = line.strip()
        if not line:
            continue
        try:
            payload = json.loads(line)
        except json.JSONDecodeError as exc:
            raise ValueError("Invalid JSONL tweet record on line %s: %s" % (line_number, exc))
        unwrapped = _unwrap_tweet_collection(payload)
        if isinstance(unwrapped, list):
            records.extend(item for item in unwrapped if isinstance(item, dict))
        elif isinstance(unwrapped, dict):
            records.append(unwrapped)
    return records


def _unwrap_tweet_collection(payload: Any) -> Any:
    """Unwrap common tweet export envelopes."""
    if not isinstance(payload, dict):
        return payload
    for key in ("data", "tweets", "items", "results"):
        value = payload.get(key)
        if isinstance(value, list):
            return value
    tweet = payload.get("tweet")
    if isinstance(tweet, dict):
        return tweet
    return payload


def _normalize_tweet_payload(data: Dict[str, Any]) -> Dict[str, Any]:
    """Normalize xterm-cli and Xquik tweet export fields to one shape."""
    if "author" in data and "metrics" in data and "createdAt" in data:
        return data

    author_data = data.get("author") if isinstance(data.get("author"), dict) else {}
    user_data = data.get("user") if isinstance(data.get("user"), dict) else {}
    author = author_data or user_data
    author_lookup = dict(data)
    author_lookup.update(author)
    metrics = data.get("metrics") if isinstance(data.get("metrics"), dict) else {}

    normalized = dict(data)
    normalized["id"] = _first_value(data, "id", "tweet_id", "tweetId", "tweetID")
    normalized["text"] = _first_value(data, "text", "full_text", "fullText", "content", "body")
    normalized["createdAt"] = _first_value(
        data,
        "createdAt",
        "created_at",
        "createdAtIso",
        "created_at_iso",
        "timestamp",
    )
    normalized["lang"] = _first_value(data, "lang", "language")
    normalized["author"] = {
        "id": _first_value(author_lookup, "author_id", "authorId", "user_id", "userId", "id"),
        "name": _first_value(author_lookup, "name", "display_name", "displayName", "username"),
        "screenName": _first_value(
            author_lookup,
            "screenName",
            "screen_name",
            "username",
            "handle",
            "userName",
        ),
        "profileImageUrl": _first_value(author_lookup, "profileImageUrl", "profile_image_url", "avatar_url"),
        "verified": bool(author_lookup.get("verified", False)),
    }
    normalized["metrics"] = {
        "likes": _metric_value(data, metrics, "likes", "like_count", "likeCount"),
        "retweets": _metric_value(data, metrics, "retweets", "retweet_count", "retweetCount"),
        "replies": _metric_value(data, metrics, "replies", "reply_count", "replyCount"),
        "quotes": _metric_value(data, metrics, "quotes", "quote_count", "quoteCount"),
        "views": _metric_value(data, metrics, "views", "view_count", "viewCount", "impression_count"),
        "bookmarks": _metric_value(data, metrics, "bookmarks", "bookmark_count", "bookmarkCount"),
    }
    return normalized


def _first_value(data: Dict[str, Any], *keys: str) -> Any:
    """Return the first present, non-empty value for a key list."""
    for key in keys:
        value = data.get(key)
        if value is not None and value != "":
            return value
    return ""


def _metric_value(data: Dict[str, Any], metrics: Dict[str, Any], *keys: str) -> int:
    """Read a metric from nested or flat tweet export fields."""
    for key in keys:
        value = metrics.get(key, data.get(key))
        if value is not None:
            return int(value or 0)
    return 0


def _optional_int(value: Any) -> Optional[int]:
    """Parse an optional integer value."""
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _optional_str(value: Any) -> Optional[str]:
    """Parse an optional string value."""
    if value is None:
        return None
    text = str(value)
    return text if text else None
