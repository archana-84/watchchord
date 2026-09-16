import json
import sqlite3
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATABASE_PATH = PROJECT_ROOT / "database" / "watchchord.db"
SAMPLE_PATH = PROJECT_ROOT / "data" / "raw" / "tmdb_recent_sample.json"


def main():
    if not DATABASE_PATH.exists():
        raise FileNotFoundError("The WatchChord database is missing.")

    with SAMPLE_PATH.open("r", encoding="utf-8") as file:
        snapshot = json.load(file)

    movies = snapshot["response"]["results"]
    fetched_at = snapshot["fetched_at_utc"]

    connection = sqlite3.connect(DATABASE_PATH)

    try:
        connection.execute("PRAGMA foreign_keys = ON;")

        with connection:
            connection.execute("BEGIN IMMEDIATE;")

            connection.execute("""
                CREATE TABLE IF NOT EXISTS tmdb_movies (
                    tmdb_id INTEGER PRIMARY KEY CHECK (tmdb_id > 0),
                    title TEXT NOT NULL,
                    release_date TEXT NOT NULL,
                    overview TEXT,
                    poster_path TEXT,
                    vote_average REAL NOT NULL
                        CHECK (vote_average BETWEEN 0 AND 10),
                    vote_count INTEGER NOT NULL CHECK (vote_count >= 0),
                    fetched_at_utc TEXT NOT NULL
                );
            """)

            connection.execute("""
                CREATE TABLE IF NOT EXISTS tmdb_movie_genres (
                    tmdb_id INTEGER NOT NULL,
                    genre_id INTEGER NOT NULL,
                    PRIMARY KEY (tmdb_id, genre_id),
                    FOREIGN KEY (tmdb_id) REFERENCES tmdb_movies(tmdb_id)
                );
            """)

            for movie in movies:
                connection.execute("""
                    INSERT INTO tmdb_movies (
                        tmdb_id, title, release_date, overview,
                        poster_path, vote_average, vote_count,
                        fetched_at_utc
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(tmdb_id) DO UPDATE SET
                        title = excluded.title,
                        release_date = excluded.release_date,
                        overview = excluded.overview,
                        poster_path = excluded.poster_path,
                        vote_average = excluded.vote_average,
                        vote_count = excluded.vote_count,
                        fetched_at_utc = excluded.fetched_at_utc;
                """, (
                    movie["id"],
                    movie["title"],
                    movie["release_date"],
                    movie.get("overview"),
                    movie.get("poster_path"),
                    movie["vote_average"],
                    movie["vote_count"],
                    fetched_at,
                ))

                # Refresh genres for this movie only.
                connection.execute(
                    "DELETE FROM tmdb_movie_genres WHERE tmdb_id = ?;",
                    (movie["id"],),
                )

                connection.executemany("""
                    INSERT INTO tmdb_movie_genres (tmdb_id, genre_id)
                    VALUES (?, ?);
                """, [
                    (movie["id"], genre_id)
                    for genre_id in sorted(set(movie["genre_ids"]))
                ])

            total = connection.execute(
                "SELECT COUNT(*) FROM tmdb_movies;"
            ).fetchone()[0]

        print(f"Sample records processed: {len(movies)}")
        print(f"Total TMDB movies stored: {total}")
        print("MovieLens tables unchanged.")

    finally:
        connection.close()


if __name__ == "__main__":
    main()