import json
from collections import Counter
from datetime import date
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
SAMPLE_PATH = PROJECT_ROOT / "data" / "raw" / "tmdb_recent_sample.json"

with SAMPLE_PATH.open("r", encoding="utf-8") as file:
    snapshot = json.load(file)

movies = snapshot["response"]["results"]
parameters = snapshot["query_parameters"]

start_date = date.fromisoformat(parameters["primary_release_date.gte"])
end_date = date.fromisoformat(parameters["primary_release_date.lte"])

valid_ids = []
invalid_ids = 0
missing_titles = 0
invalid_dates = 0
outside_date_range = 0
missing_genres = 0
invalid_vote_averages = 0
invalid_vote_counts = 0
zero_vote_movies = 0

for movie in movies:
    movie_id = movie.get("id")
    if type(movie_id) is int and movie_id > 0:
        valid_ids.append(movie_id)
    else:
        invalid_ids += 1

    title = movie.get("title")
    if not isinstance(title, str) or not title.strip():
        missing_titles += 1

    try:
        release_date = date.fromisoformat(movie.get("release_date", ""))
    except (ValueError, TypeError):
        invalid_dates += 1
    else:
        if not start_date <= release_date <= end_date:
            outside_date_range += 1

    genres = movie.get("genre_ids")
    if not isinstance(genres, list) or not genres:
        missing_genres += 1

    vote_average = movie.get("vote_average")
    if (
        type(vote_average) not in (int, float)
        or not 0 <= vote_average <= 10
    ):
        invalid_vote_averages += 1

    vote_count = movie.get("vote_count")
    if type(vote_count) is not int or vote_count < 0:
        invalid_vote_counts += 1
    elif vote_count == 0:
        zero_vote_movies += 1

duplicate_ids = sum(
    count > 1 for count in Counter(valid_ids).values()
)

print(f"Records checked: {len(movies)}")
print(f"Invalid movie IDs: {invalid_ids}")
print(f"Repeated movie IDs: {duplicate_ids}")
print(f"Missing titles: {missing_titles}")
print(f"Invalid or missing release dates: {invalid_dates}")
print(f"Outside requested date range: {outside_date_range}")
print(f"Missing genre lists: {missing_genres}")
print(f"Invalid vote averages: {invalid_vote_averages}")
print(f"Invalid vote counts: {invalid_vote_counts}")
print(f"Movies with zero votes: {zero_vote_movies}")