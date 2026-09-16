import json
import sqlite3
import ssl
import tomllib
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

import certifi

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATABASE_PATH = PROJECT_ROOT / "database" / "watchchord.db"
SECRETS_PATH = PROJECT_ROOT / ".streamlit" / "secrets.toml"


def main():
    if not DATABASE_PATH.exists():
        raise FileNotFoundError("The WatchChord database is missing.")

    with SECRETS_PATH.open("rb") as file:
        secrets = tomllib.load(file)

    token = secrets["TMDB_READ_ACCESS_TOKEN"].strip()

    request = Request(
        "https://api.themoviedb.org/3/genre/movie/list?language=en",
        headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/json",
        },
    )

    context = ssl.create_default_context(cafile=certifi.where())

    try:
        with urlopen(request, timeout=20, context=context) as response:
            data = json.load(response)
    except HTTPError as error:
        print(f"TMDB returned HTTP {error.code}.")
        return
    except URLError as error:
        print(f"Connection error: {error.reason}")
        return
    except TimeoutError:
        print("The request timed out. Try again.")
        return

    genres = data.get("genres", [])
    if not genres:
        print("No genres returned. Database unchanged.")
        return

    connection = sqlite3.connect(DATABASE_PATH)

    try:
        with connection:
            connection.execute("""
                CREATE TABLE IF NOT EXISTS tmdb_genres (
                    genre_id INTEGER PRIMARY KEY,
                    name TEXT NOT NULL
                );
            """)

            connection.executemany("""
                INSERT INTO tmdb_genres (genre_id, name)
                VALUES (?, ?)
                ON CONFLICT(genre_id) DO UPDATE SET
                    name = excluded.name;
            """, [
                (genre["id"], genre["name"])
                for genre in genres
            ])

        movielens_genres = connection.execute("""
            SELECT DISTINCT genre
            FROM movie_genres
            ORDER BY genre;
        """).fetchall()

        tmdb_names = {genre["name"] for genre in genres}
        aliases = {"Sci-Fi": "Science Fiction"}

        print(f"TMDB genre records saved: {len(genres)}")
        print("\nGenre compatibility:")

        for (name,) in movielens_genres:
            target = aliases.get(name, name)

            if target in tmdb_names:
                print(f"{name} -> {target}")
            else:
                print(f"{name} -> No direct match")

    finally:
        connection.close()


if __name__ == "__main__":
    main()