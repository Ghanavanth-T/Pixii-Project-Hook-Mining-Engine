import sqlite3
import json
from datetime import datetime
from pathlib import Path

DB_PATH = Path(__file__).parent / "hook_library.db"


def get_connection():
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_connection()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS viral_posts (
            id TEXT PRIMARY KEY,
            source TEXT NOT NULL,
            subreddit_or_topic TEXT,
            title TEXT,
            body TEXT,
            score INTEGER,
            url TEXT,
            crawled_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS hook_patterns (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            pattern_name TEXT NOT NULL,
            category TEXT NOT NULL,
            description TEXT,
            example TEXT,
            frequency INTEGER DEFAULT 1,
            first_seen TEXT NOT NULL,
            last_seen TEXT NOT NULL,
            source_post_ids TEXT
        );

        CREATE TABLE IF NOT EXISTS generated_posts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            hook_pattern_id INTEGER,
            content TEXT NOT NULL,
            platform TEXT,
            created_at TEXT NOT NULL,
            status TEXT DEFAULT 'draft',
            FOREIGN KEY (hook_pattern_id) REFERENCES hook_patterns(id)
        );

        CREATE TABLE IF NOT EXISTS pipeline_runs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            started_at TEXT NOT NULL,
            finished_at TEXT,
            posts_crawled INTEGER DEFAULT 0,
            patterns_found INTEGER DEFAULT 0,
            posts_generated INTEGER DEFAULT 0,
            status TEXT DEFAULT 'running'
        );
    """)
    conn.commit()
    conn.close()


def save_viral_posts(posts: list[dict]):
    conn = get_connection()
    saved = 0
    for p in posts:
        try:
            conn.execute(
                "INSERT OR IGNORE INTO viral_posts (id, source, subreddit_or_topic, title, body, score, url, crawled_at) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (p["id"], p["source"], p.get("subreddit_or_topic", ""),
                 p.get("title", ""), p.get("body", "")[:5000],
                 p.get("score", 0), p.get("url", ""), datetime.utcnow().isoformat())
            )
            saved += 1
        except sqlite3.IntegrityError:
            pass
    conn.commit()
    conn.close()
    return saved


def save_hook_patterns(patterns: list[dict], source_post_ids: list[str]):
    conn = get_connection()
    now = datetime.utcnow().isoformat()
    ids_json = json.dumps(source_post_ids[:20])
    new_count = 0

    for pat in patterns:
        # Ensure all fields are strings — AI sometimes returns dicts/lists
        def to_str(val):
            if isinstance(val, (dict, list)):
                return json.dumps(val)
            return str(val) if val is not None else ""

        name = to_str(pat.get("pattern_name", ""))
        category = to_str(pat.get("category", "other"))
        description = to_str(pat.get("description", ""))
        example = to_str(pat.get("example", ""))

        if not name:
            continue

        existing = conn.execute(
            "SELECT id, frequency, source_post_ids FROM hook_patterns WHERE pattern_name = ?",
            (name,)
        ).fetchone()

        if existing:
            old_ids = json.loads(existing["source_post_ids"] or "[]")
            merged = list(set(old_ids + source_post_ids[:10]))[:30]
            conn.execute(
                "UPDATE hook_patterns SET frequency = ?, last_seen = ?, source_post_ids = ?, description = ? WHERE id = ?",
                (existing["frequency"] + 1, now, json.dumps(merged), description, existing["id"])
            )
        else:
            conn.execute(
                "INSERT INTO hook_patterns (pattern_name, category, description, example, frequency, first_seen, last_seen, source_post_ids) "
                "VALUES (?, ?, ?, ?, 1, ?, ?, ?)",
                (name, category, description, example, now, now, ids_json)
            )
            new_count += 1

    conn.commit()
    conn.close()
    return new_count


def save_generated_post(content: str, hook_pattern_id: int, platform: str = "twitter"):
    conn = get_connection()
    conn.execute(
        "INSERT INTO generated_posts (hook_pattern_id, content, platform, created_at) VALUES (?, ?, ?, ?)",
        (hook_pattern_id, content, platform, datetime.utcnow().isoformat())
    )
    conn.commit()
    conn.close()


def start_pipeline_run():
    conn = get_connection()
    cur = conn.execute(
        "INSERT INTO pipeline_runs (started_at) VALUES (?)",
        (datetime.utcnow().isoformat(),)
    )
    run_id = cur.lastrowid
    conn.commit()
    conn.close()
    return run_id


def finish_pipeline_run(run_id: int, posts_crawled: int, patterns_found: int, posts_generated: int, status="completed"):
    conn = get_connection()
    conn.execute(
        "UPDATE pipeline_runs SET finished_at = ?, posts_crawled = ?, patterns_found = ?, posts_generated = ?, status = ? WHERE id = ?",
        (datetime.utcnow().isoformat(), posts_crawled, patterns_found, posts_generated, status, run_id)
    )
    conn.commit()
    conn.close()


def get_all_patterns():
    conn = get_connection()
    rows = conn.execute("SELECT * FROM hook_patterns ORDER BY frequency DESC").fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_all_generated_posts():
    conn = get_connection()
    rows = conn.execute(
        "SELECT g.*, h.pattern_name, h.category FROM generated_posts g "
        "LEFT JOIN hook_patterns h ON g.hook_pattern_id = h.id "
        "ORDER BY g.created_at DESC"
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_pipeline_runs():
    conn = get_connection()
    rows = conn.execute("SELECT * FROM pipeline_runs ORDER BY started_at DESC LIMIT 20").fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_top_patterns(limit=10):
    conn = get_connection()
    rows = conn.execute("SELECT * FROM hook_patterns ORDER BY frequency DESC LIMIT ?", (limit,)).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_stats():
    conn = get_connection()
    stats = {
        "total_posts_crawled": conn.execute("SELECT COUNT(*) FROM viral_posts").fetchone()[0],
        "total_patterns": conn.execute("SELECT COUNT(*) FROM hook_patterns").fetchone()[0],
        "total_generated": conn.execute("SELECT COUNT(*) FROM generated_posts").fetchone()[0],
        "total_runs": conn.execute("SELECT COUNT(*) FROM pipeline_runs").fetchone()[0],
    }
    conn.close()
    return stats


init_db()
