import sqlite3
from datetime import datetime, timezone


DB_NAME = "bot.db"


def get_connection():
    return sqlite3.connect(DB_NAME)


def initialize_database():
    conn = get_connection()
    cursor = conn.cursor()

    # Channels that count as update channels
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS update_channels (
            channel_id INTEGER PRIMARY KEY,
            channel_name TEXT NOT NULL
        )
    """)

    # Last update for each user
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            last_update TEXT NOT NULL,
            last_reminder TEXT
        )
    """)

    conn.commit()
    conn.close()


def add_update_channel(channel_id, channel_name):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        INSERT OR REPLACE INTO update_channels
        (channel_id, channel_name)
        VALUES (?, ?)
    """, (channel_id, channel_name))

    conn.commit()
    conn.close()


def remove_update_channel(channel_id):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        DELETE FROM update_channels
        WHERE channel_id = ?
    """, (channel_id,))

    conn.commit()
    conn.close()


def is_update_channel(channel_id):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT 1
        FROM update_channels
        WHERE channel_id = ?
    """, (channel_id,))

    result = cursor.fetchone()

    conn.close()

    return result is not None


def record_update(user_id):
    conn = get_connection()
    cursor = conn.cursor()

    now = datetime.now(timezone.utc).isoformat()

    cursor.execute("""
        INSERT INTO users
            (user_id, last_update, last_reminder)
        VALUES (?, ?, NULL)

        ON CONFLICT(user_id)
        DO UPDATE SET
            last_update = excluded.last_update,
            last_reminder = NULL
    """, (user_id, now))

    conn.commit()
    conn.close()


def get_users():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT user_id, last_update, last_reminder
        FROM users
    """)

    users = cursor.fetchall()

    conn.close()

    return users


def mark_reminded(user_id):
    conn = get_connection()
    cursor = conn.cursor()

    now = datetime.now(timezone.utc).isoformat()

    cursor.execute("""
        UPDATE users
        SET last_reminder = ?
        WHERE user_id = ?
    """, (now, user_id))

    conn.commit()
    conn.close()


def get_update_channels():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT channel_id, channel_name
        FROM update_channels
    """)

    channels = cursor.fetchall()

    conn.close()

    return channels