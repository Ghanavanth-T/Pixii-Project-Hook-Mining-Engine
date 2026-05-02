# 🪝 Hook Mining Engine

**Crawls 1K+ viral posts weekly, surfaces emerging hook patterns into a library, and writes posts for Pixii.**

A fully automated pipeline that mines viral social media content, uses Claude AI to extract repeatable hook patterns, and generates brand-specific posts.

## Architecture

```
┌─────────────┐     ┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│   Crawler    │────▶│   Analyzer   │────▶│  Hook Library│────▶│  Generator   │
│ Reddit + X   │     │  Claude AI   │     │   SQLite DB  │     │  Claude AI   │
└─────────────┘     └──────────────┘     └──────────────┘     └──────────────┘
       │                                        │                      │
       ▼                                        ▼                      ▼
  1K+ viral posts              Hook patterns extracted        Pixii posts written
```

## APIs & Tools Used

| Tool | Purpose |
|------|---------|
| **Claude API** (Anthropic) | Hook pattern analysis + post generation |
| **Reddit API** (PRAW) | Crawl viral posts from marketing/copywriting subreddits |
| **Twitter/X via Apify** | Crawl viral tweets on marketing topics |
| **SQLite** | Persistent hook pattern library |
| **Streamlit** | Interactive dashboard |
| **APScheduler** | Automated weekly pipeline runs |

## Quick Start

### 1. Install dependencies

```bash
pip install -r requirements.txt
```

### 2. Set up environment variables

```bash
cp .env.example .env
# Edit .env with your API keys
```

### 3. Run the pipeline manually

```bash
python pipeline.py
```

### 4. Launch the dashboard

```bash
streamlit run dashboard.py
```

### 5. Start the automated scheduler

```bash
python scheduler.py
```

## Project Structure

```
├── pipeline.py      # Main orchestrator — runs crawl → analyze → generate
├── crawler.py       # Reddit + Twitter/X crawlers
├── analyzer.py      # Claude-powered hook pattern extraction
├── generator.py     # Claude-powered Pixii post generation
├── database.py      # SQLite schema + CRUD operations
├── dashboard.py     # Streamlit UI dashboard
├── scheduler.py     # APScheduler for automated runs
├── requirements.txt
├── .env.example
└── README.md
```

## How It Works

1. **Crawl** — Pulls hot/viral posts from 12 marketing subreddits and Twitter/X search results
2. **Analyze** — Claude reads the posts in batches, extracting repeatable hook patterns (curiosity gaps, bold claims, contrarian takes, etc.)
3. **Store** — Patterns are deduplicated and stored in SQLite with frequency tracking
4. **Generate** — Claude uses the top patterns from the library to write on-brand posts for Pixii
5. **Repeat** — The scheduler runs the full pipeline every Monday and generates extra posts on Thursdays

## Dashboard Features

- 📊 Real-time stats (posts crawled, patterns found, posts generated)
- 📚 Full hook pattern library with search and filter
- ✍️ Generated posts viewer with hook attribution
- 📈 Analytics: pattern frequency charts, category distribution
- 🚀 One-click pipeline trigger
- ⚡ Quick post generation controls
