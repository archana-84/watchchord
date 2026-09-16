import argparse
import sqlite3
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATABASE_PATH = PROJECT_ROOT / "database" / "watchchord.db"


def main():
    parser = argparse.ArgumentParser(
        description="Find movies matching two viewers' genre preferences."
    )
    parser.add_argument("--viewer-a", required=True)
    parser.add_argument("--viewer-b", required=True)
    parser.add_argument("--exclude", default=None)
    parser.add_argument(
        "--watched",
        nargs="+",
        type=int,
        default=[],
        help="Movie IDs already watched by either viewer.",
    )
    args = parser.parse_args()

    if not DATABASE_PATH.exists():
        raise FileNotFoundError("Create and import the database first.")

    connection = sqlite3.connect(DATABASE_PATH)
    connection.row_factory = sqlite3.Row

    try:
        available_genres = {
            row["genre"]
            for row in connection.execute(
                "SELECT DISTINCT genre FROM movie_genres;"
            )
        }

        for genre in [args.viewer_a, args.viewer_b, args.exclude]:
            if genre is not None and genre not in available_genres:
                parser.error(
                    f"Unknown genre: {genre}. Choose from: "
                    + ", ".join(sorted(available_genres))
                )

        connection.execute("""
            CREATE TEMP TABLE watched_movies (
                movie_id INTEGER PRIMARY KEY
            );
        """)

        connection.executemany(
            "INSERT INTO watched_movies (movie_id) VALUES (?);",
            [(movie_id,) for movie_id in sorted(set(args.watched))],
        )

        query = """
            WITH overall AS (
                SELECT AVG(rating) AS overall_average
                FROM ratings
            ),
            movie_stats AS (
                SELECT
                    movie_id,
                    COUNT(*) AS rating_count,
                    SUM(rating) AS total_rating_points
                FROM ratings
                GROUP BY movie_id
            )
            SELECT
                m.movie_id,
                m.title,
                m.genres,
                s.rating_count,
                (
                    s.total_rating_points
                    + 20.0 * o.overall_average
                ) / (s.rating_count + 20.0) AS weighted_score
            FROM movies AS m
            JOIN movie_stats AS s
                ON s.movie_id = m.movie_id
            CROSS JOIN overall AS o
            WHERE EXISTS (
                SELECT 1 FROM movie_genres AS g
                WHERE g.movie_id = m.movie_id AND g.genre = ?
            )
            AND EXISTS (
                SELECT 1 FROM movie_genres AS g
                WHERE g.movie_id = m.movie_id AND g.genre = ?
            )
            AND NOT EXISTS (
                SELECT 1 FROM movie_genres AS g
                WHERE g.movie_id = m.movie_id AND g.genre = ?
            )
            AND NOT EXISTS (
                SELECT 1
                FROM watched_movies AS w
                WHERE w.movie_id = m.movie_id
            )
            ORDER BY
                weighted_score DESC,
                s.rating_count DESC,
                m.movie_id ASC
            LIMIT 10;
        """

        results = connection.execute(
            query,
            (args.viewer_a, args.viewer_b, args.exclude),
        ).fetchall()

        print(f"\nViewer A: {args.viewer_a}")
        print(f"Viewer B: {args.viewer_b}")
        print(f"Excluded genre: {args.exclude or 'None'}")

        if not results:
            print("\nNo rated movies match these preferences.")
            print("Try different preferences or review the exclusion.")
            return

        for position, row in enumerate(results, start=1):
            print(f"\n{position}. {row['title']}")
            print(f"   Genres: {row['genres']}")
            print(
                f"   Score: {row['weighted_score']:.3f}"
                f" | Ratings: {row['rating_count']}"
            )

    finally:
        connection.close()


if __name__ == "__main__":
    main()