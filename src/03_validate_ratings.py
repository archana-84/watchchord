import csv
from collections import Counter
from decimal import Decimal, InvalidOperation
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
RATINGS_FILE = (
    PROJECT_ROOT / "data" / "raw" / "ml-latest-small" / "ratings.csv"
)

allowed_ratings = {Decimal(i) / 2 for i in range(1, 11)}

invalid_user_ids = 0
invalid_ratings = 0
user_movie_pairs = Counter()
unique_users = set()
rating_counts = Counter()

with RATINGS_FILE.open("r", encoding="utf-8", newline="") as file:
    for row in csv.DictReader(file):
        user_id = row["userId"].strip()
        movie_id = row["movieId"].strip()

        try:
            parsed_user_id = int(user_id)
            if parsed_user_id <= 0:
                raise ValueError
        except ValueError:
            invalid_user_ids += 1
        else:
            unique_users.add(parsed_user_id)
            user_movie_pairs[(parsed_user_id, movie_id)] += 1

        try:
            rating = Decimal(row["rating"].strip())
        except InvalidOperation:
            invalid_ratings += 1
        else:
            if rating not in allowed_ratings:
                invalid_ratings += 1
            else:
                rating_counts[rating] += 1

duplicate_pairs = sum(
    count > 1 for count in user_movie_pairs.values()
)
extra_rows = sum(
    count - 1 for count in user_movie_pairs.values() if count > 1
)

print(f"Invalid user IDs: {invalid_user_ids}")
print(f"Invalid ratings: {invalid_ratings}")
print(f"Repeated user-movie pairs: {duplicate_pairs}")
print(f"Extra rows for repeated pairs: {extra_rows}")
print(f"Unique valid users: {len(unique_users):,}")

print("\nRating distribution:")
for rating in sorted(allowed_ratings):
    print(f"{rating:.1f} stars: {rating_counts[rating]:,}")