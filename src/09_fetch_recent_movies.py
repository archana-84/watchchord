import json
import ssl
import tomllib
from datetime import date, datetime, timezone
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

import certifi

PROJECT_ROOT = Path(__file__).resolve().parent.parent
SECRETS_PATH = PROJECT_ROOT / ".streamlit" / "secrets.toml"
OUTPUT_PATH = PROJECT_ROOT / "data" / "raw" / "tmdb_recent_sample.json"
START_YEAR = 2024
PAGES_PER_YEAR = 5


def fetch_sample(token, today, fetch_json):
    """Return deduplicated records and request metadata; no files are changed."""
    movies_by_id = {}
    requests = []
    for year in range(START_YEAR, today.year + 1):
        start = date(year, 1, 1)
        end = min(date(year, 12, 31), today)
        for page in range(1, PAGES_PER_YEAR + 1):
            parameters = {
                "language": "en-US",
                "include_adult": "false",
                "include_video": "false",
                "primary_release_date.gte": start.isoformat(),
                "primary_release_date.lte": end.isoformat(),
                "sort_by": "popularity.desc",
                "page": page,
            }
            request = Request(
                "https://api.themoviedb.org/3/discover/movie?"
                + urlencode(parameters),
                headers={
                    "Authorization": f"Bearer {token}",
                    "Accept": "application/json",
                },
            )
            data = fetch_json(request)
            if not isinstance(data, dict) or not isinstance(data.get("results"), list):
                raise ValueError("TMDB returned an unexpected response structure.")
            results = data["results"]
            total_pages = data.get("total_pages")
            if type(total_pages) is not int or total_pages < 0:
                raise ValueError("TMDB returned an invalid page count.")
            for movie in results:
                if not isinstance(movie, dict):
                    raise ValueError("TMDB returned an invalid movie record.")
                movie_id = movie.get("id")
                if type(movie_id) is not int or movie_id <= 0:
                    raise ValueError("TMDB returned an invalid movie ID.")
                movies_by_id[movie_id] = movie
            requests.append({
                "parameters": parameters,
                "records_returned": len(results),
                "total_pages_reported": total_pages,
            })
            print(f"{year} | page {page}: {len(results)} records")
            if not results or page >= total_pages:
                break
    return list(movies_by_id.values()), requests


def main():
    try:
        with SECRETS_PATH.open("rb") as file:
            secrets = tomllib.load(file)
    except FileNotFoundError:
        print("Could not find .streamlit/secrets.toml.")
        return
    except tomllib.TOMLDecodeError:
        print("Check the formatting of secrets.toml.")
        return
    token = secrets.get("TMDB_READ_ACCESS_TOKEN", "")
    if not isinstance(token, str) or not token.strip():
        print("TMDB_READ_ACCESS_TOKEN is missing or empty.")
        return

    started = datetime.now(timezone.utc)
    today = started.date()
    context = ssl.create_default_context(cafile=certifi.where())

    def fetch_json(request):
        with urlopen(request, timeout=20, context=context) as response:
            return json.load(response)

    try:
        movies, requests = fetch_sample(token.strip(), today, fetch_json)
    except HTTPError as error:
        print(f"TMDB returned HTTP {error.code}. Previous sample unchanged.")
        if error.code == 429:
            print("TMDB asked us to slow down. Wait before trying again.")
        return
    except URLError as error:
        print(f"Connection error: {error.reason}. Previous sample unchanged.")
        return
    except TimeoutError:
        print("Request timed out. Previous sample unchanged; try again later.")
        return
    except (ValueError, UnicodeDecodeError):
        print("TMDB returned invalid data. Previous sample unchanged.")
        return

    if not movies:
        print("No movies returned. Previous sample unchanged.")
        return

    snapshot = {
        "source": "TMDB",
        "fetched_at_utc": datetime.now(timezone.utc).isoformat(),
        "fetch_started_at_utc": started.isoformat(),
        "selection_method": "First five popularity pages per release year; not a complete catalog or random sample.",
        "query_parameters": {
            "primary_release_date.gte": f"{START_YEAR}-01-01",
            "primary_release_date.lte": today.isoformat(),
            "pages_per_year": PAGES_PER_YEAR,
        },
        "requests": requests,
        "response": {"results": movies},
    }
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    temporary_path = OUTPUT_PATH.with_suffix(".json.tmp")
    temporary_path.write_text(
        json.dumps(snapshot, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    temporary_path.replace(OUTPUT_PATH)
    print(f"\nSaved: {OUTPUT_PATH.name}")
    print(f"Unique movies saved: {len(movies)}")
    print(f"API requests completed: {len(requests)}")
    print("SQLite database unchanged. Validate this sample before importing.")


if __name__ == "__main__":
    main()
