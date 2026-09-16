import json
import ssl
import tomllib
from datetime import datetime, timezone
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

import certifi

PROJECT_ROOT = Path(__file__).resolve().parent.parent
SECRETS_PATH = PROJECT_ROOT / ".streamlit" / "secrets.toml"
OUTPUT_PATH = PROJECT_ROOT / "data" / "raw" / "tmdb_recent_sample.json"


def main():
    with SECRETS_PATH.open("rb") as file:
        secrets = tomllib.load(file)

    token = secrets.get("TMDB_READ_ACCESS_TOKEN", "")
    if not isinstance(token, str) or not token.strip():
        print("TMDB_READ_ACCESS_TOKEN is missing or empty.")
        return

    fetched_at = datetime.now(timezone.utc)

    parameters = {
        "language": "en-US",
        "include_adult": "false",
        "include_video": "false",
        "primary_release_date.gte": "2024-01-01",
        "primary_release_date.lte": fetched_at.date().isoformat(),
        "sort_by": "popularity.desc",
        "page": 1,
    }

    request = Request(
        "https://api.themoviedb.org/3/discover/movie?"
        + urlencode(parameters),
        headers={
            "Authorization": f"Bearer {token.strip()}",
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
    except (json.JSONDecodeError, UnicodeDecodeError):
        print("TMDB returned an unreadable response.")
        return

    movies = data.get("results")
    if not isinstance(movies, list):
        print("The response did not contain a movie results list.")
        return

    snapshot = {
        "source": "TMDB",
        "fetched_at_utc": fetched_at.isoformat(),
        "query_parameters": parameters,
        "response": data,
    }

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(
        json.dumps(snapshot, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    print(f"Saved: {OUTPUT_PATH.name}")
    print(f"Movies on this page: {len(movies)}")
    print(f"Total matching pages reported: {data.get('total_pages')}")
    print("\nFirst five movies:")

    for movie in movies[:5]:
        print(
            f"- {movie['title']}"
            f" | Released: {movie.get('release_date') or 'Unknown'}"
            f" | TMDB ID: {movie['id']}"
        )


if __name__ == "__main__":
    main()