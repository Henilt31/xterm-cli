# xterm-cli

A terminal-first CLI for Twitter/X — read timelines, search tweets, schedule posts, and get AI-powered feed summaries, all from your terminal without API keys.

---

## Features

### Read
- **Feed** — fetch your For You and Following timelines
- **Bookmarks** — list your saved tweets
- **Search** — find tweets by keyword with Top / Latest / Photos / Videos tabs
- **Tweet detail** — view a tweet and its replies; use `show <N>` to open tweet #N from the last list
- **Article** — fetch a Twitter Article and export it as Markdown
- **List timeline** — fetch tweets from a Twitter List
- **User lookup** — view profile, tweets, likes, followers, and following
- **Full text** — use `--full-text` to disable tweet truncation in table output
- **Structured output** — export any data as JSON or YAML for scripting

### Write
- **Post** — create new tweets with optional image attachments (up to 4)
- **Reply** — reply to any tweet, with images
- **Quote** — quote-tweet with optional images
- **Delete** — remove your own tweets
- **Like / Unlike** — manage tweet likes
- **Retweet / Unretweet** — manage retweets
- **Bookmark / Unbookmark** — save and remove tweets

### Unique Features
- **AI Feed Digest** — summarise your entire feed into a daily briefing using Claude AI
- **Local Archive** — save tweets to a local SQLite database and search them offline
- **Tweet Scheduler** — schedule tweets to post at a future time with no third-party service

### Auth & Anti-Detection
- Cookie auth via browser cookies or environment variables
- Full cookie forwarding for richer browser context
- TLS fingerprint impersonation with dynamic Chrome version matching
- Request timing jitter to avoid pattern detection
- Write operation delays (1.5–4s random) to reduce rate limit risk
- Proxy support via `TWITTER_PROXY` environment variable

---

## Installation

**Recommended (uv):**
```bash
uv tool install xterm-cli
```

**Alternative (pipx):**
```bash
pipx install xterm-cli
```

**Install from source:**
```bash
git clone https://github.com/Henilt31/xterm-cli.git
cd xterm-cli
uv sync
```

---

## Authentication

xterm-cli uses this priority order:

1. **Environment variables** — `TWITTER_AUTH_TOKEN` + `TWITTER_CT0`
2. **Browser cookies** (recommended) — auto-extracted from Chrome / Edge / Firefox / Brave

**Setting cookies manually (Windows PowerShell):**
```powershell
$env:TWITTER_AUTH_TOKEN = "your_auth_token"
$env:TWITTER_CT0 = "your_ct0_value"
```

To get these values: open Chrome → go to x.com → press F12 → Application tab → Cookies → x.com → copy `auth_token` and `ct0` values.

**Check authentication:**
```bash
twitter status
```

---

## Usage

### Feed
```bash
twitter feed                        # For You timeline
twitter feed -t following           # Following timeline
twitter feed --max 50               # Fetch up to 50 tweets
twitter feed --full-text            # Show full tweet text
twitter feed --filter               # Apply engagement scoring
twitter feed --json                 # Structured JSON output
```

### Bookmarks
```bash
twitter bookmarks
twitter bookmarks --full-text
twitter bookmarks --max 30 --yaml
```

### Search
```bash
twitter search "AI agents"
twitter search "AI agents" -t Latest --max 50
twitter search "python" --from elonmusk --lang en --since 2026-01-01
twitter search "topic" -o results.json
```

### Tweet Detail
```bash
twitter tweet 1234567890
twitter tweet 1234567890 --full-text
twitter show 2                      # Open tweet #2 from last feed/search list
```

### User
```bash
twitter user elonmusk
twitter user-posts elonmusk --max 20
twitter followers elonmusk --max 50
twitter following elonmusk --max 50
twitter whoami
```

### Write Operations
```bash
twitter post "Hello from xterm-cli!"
twitter post "With image" --image photo.jpg
twitter post "Multi image" -i a.png -i b.jpg -i c.webp
twitter reply 1234567890 "Nice tweet!"
twitter quote 1234567890 "My thoughts"
twitter delete 1234567890
twitter like 1234567890
twitter unlike 1234567890
twitter retweet 1234567890
twitter unretweet 1234567890
twitter bookmark 1234567890
twitter unbookmark 1234567890
twitter follow elonmusk
twitter unfollow elonmusk
```

---

## Unique Features

### 1. AI Feed Digest
Summarises your Twitter feed into a concise daily briefing using the Claude AI API.

**Setup:**
```powershell
# Windows PowerShell
$env:ANTHROPIC_API_KEY = "sk-ant-..."

# Mac/Linux
export ANTHROPIC_API_KEY=sk-ant-...
```

