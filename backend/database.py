import sqlite3
import os

DB_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(DB_DIR, "manghe.db")


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def init_db():
    conn = get_db()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS collection (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            pet_id INTEGER NOT NULL,
            count INTEGER DEFAULT 1,
            first_obtained_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id),
            UNIQUE(user_id, pet_id)
        );

        CREATE TABLE IF NOT EXISTS daily_pulls (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            pull_date TEXT NOT NULL,
            pull_count INTEGER DEFAULT 0,
            FOREIGN KEY (user_id) REFERENCES users(id),
            UNIQUE(user_id, pull_date)
        );
        CREATE TABLE IF NOT EXISTS pets (
            id INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            emoji TEXT NOT NULL,
            rarity TEXT NOT NULL,
            description TEXT NOT NULL DEFAULT '',
            image_path TEXT DEFAULT NULL,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)
    conn.commit()

    # Seed pets from SEED_PETS if the table is empty (first run)
    count = conn.execute("SELECT COUNT(*) FROM pets").fetchone()[0]
    if count == 0:
        from pet_data import SEED_PETS
        for p in SEED_PETS:
            conn.execute(
                "INSERT INTO pets (id, name, emoji, rarity, description) VALUES (?, ?, ?, ?, ?)",
                (p["id"], p["name"], p["emoji"], p["rarity"], p["description"]),
            )
        conn.commit()

    conn.close()
