import sqlite3
from pathlib import Path
import re
import streamlit as st

def display_title(title):
    return re.sub(
        r"^(.*), (The|An|A)( \(\d{4}\))$",
        r"\2 \1\3",
        title,
    )

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATABASE_PATH = PROJECT_ROOT / "database" / "watchchord.db"

st.set_page_config(
    page_title="WatchChord",
    page_icon="🎬",
    layout="centered",
)

st.title("WatchChord")
st.write("Different tastes. One great movie night.")
st.caption(
    "Find movies matching both viewers' genre choices, "
    "while excluding unwanted genres and movies already watched."
)

if not DATABASE_PATH.exists():
    st.error("The movie database is missing. Run the database setup first.")
    st.stop()

connection = sqlite3.connect(DATABASE_PATH)

try:
    genres = [
        row[0]
        for row in connection.execute(
            "SELECT DISTINCT genre FROM movie_genres ORDER BY genre;"
        )
    ]

    movies = connection.execute("""
        SELECT movie_id, title
        FROM movies
        ORDER BY title, movie_id;
    """).fetchall()
finally:
    connection.close()

if not genres or not movies:
    st.error("Load the movies and build the genre table first.")
    st.stop()

movie_titles = dict(
    sorted(
        [
            (movie_id, display_title(title))
            for movie_id, title in movies
        ],
        key=lambda item: (item[1].casefold(), item[0]),
    )
)
st.subheader("Who's watching?")

left, right = st.columns(2)

with left:
    viewer_a = st.selectbox(
        "Viewer A's preferred genre",
        options=genres,
        index=genres.index("Comedy"),
        key="viewer_a",
    )

with right:
    viewer_b = st.selectbox(
        "Viewer B's preferred genre",
        options=genres,
        index=genres.index("Adventure"),
        key="viewer_b",
    )

excluded_genre = st.selectbox(
    "Genre either viewer wants to avoid",
    options=[None] + genres,
    format_func=lambda genre: "No exclusion" if genre is None else genre,
)

watched_ids = st.multiselect(
    "Movies either viewer has already watched",
    options=list(movie_titles),
    format_func=lambda movie_id: movie_titles[movie_id],
    placeholder="Type a movie title to search",
)

st.divider()
st.subheader("Your movie-night preferences")

st.write(f"**Viewer A:** {viewer_a}")
st.write(f"**Viewer B:** {viewer_b}")
st.write(f"**Excluded genre:** {excluded_genre or 'None'}")
st.write(f"**Movies already watched:** {len(watched_ids)}")

if excluded_genre in (viewer_a, viewer_b):
    st.warning(
        "A preferred genre is also excluded. "
        "Change a preference or the exclusion to find matching movies."
    )

st.caption(
    "Movie data: MovieLens Latest Small, GroupLens. "
    "This dataset contains ratings through September 2018."
)

st.divider()
st.subheader("Your shared shortlist")

if excluded_genre in (viewer_a, viewer_b):
    st.info("Resolve the conflicting genre choices above to see recommendations.")
else:
    connection = sqlite3.connect(DATABASE_PATH)
    connection.row_factory = sqlite3.Row

    try:
        connection.execute("""
            CREATE TEMP TABLE watched_movies (
                movie_id INTEGER PRIMARY KEY
            );
        """)

        connection.executemany(
            "INSERT INTO watched_movies (movie_id) VALUES (?);",
            [(movie_id,) for movie_id in sorted(set(watched_ids))],
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
                SELECT 1 FROM watched_movies AS w
                WHERE w.movie_id = m.movie_id
            )
            ORDER BY
                weighted_score DESC,
                s.rating_count DESC,
                m.movie_id ASC
            LIMIT 10;
        """

        recommendations = connection.execute(
            query,
            (viewer_a, viewer_b, excluded_genre),
        ).fetchall()

    finally:
        connection.close()

    if not recommendations:
        st.info(
            "No rated movies match all your choices. "
            "Try changing a preferred genre or reviewing your exclusions."
        )
    else:
        st.caption(
            "Ranked by a weighted community rating, not a prediction "
            "of either viewer's enjoyment. Genre exclusions use dataset "
            "labels and are not content-safety guarantees."
        )

        for position, movie in enumerate(recommendations, start=1):
            with st.container(border=True):
                st.subheader(
                    f"{position}. {display_title(movie['title'])}"
                )
                st.write(movie["genres"].replace("|", " · "))

                if viewer_a == viewer_b:
                    st.write(
                        f"**Why it matches:** Tagged {viewer_a}, "
                        "the genre both viewers selected."
                    )
                else:
                    st.write(
                        f"**Why it matches:** Tagged {viewer_a} for "
                        f"Viewer A and {viewer_b} for Viewer B."
                    )

                st.caption(
                    f"Weighted rating: {movie['weighted_score']:.3f} / 5"
                    f" · Based on {movie['rating_count']:,} ratings"
                )
