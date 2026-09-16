import sqlite3
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATABASE_DIR = PROJECT_ROOT / "database"
DATABASE_DIR.mkdir(exist_ok=True)

DATABASE_PATH = DATABASE_DIR / "watchchord.db"

with sqlite3.connect(DATABASE_PATH) as connection:
    connection.execute("PRAGMA foreign_keys = ON;")

    connection.execute("""
        CREATE TABLE IF NOT EXISTS movies (
            movie_id INTEGER PRIMARY KEY CHECK (movie_id > 0),
            title TEXT NOT NULL CHECK (length(trim(title)) > 0),
            genres TEXT NOT NULL CHECK (length(trim(genres)) > 0)
        );
    """)

    connection.execute("""
        CREATE TABLE IF NOT EXISTS ratings (
            user_id INTEGER NOT NULL CHECK (user_id > 0),
            movie_id INTEGER NOT NULL,
            rating REAL NOT NULL CHECK (
                rating IN (
                    0.5, 1.0, 1.5, 2.0, 2.5,
                    3.0, 3.5, 4.0, 4.5, 5.0
                )
            ),
            rated_at INTEGER NOT NULL CHECK (rated_at >= 0),
            PRIMARY KEY (user_id, movie_id),
            FOREIGN KEY (movie_id) REFERENCES movies(movie_id)
        );
    """)

    tables = connection.execute("""
        SELECT name
        FROM sqlite_master
        WHERE type = 'table'
        ORDER BY name;
    """).fetchall()

    print(f"Database: {DATABASE_PATH}")
    for (table_name,) in tables:
        print(f"Table ready: {table_name}")
        