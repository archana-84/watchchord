import sqlite3
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATABASE_PATH = PROJECT_ROOT / "database" / "watchchord.db"


def main():
    if not DATABASE_PATH.exists():
        raise FileNotFoundError("Create and import the database first.")

    connection = sqlite3.connect(DATABASE_PATH)

    try:
        connection.execute("PRAGMA foreign_keys = ON;")

        with connection:
            connection.execute("BEGIN IMMEDIATE;")

            connection.execute("""
                CREATE TABLE IF NOT EXISTS movie_genres (
                    movie_id INTEGER NOT NULL,
                    genre TEXT NOT NULL CHECK (
                        length(trim(genre)) > 0
                        AND genre <> '(no genres listed)'
                    ),
                    PRIMARY KEY (movie_id, genre),
                    FOREIGN KEY (movie_id)
                        REFERENCES movies(movie_id)
                );
            """)

            movies = connection.execute("""
                SELECT movie_id, genres
                FROM movies;
            """).fetchall()

            if not movies:
                raise ValueError("Import the movie data first.")

            genre_pairs = set()
            movies_without_genres = 0

            for movie_id, genre_text in movies:
                genres = {
                    genre.strip()
                    for genre in genre_text.split("|")
                    if genre.strip()
                    and genre.strip() != "(no genres listed)"
                }

                if not genres:
                    movies_without_genres += 1

                for genre in genres:
                    genre_pairs.add((movie_id, genre))

            # Rebuild this derived table so reruns stay consistent.
            connection.execute("DELETE FROM movie_genres;")

            connection.executemany("""
                INSERT INTO movie_genres (movie_id, genre)
                VALUES (?, ?);
            """, sorted(genre_pairs))

            genre_counts = connection.execute("""
                SELECT genre, COUNT(*) AS movie_count
                FROM movie_genres
                GROUP BY genre
                ORDER BY movie_count DESC, genre ASC;
            """).fetchall()

        print(f"Movie-genre pairs saved: {len(genre_pairs):,}")
        print(f"Movies without listed genres: {movies_without_genres}")

        print("\nMovies per genre:")
        for genre, movie_count in genre_counts:
            print(f"{genre}: {movie_count:,}")

    finally:
        connection.close()


if __name__ == "__main__":
    main()