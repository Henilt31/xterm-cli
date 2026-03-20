# Unique Features Added (v0.9.0)

These three features were added on top of the original `twitter-cli` codebase.
They live in three new files and a block of new CLI commands appended to `cli.py`.

---

## 1. AI Feed Digest — `twitter digest`

**File:** `twitter_cli/digest.py`

Summarises your Twitter feed into a short daily briefing using the Claude API.
No changes to any existing code — purely additive.

### Setup

```bash
export ANTHROPIC_API_KEY=sk-ant-...
```

### Usage

```bash
# Digest your For You feed (default 40 tweets)
twitter digest

# Digest your Following feed, fetch more tweets
twitter digest -t following --max 60

# Score tweets by engagement first, then summarise the top ones
twitter digest --filter
```

### Output (example)

```
╭──────────────────── Daily Feed Digest ─────────────────────╮
│                                                              │
│ Top Topics                                                   │
│ • AI coding tools and Claude Code adoption                   │
│ • Rust vs Python performance debate                          │
│ • India startup funding news                                 │
│                                                              │
│ Must-Read Tweets                                             │
│ • @karpathy: "the attention pattern for this token is..."    │
│ • @sama: announced new model release                         │
│                                                              │
│ Sentiment Pulse                                              │
│ Mixed — excitement about AI tools offset by skepticism.      │
│                                                              │
│ Worth Your Time                                              │
│ Thread by @antirez on Redis internals — worth a full read.   │
╰──────────────────────────────────────────────────────────────╯
```

---

## 2. Local Tweet Archive — `twitter archive`

**File:** `twitter_cli/archive.py`

Saves fetched tweets to a local SQLite database (`~/.twitter_cli/archive.db`)
so you can search your history offline without hitting the Twitter API again.

### Usage

```bash
# View stats about your archive
twitter archive stats

# Full-text search (FTS5 — supports AND, OR, phrases)
twitter archive search "machine learning"
twitter archive search "python OR rust" --max 20
twitter archive search "AI agent" --json

# List recent fetch sessions
twitter archive list

# Delete everything (with confirmation prompt)
twitter archive clear
```

> **Saving tweets**: The archive commands read from the DB.
> To populate it, the `save_tweets()` function in `archive.py` can be called
> from any feed/search command. Wire it up by calling
> `_maybe_save_to_archive(tweets, source="feed", save=True)` after any fetch
> in `cli.py` (a helper is already defined at the bottom of the commands block).

### Database location

Default: `~/.twitter_cli/archive.db`
Override: `export TWITTER_ARCHIVE_PATH=/your/path/archive.db`

---

## 3. Tweet Scheduler — `twitter schedule`

**File:** `twitter_cli/scheduler.py`

Schedule tweets to post at a future time. Jobs are stored in
`~/.twitter_cli/schedule.json`. A lightweight daemon polls for due jobs
and posts them using your browser cookies — no cron, no third-party service.

### Usage

```bash
# Add a job with an absolute time
twitter schedule add "Good morning!" --at "2026-03-21 09:00"

# Add a job with a relative offset
twitter schedule add "Posting this in 2 hours" --in 2h
twitter schedule add "Quick reminder" --in 30m

# Reply to a tweet at a scheduled time
twitter schedule add "Part 2 of my thread" --in 1h --reply-to 1234567890

# View pending jobs
twitter schedule list

# View all jobs including sent/failed
twitter schedule list --all

# Cancel a pending job
twitter schedule cancel abc12345

# Start the daemon (blocks — run in background)
twitter schedule run
nohup twitter schedule run --interval 60 &
```

### How it works

1. `schedule add` writes a JSON entry to `~/.twitter_cli/schedule.json`.
2. `schedule run` loops every N seconds, checks for jobs whose `scheduled` time has passed, and calls the Twitter post API for each.
3. Jobs are marked `sent` or `failed` with a timestamp so you have a clear audit trail.

---

## File Summary

| File | Purpose |
|---|---|
| `twitter_cli/digest.py` | Claude API call + prompt logic for feed digest |
| `twitter_cli/archive.py` | SQLite helpers: save, search, stats, clear |
| `twitter_cli/scheduler.py` | JSON job store + daemon loop + time parser |
| `twitter_cli/cli.py` *(modified)* | Added `digest`, `archive`, `schedule` command groups |
| `pyproject.toml` *(modified)* | Version bumped to 0.9.0; added `[ai]` optional dep |
