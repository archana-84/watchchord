import json
import tomllib
import ssl
import certifi
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

PROJECT_ROOT = Path(__file__).resolve().parent.parent
SECRETS_PATH = PROJECT_ROOT / ".streamlit" / "secrets.toml"


def main():
    try:
        with SECRETS_PATH.open("rb") as file:
            secrets = tomllib.load(file)
    except FileNotFoundError:
        print("Could not find .streamlit/secrets.toml.")
        return
    except tomllib.TOMLDecodeError:
        print("Check the formatting and quotation marks in secrets.toml.")
        return

    token = secrets.get("TMDB_READ_ACCESS_TOKEN", "")
    if not isinstance(token, str) or not token.strip():
        print("TMDB_READ_ACCESS_TOKEN is missing or empty.")
        return

    request = Request(
        "https://api.themoviedb.org/3/genre/movie/list?language=en",
        headers={
            "Authorization": f"Bearer {token.strip()}",
            "Accept": "application/json",
        },
    )

    try:
        context = ssl.create_default_context(cafile=certifi.where())

        with urlopen(request, timeout=20, context=context) as response:
            data = json.load(response)
    except HTTPError as error:
        print(f"TMDB returned HTTP {error.code}.")
        if error.code == 401:
            print("Check that you copied the API Read Access Token.")
        return
    except URLError as error:
        print(f"Connection error: {error.reason}")
        return
    except TimeoutError:
        print("The request timed out after 20 seconds.")
        return
    except (json.JSONDecodeError, UnicodeDecodeError):
        print("TMDB returned an unreadable response. Try again later.")
        return

    genres = data.get("genres", [])
    if not genres:
        print("The response did not contain any movie genres.")
        return

    print("TMDB connection successful!")
    print(f"Movie genres received: {len(genres)}")

    for genre in genres:
        print(f"{genre['id']}: {genre['name']}")


if __name__ == "__main__":
    main()