**Usage:**
```bash
twitter digest                      # Digest your For You feed
twitter digest -t following         # Digest your Following feed
twitter digest --max 60             # Fetch more tweets before summarising
twitter digest --filter             # Score tweets first, then summarise top ones
```

**Output includes:**
- Top topics from your feed
- Must-read tweet highlights
- Overall sentiment pulse
- One actionable takeaway

---

### 2. Local Tweet Archive
Saves fetched tweets to a local SQLite database so you can search your history offline without hitting the Twitter API.

**Usage:**
```bash
twitter archive stats                        # Show total tweets, date range, top authors
twitter archive search "Tesla"               # Full-text search across saved tweets
twitter archive search "AI OR python" --max 20
twitter archive list                         # List all fetch sessions
twitter archive clear                        # Delete all archived data
```

**Database location:**
- Default: `~/.twitter_cli/archive.db`
- Override: `export TWITTER_ARCHIVE_PATH=/your/path/archive.db`

---

### 3. Tweet Scheduler
Schedule tweets to post at a future time. Jobs are stored locally in `~/.twitter_cli/schedule.json`. Run the daemon to send them automatically — no third-party service or paid tool needed.

**Usage:**
```bash
twitter schedule add "Good morning!" --at "2026-03-21 09:00"
twitter schedule add "Posting this later" --in 2h
twitter schedule add "Quick reminder" --in 30m
twitter schedule add "Part 2" --in 1h --reply-to 1234567890
twitter schedule list
twitter schedule list --all
twitter schedule cancel abc12345
twitter schedule run

# Run in background (Windows)
start /B twitter schedule run

# Run in background (Mac/Linux)
nohup twitter schedule run &
```

---

## Configuration

Create `config.yaml` in your working directory:

```yaml
fetch:
  count: 50

filter:
  mode: "topN"
  topN: 20
  minScore: 50
  lang: []
  excludeRetweets: false
  weights:
    likes: 1.0
    retweets: 3.0
    replies: 2.0
    bookmarks: 5.0
    views_log: 0.5

rateLimit:
  requestDelay: 2.5
  maxRetries: 3
  retryBaseDelay: 5.0
  maxCount: 200
```

---

## Proxy Support

```bash
export TWITTER_PROXY=http://127.0.0.1:7890
export TWITTER_PROXY=socks5://127.0.0.1:1080
```

---

## Output Modes

| Mode | When to use |
|---|---|
| Default rich table | Interactive reading in terminal |
| `--full-text` | Reading long tweets in table view |
| `--json` | Piping data to scripts |
| `--yaml` | AI agent integration |
| `-c` / `--compact` | Token-efficient output |

---

## Project Structure

```
xterm-cli/
├── twitter_cli/
│   ├── cli.py            # All CLI commands
│   ├── client.py         # HTTP + anti-detection layer
│   ├── auth.py           # Browser cookie extractor
│   ├── graphql.py        # Twitter internal API query IDs
│   ├── parser.py         # Tweet and user JSON parsing
│   ├── formatter.py      # Rich tables and Markdown output
│   ├── filter.py         # Engagement scoring
│   ├── models.py         # Tweet, Author, Metrics dataclasses
│   ├── serialization.py  # Tweet to JSON/YAML conversion
│   ├── digest.py         # AI feed digest (Claude API)
│   ├── archive.py        # Local SQLite archive
│   ├── scheduler.py      # Tweet scheduler and daemon
│   ├── cache.py          # Short-index tweet cache
│   ├── search.py         # Search query builder
│   ├── output.py         # Structured output helpers
│   ├── config.py         # Config loader
│   ├── constants.py      # API URLs and header constants
│   ├── exceptions.py     # Custom error types
│   └── timeutil.py       # Timestamp formatting
├── tests/
├── config.yaml
└── pyproject.toml
```

---

## Best Practices — Avoiding Bans

- Use a proxy — set `TWITTER_PROXY` to avoid direct IP exposure
- Keep request volumes low — use `--max 20` instead of `--max 500`
- Do not run too frequently — each startup fetches x.com to initialise anti-detection headers
- Use browser cookie extraction — provides full cookie fingerprint
- Avoid datacenter IPs — residential proxies are much safer

---

## Troubleshooting

**No Twitter cookies found**
- Make sure you are logged into x.com in Chrome, Edge, Firefox, or Brave
- Or set `TWITTER_AUTH_TOKEN` and `TWITTER_CT0` manually
- Run `twitter -v status` for debug diagnostics

**Cookie expired or invalid (401/403)**
- Re-login to x.com in your browser and retry

**Twitter API error 404**
- Twitter rotates internal GraphQL query IDs occasionally
- Retry the command — the client attempts a live fallback automatically

**Unicode error on Windows**
```powershell
$env:PYTHONIOENCODING = "utf-8"
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
```

---

## License

Apache-2.0
