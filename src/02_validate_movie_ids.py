import csv
from collections import Counter
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data" / "raw" / "ml-latest-small"

with (DATA_DIR / "movies.csv").open(
    "r", encoding="utf-8", newline=""
) as file:
    movies = list(csv.DictReader(file))

movie_ids = [row["movieId"].strip() for row in movies]
id_counts = Counter(movie_ids)

missing_ids = sum(movie_id == "" for movie_id in movie_ids)
duplicate_ids = sum(
    count > 1 for movie_id, count in id_counts.items() if movie_id
)
known_ids = {movie_id for movie_id in movie_ids if movie_id}

print(f"Movies with missing IDs: {missing_ids}")
print(f"Distinct movie IDs appearing more than once: {duplicate_ids}")

for filename in ["ratings.csv", "tags.csv", "links.csv"]:
    missing = 0
    unmatched = 0

    with (DATA_DIR / filename).open(
        "r", encoding="utf-8", newline=""
    ) as file:
        for row in csv.DictReader(file):
            movie_id = row["movieId"].strip()

            if not movie_id:
                missing += 1
            elif movie_id not in known_ids:
                unmatched += 1

    print(f"\n{filename}")
    print(f"Rows with missing movie IDs: {missing}")
    print(f"Rows referencing unknown movie IDs: {unmatched}")
    