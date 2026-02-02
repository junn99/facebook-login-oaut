"""Database operations for Turso/libsql."""

import json
from datetime import datetime, timedelta
from typing import Optional
import libsql_experimental as libsql

from .config import config
from .models import User, Token, Insight, AudienceData, CollectionLog


_connection = None


def get_connection():
    """Get or create database connection."""
    global _connection
    if _connection is None:
        _connection = libsql.connect(
            database=config.DATABASE_URL,
            auth_token=config.DATABASE_AUTH_TOKEN
        )
    return _connection


def init_db():
    """Initialize database tables if they don't exist."""
    conn = get_connection()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            instagram_id TEXT UNIQUE NOT NULL,
            instagram_username TEXT NOT NULL,
            facebook_page_id TEXT NOT NULL,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS tokens (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            token_type TEXT NOT NULL,
            access_token TEXT NOT NULL,
            expires_at DATETIME,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS insights (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            metric_name TEXT NOT NULL,
            metric_value REAL NOT NULL,
            period TEXT NOT NULL,
            collected_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS audience_data (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            data_type TEXT NOT NULL,
            data_json TEXT NOT NULL,
            collected_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS collection_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            collection_type TEXT NOT NULL,
            status TEXT NOT NULL,
            error_message TEXT,
            collected_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        );

        CREATE INDEX IF NOT EXISTS idx_insights_user_collected ON insights(user_id, collected_at);
        CREATE INDEX IF NOT EXISTS idx_insights_metric ON insights(metric_name);
        CREATE INDEX IF NOT EXISTS idx_tokens_user ON tokens(user_id);
        CREATE INDEX IF NOT EXISTS idx_audience_user ON audience_data(user_id);
    """)
    conn.commit()


# User operations
def get_user_by_instagram_id(instagram_id: str) -> Optional[User]:
    """Get user by Instagram ID."""
    conn = get_connection()
    result = conn.execute(
        "SELECT id, instagram_id, instagram_username, facebook_page_id, created_at, updated_at FROM users WHERE instagram_id = ?",
        (instagram_id,)
    ).fetchone()
    if result:
        return User(
            id=result[0],
            instagram_id=result[1],
            instagram_username=result[2],
            facebook_page_id=result[3],
            created_at=result[4],
            updated_at=result[5]
        )
    return None


def get_all_users() -> list[User]:
    """Get all users."""
    conn = get_connection()
    results = conn.execute(
        "SELECT id, instagram_id, instagram_username, facebook_page_id, created_at, updated_at FROM users"
    ).fetchall()
    return [
        User(
            id=r[0], instagram_id=r[1], instagram_username=r[2],
            facebook_page_id=r[3], created_at=r[4], updated_at=r[5]
        )
        for r in results
    ]


def create_or_update_user(instagram_id: str, instagram_username: str, facebook_page_id: str) -> User:
    """Create or update a user."""
    conn = get_connection()
    existing = get_user_by_instagram_id(instagram_id)

    if existing:
        conn.execute(
            "UPDATE users SET instagram_username = ?, facebook_page_id = ?, updated_at = CURRENT_TIMESTAMP WHERE instagram_id = ?",
            (instagram_username, facebook_page_id, instagram_id)
        )
        conn.commit()
        return get_user_by_instagram_id(instagram_id)
    else:
        conn.execute(
            "INSERT INTO users (instagram_id, instagram_username, facebook_page_id) VALUES (?, ?, ?)",
            (instagram_id, instagram_username, facebook_page_id)
        )
        conn.commit()
        return get_user_by_instagram_id(instagram_id)


# Token operations
def save_token(user_id: int, token_type: str, access_token: str, expires_at: Optional[datetime] = None):
    """Save or update a token."""
    conn = get_connection()
    # Delete existing token of same type
    conn.execute("DELETE FROM tokens WHERE user_id = ? AND token_type = ?", (user_id, token_type))
    conn.execute(
        "INSERT INTO tokens (user_id, token_type, access_token, expires_at) VALUES (?, ?, ?, ?)",
        (user_id, token_type, access_token, expires_at)
    )
    conn.commit()


def get_user_token(user_id: int, token_type: str) -> Optional[Token]:
    """Get token for a user."""
    conn = get_connection()
    result = conn.execute(
        "SELECT id, user_id, token_type, access_token, expires_at, created_at FROM tokens WHERE user_id = ? AND token_type = ?",
        (user_id, token_type)
    ).fetchone()
    if result:
        return Token(
            id=result[0], user_id=result[1], token_type=result[2],
            access_token=result[3], expires_at=result[4], created_at=result[5]
        )
    return None


def get_expiring_tokens(days: int = 7) -> list[tuple[User, Token]]:
    """Get tokens expiring within specified days."""
    conn = get_connection()
    threshold = datetime.utcnow() + timedelta(days=days)
    results = conn.execute("""
        SELECT u.id, u.instagram_id, u.instagram_username, u.facebook_page_id,
               t.id, t.user_id, t.token_type, t.access_token, t.expires_at
        FROM users u
        JOIN tokens t ON u.id = t.user_id
        WHERE t.token_type = 'user' AND t.expires_at IS NOT NULL AND t.expires_at < ?
    """, (threshold,)).fetchall()

    return [
        (
            User(id=r[0], instagram_id=r[1], instagram_username=r[2], facebook_page_id=r[3]),
            Token(id=r[4], user_id=r[5], token_type=r[6], access_token=r[7], expires_at=r[8])
        )
        for r in results
    ]


# Insights operations
def save_insights(user_id: int, insights: list[dict]):
    """Save multiple insight records."""
    conn = get_connection()
    for insight in insights:
        conn.execute(
            "INSERT INTO insights (user_id, metric_name, metric_value, period) VALUES (?, ?, ?, ?)",
            (user_id, insight["metric_name"], insight["metric_value"], insight["period"])
        )
    conn.commit()


def get_insights(user_id: int, start_date: Optional[datetime] = None, end_date: Optional[datetime] = None, metric_name: Optional[str] = None) -> list[Insight]:
    """Get insights with optional filters."""
    conn = get_connection()
    query = "SELECT id, user_id, metric_name, metric_value, period, collected_at FROM insights WHERE user_id = ?"
    params = [user_id]

    if start_date:
        query += " AND collected_at >= ?"
        params.append(start_date)
    if end_date:
        query += " AND collected_at <= ?"
        params.append(end_date)
    if metric_name:
        query += " AND metric_name = ?"
        params.append(metric_name)

    query += " ORDER BY collected_at DESC"
    results = conn.execute(query, params).fetchall()

    return [
        Insight(id=r[0], user_id=r[1], metric_name=r[2], metric_value=r[3], period=r[4], collected_at=r[5])
        for r in results
    ]


def get_latest_insights(user_id: int) -> dict[str, Insight]:
    """Get the latest value for each metric."""
    conn = get_connection()
    results = conn.execute("""
        SELECT i.id, i.user_id, i.metric_name, i.metric_value, i.period, i.collected_at
        FROM insights i
        INNER JOIN (
            SELECT metric_name, MAX(collected_at) as max_collected
            FROM insights WHERE user_id = ?
            GROUP BY metric_name
        ) latest ON i.metric_name = latest.metric_name AND i.collected_at = latest.max_collected
        WHERE i.user_id = ?
    """, (user_id, user_id)).fetchall()

    return {
        r[2]: Insight(id=r[0], user_id=r[1], metric_name=r[2], metric_value=r[3], period=r[4], collected_at=r[5])
        for r in results
    }


# Audience data operations
def save_audience_data(user_id: int, data_type: str, data: dict):
    """Save audience data."""
    conn = get_connection()
    conn.execute(
        "INSERT INTO audience_data (user_id, data_type, data_json) VALUES (?, ?, ?)",
        (user_id, data_type, json.dumps(data))
    )
    conn.commit()


def get_latest_audience_data(user_id: int) -> dict[str, dict]:
    """Get latest audience data by type."""
    conn = get_connection()
    results = conn.execute("""
        SELECT a.data_type, a.data_json
        FROM audience_data a
        INNER JOIN (
            SELECT data_type, MAX(collected_at) as max_collected
            FROM audience_data WHERE user_id = ?
            GROUP BY data_type
        ) latest ON a.data_type = latest.data_type AND a.collected_at = latest.max_collected
        WHERE a.user_id = ?
    """, (user_id, user_id)).fetchall()

    return {r[0]: json.loads(r[1]) for r in results}


# Collection log operations
def log_collection(user_id: int, collection_type: str, status: str, error_message: Optional[str] = None):
    """Log a collection attempt."""
    conn = get_connection()
    conn.execute(
        "INSERT INTO collection_log (user_id, collection_type, status, error_message) VALUES (?, ?, ?, ?)",
        (user_id, collection_type, status, error_message)
    )
    conn.commit()
