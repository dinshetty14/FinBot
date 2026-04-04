"""
FinBot Database Module
SQLite-based user management with async support.
"""

import sqlite3
from pathlib import Path
from typing import Optional

from app.config import DATABASE_PATH


def _get_connection() -> sqlite3.Connection:
    """Get a SQLite connection with row factory."""
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    """Create the users table if it doesn't exist."""
    conn = _get_connection()
    try:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                role TEXT NOT NULL,
                department TEXT NOT NULL
            )
        """)
        conn.commit()
    finally:
        conn.close()


def get_user_by_username(username: str) -> Optional[dict]:
    """Fetch a user by username."""
    conn = _get_connection()
    try:
        cursor = conn.execute(
            "SELECT id, username, password_hash, role, department FROM users WHERE username = ?",
            (username,),
        )
        row = cursor.fetchone()
        if row:
            return dict(row)
        return None
    finally:
        conn.close()


def get_user_by_id(user_id: int) -> Optional[dict]:
    """Fetch a user by ID."""
    conn = _get_connection()
    try:
        cursor = conn.execute(
            "SELECT id, username, password_hash, role, department FROM users WHERE id = ?",
            (user_id,),
        )
        row = cursor.fetchone()
        if row:
            return dict(row)
        return None
    finally:
        conn.close()


def create_user(username: str, password_hash: str, role: str, department: str) -> int:
    """Create a new user and return the user ID."""
    conn = _get_connection()
    try:
        cursor = conn.execute(
            "INSERT INTO users (username, password_hash, role, department) VALUES (?, ?, ?, ?)",
            (username, password_hash, role, department),
        )
        conn.commit()
        return cursor.lastrowid
    finally:
        conn.close()


def update_user_role(user_id: int, role: str) -> bool:
    """Update a user's role."""
    conn = _get_connection()
    try:
        cursor = conn.execute(
            "UPDATE users SET role = ? WHERE id = ?",
            (role, user_id),
        )
        conn.commit()
        return cursor.rowcount > 0
    finally:
        conn.close()


def delete_user(user_id: int) -> bool:
    """Delete a user by ID."""
    conn = _get_connection()
    try:
        cursor = conn.execute("DELETE FROM users WHERE id = ?", (user_id,))
        conn.commit()
        return cursor.rowcount > 0
    finally:
        conn.close()


def list_users() -> list[dict]:
    """List all users (without password hashes)."""
    conn = _get_connection()
    try:
        cursor = conn.execute(
            "SELECT id, username, role, department FROM users"
        )
        return [dict(row) for row in cursor.fetchall()]
    finally:
        conn.close()
