import os
import sqlite3
import tempfile
from contextlib import closing
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
SOURCE = PROJECT_ROOT / "database" / "watchchord.db"
DESTINATION = PROJECT_ROOT / "demo" / "watchchord_demo.db"
TABLES = (
    "movies", "movie_genres", "tmdb_movies", "tmdb_genres",
    "tmdb_movie_genres", "movie_links",
)


def build_demo(source, destination):
    source = Path(source).resolve()
    destination = Path(destination).resolve()
    if source == destination:
        raise ValueError("The demo must be separate from the source database.")
    if not source.is_file():
        raise FileNotFoundError(f"Source database not found: {source}")
    destination.parent.mkdir(parents=True, exist_ok=True)
    handle, temporary_name = tempfile.mkstemp(
        prefix="watchchord_", suffix=".db", dir=destination.parent
    )
    os.close(handle)
    temporary = Path(temporary_name)
    counts = {}
    try:
        with closing(sqlite3.connect(source.as_uri() + "?mode=ro", uri=True)) as src:
            src.execute("BEGIN")  # Read every table from the same snapshot.
            with closing(sqlite3.connect(temporary)) as dst:
                with dst:
                    for table in TABLES:
                        definition = src.execute(
                            "SELECT sql FROM sqlite_master WHERE type='table' AND name=?",
                            (table,),
                        ).fetchone()
                        if not definition:
                            raise ValueError(f"Required table is missing: {table}")
                        dst.execute(definition[0])
                        cursor = src.execute(f'SELECT * FROM "{table}"')
                        placeholders = ",".join("?" for _ in cursor.description)
                        dst.executemany(
                            f'INSERT INTO "{table}" VALUES ({placeholders})', cursor
                        )
                        counts[table] = dst.execute(
                            f'SELECT COUNT(*) FROM "{table}"'
                        ).fetchone()[0]
                    dst.execute("""CREATE TABLE movie_rating_summary (
                        movie_id INTEGER PRIMARY KEY REFERENCES movies(movie_id),
                        rating_count INTEGER NOT NULL CHECK (rating_count > 0),
                        total_rating_points REAL NOT NULL
                    )""")
                    dst.executemany(
                        "INSERT INTO movie_rating_summary VALUES (?, ?, ?)",
                        src.execute("""SELECT movie_id, COUNT(*), SUM(rating)
                                       FROM ratings GROUP BY movie_id"""),
                    )
                    average, total = src.execute(
                        "SELECT AVG(rating), COUNT(*) FROM ratings"
                    ).fetchone()
                    if not total:
                        raise ValueError("The source ratings table is empty.")
                    dst.execute("""CREATE TABLE rating_baseline (
                        id INTEGER PRIMARY KEY CHECK (id = 1),
                        overall_average REAL NOT NULL,
                        total_ratings INTEGER NOT NULL
                    )""")
                    dst.execute(
                        "INSERT INTO rating_baseline VALUES (1, ?, ?)", (average, total)
                    )
                    represented = dst.execute(
                        "SELECT SUM(rating_count) FROM movie_rating_summary"
                    ).fetchone()[0]
                    if represented != total:
                        raise ValueError("Rating summary count does not match source.")
                    if dst.execute("PRAGMA foreign_key_check").fetchall():
                        raise ValueError("Demo database has broken movie links.")
                if dst.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
                    raise ValueError("Demo database integrity check failed.")
        os.replace(temporary, destination)
    finally:
        temporary.unlink(missing_ok=True)
    return counts, total


if __name__ == "__main__":
    counts, total = build_demo(SOURCE, DESTINATION)
    print("Saved: demo/watchchord_demo.db")
    print(f"MovieLens movies: {counts['movies']:,}")
    print(f"TMDB movies: {counts['tmdb_movies']:,}")
    print(f"Ratings represented in summaries: {total:,}")
    print(f"Demo database size: {DESTINATION.stat().st_size / 1024 / 1024:.2f} MB")
    print("Validation passed. Individual rating records are not included.")
    print("Original database unchanged. The app still uses the original database.")
