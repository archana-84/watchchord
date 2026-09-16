import csv
from pathlib import Path

# Locate the project folder using this script's location.
PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data" / "raw" / "ml-latest-small"

for filename in ["movies.csv", "ratings.csv", "tags.csv", "links.csv"]:
    file_path = DATA_DIR / filename

    with file_path.open("r", encoding="utf-8", newline="") as file:
        reader = csv.DictReader(file)
        columns = reader.fieldnames
        first_row = next(reader, None)
        row_count = 0 if first_row is None else 1 + sum(1 for _ in reader)

    print(f"\nFile: {filename}")
    print(f"Columns: {columns}")
    print(f"Records: {row_count:,}")
    print(f"First record: {first_row}")