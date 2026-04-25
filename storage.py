import sqlite3
from datetime import datetime
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
DB_DIR = BASE_DIR / "database"
DB_PATH = DB_DIR / "results.db"


def _get_connection() -> sqlite3.Connection:
    DB_DIR.mkdir(parents=True, exist_ok=True)
    return sqlite3.connect(DB_PATH)


def init_db() -> None:
    conn = _get_connection()
    cursor = conn.cursor()

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS records (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        record_name TEXT NOT NULL UNIQUE,
        record_content TEXT NOT NULL,
        created_at TEXT NOT NULL
    )
    """)

    conn.commit()
    conn.close()


def save_record(record_name: str, record_content: str) -> None:
    conn = _get_connection()
    cursor = conn.cursor()
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    cursor.execute("""
    INSERT INTO records (record_name, record_content, created_at)
    VALUES (?, ?, ?)
    ON CONFLICT(record_name) DO UPDATE SET
        record_content = excluded.record_content,
        created_at = excluded.created_at
    """, (record_name, record_content, now))

    conn.commit()
    conn.close()


def load_all_records() -> list[str]:
    conn = _get_connection()
    cursor = conn.cursor()

    cursor.execute("""
    SELECT record_name
    FROM records
    ORDER BY created_at DESC, id DESC
    """)
    rows = cursor.fetchall()

    conn.close()
    return [row[0] for row in rows]


def load_record_by_name(record_name: str) -> str:
    conn = _get_connection()
    cursor = conn.cursor()

    cursor.execute("""
    SELECT record_content
    FROM records
    WHERE record_name = ?
    """, (record_name,))
    row = cursor.fetchone()

    conn.close()
    return row[0] if row else ""


def delete_record_by_name(record_name: str) -> None:
    conn = _get_connection()
    cursor = conn.cursor()

    cursor.execute("""
    DELETE FROM records
    WHERE record_name = ?
    """, (record_name,))

    conn.commit()
    conn.close()