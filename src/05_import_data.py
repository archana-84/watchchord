import csv
import sqlite3
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data" / "raw" / "ml-latest-small"
DATABASE_PATH = PROJECT_ROOT / "database" / "watchchord.db"


def movie_rows():
    with (DATA_DIR / "movies.csv").open(
        "r", encoding="utf-8", newline=""
    ) as file:
        for row in csv.DictReader(file):
            yield (
                int(row["movieId"]),
                row["title"],
                row["genres"],
            )


def rating_rows():
    with (DATA_DIR / "ratings.csv").open(
        "r", encoding="utf-8", newline=""
    ) as file:
        for row in csv.DictReader(file):
            yield (
                int(row["userId"]),
                int(row["movieId"]),
                float(row["rating"]),
                int(row["timestamp"]),
            )


def main():
    if not DATABASE_PATH.exists():
        raise FileNotFoundError("Run 04_create_database.py first.")

    connection = sqlite3.connect(DATABASE_PATH)

    try:
        connection.execute("PRAGMA foreign_keys = ON;")

        with connection:
            connection.execute("BEGIN IMMEDIATE;")

            existing_movies = connection.execute(
                "SELECT COUNT(*) FROM movies;"
            ).fetchone()[0]

            existing_ratings = connection.execute(
                "SELECT COUNT(*) FROM ratings;"
            ).fetchone()[0]

            if existing_movies or existing_ratings:
                print("Import skipped: tables already contain data.")
                print(f"Movies: {existing_movies:,}")
                print(f"Ratings: {existing_ratings:,}")
                return

            connection.executemany("""
                INSERT INTO movies (movie_id, title, genres)
                VALUES (?, ?, ?);
            """, movie_rows())

            connection.executemany("""
                INSERT INTO ratings (
                    user_id, movie_id, rating, rated_at
                )
                VALUES (?, ?, ?, ?);
            """, rating_rows())

            movie_count = connection.execute(
                "SELECT COUNT(*) FROM movies;"
            ).fetchone()[0]

            rating_count = connection.execute(
                "SELECT COUNT(*) FROM ratings;"
            ).fetchone()[0]

        print("Import completed and saved.")
        print(f"Movies imported: {movie_count:,}")
        print(f"Ratings imported: {rating_count:,}")

    finally:
        connection.close()


if __name__ == "__main__":
    main()