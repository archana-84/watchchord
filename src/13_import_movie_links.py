import csv
import sqlite3
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATABASE_PATH = PROJECT_ROOT / "database" / "watchchord.db"
LINKS_PATH = (
    PROJECT_ROOT / "data" / "raw" / "ml-latest-small" / "links.csv"
)


def main():
    if not DATABASE_PATH.exists():
        raise FileNotFoundError("The WatchChord database is missing.")

    rows = []

    with LINKS_PATH.open("r", encoding="utf-8", newline="") as file:
        for row in csv.DictReader(file):
            tmdb_id = row["tmdbId"].strip()

            rows.append((
                int(row["movieId"]),
                row["imdbId"].strip(),
                int(tmdb_id) if tmdb_id else None,
            ))

    connection = sqlite3.connect(DATABASE_PATH)

    try:
        connection.execute("PRAGMA foreign_keys = ON;")

        with connection:
            connection.execute("BEGIN IMMEDIATE;")

            connection.execute("""
                CREATE TABLE IF NOT EXISTS movie_links (
                    movie_id INTEGER PRIMARY KEY,
                    imdb_id TEXT NOT NULL,
                    tmdb_id INTEGER CHECK (tmdb_id > 0),
                    FOREIGN KEY (movie_id) REFERENCES movies(movie_id)
                );
            """)

            connection.executemany("""
                INSERT INTO movie_links (movie_id, imdb_id, tmdb_id)
                VALUES (?, ?, ?)
                ON CONFLICT(movie_id) DO UPDATE SET
                    imdb_id = excluded.imdb_id,
                    tmdb_id = excluded.tmdb_id;
            """, rows)

            total, linked = connection.execute("""
                SELECT
                    COUNT(*),
                    COUNT(tmdb_id)
                FROM movie_links;
            """).fetchone()

        print(f"Movie links stored: {total:,}")
        print(f"Movies with a TMDB ID: {linked:,}")
        print(f"Movies without a TMDB ID: {total - linked:,}")

        example = connection.execute("""
            SELECT m.title, l.movie_id, l.tmdb_id
            FROM movie_links AS l
            JOIN movies AS m ON m.movie_id = l.movie_id
            WHERE l.movie_id = 1;
        """).fetchone()

        if example:
            print(f"\nExample: {example[0]}")
            print(f"MovieLens ID: {example[1]}")
            print(f"TMDB ID: {example[2]}")

    finally:
        connection.close()


if __name__ == "__main__":
    main()