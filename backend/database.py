import os
import psycopg2
from psycopg2.extras import RealDictCursor

DATABASE_URL = os.getenv("DATABASE_URL",
    "postgresql://postgres:postgres@localhost:5432/manghe")


class QueryResult:
    def __init__(self, cursor):
        self._cursor = cursor

    def fetchone(self):
        row = self._cursor.fetchone()
        return dict(row) if row else None

    def fetchall(self):
        return [dict(row) for row in self._cursor.fetchall()]

    @property
    def lastrowid(self):
        row = self._cursor.fetchone()
        return row[0] if row else None


class DbConnection:
    def __init__(self, conn):
        self.conn = conn

    def execute(self, sql, params=None):
        cur = self.conn.cursor(cursor_factory=RealDictCursor)
        cur.execute(sql, params or ())
        return QueryResult(cur)

    def executescript(self, sql):
        cur = self.conn.cursor()
        for stmt in sql.split(";"):
            stmt = stmt.strip()
            if stmt:
                cur.execute(stmt + ";")

    def commit(self):
        self.conn.commit()

    def close(self):
        self.conn.close()


def get_db():
    conn = psycopg2.connect(DATABASE_URL)
    return DbConnection(conn)


def init_db():
    db = get_db()
    db.executescript("""
        CREATE TABLE IF NOT EXISTS users (
            id SERIAL PRIMARY KEY,
            username VARCHAR(20) UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS collection (
            id SERIAL PRIMARY KEY,
            user_id INTEGER NOT NULL REFERENCES users(id),
            pet_id INTEGER NOT NULL,
            count INTEGER DEFAULT 1,
            first_obtained_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(user_id, pet_id)
        );

        CREATE TABLE IF NOT EXISTS daily_pulls (
            id SERIAL PRIMARY KEY,
            user_id INTEGER NOT NULL REFERENCES users(id),
            pull_date DATE NOT NULL,
            pull_count INTEGER DEFAULT 0,
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
    db.commit()

    # Seed pets from SEED_PETS if the table is empty
    row = db.execute("SELECT COUNT(*) as cnt FROM pets").fetchone()
    if row and row["cnt"] == 0:
        from pet_data import SEED_PETS
        for p in SEED_PETS:
            db.execute(
                "INSERT INTO pets (id, name, emoji, rarity, description) VALUES (%s, %s, %s, %s, %s)",
                (p["id"], p["name"], p["emoji"], p["rarity"], p["description"]),
            )
        db.commit()

    db.close()
