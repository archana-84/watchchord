import re
import sqlite3
from contextlib import closing
from datetime import date
from pathlib import Path

import streamlit as st

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATABASE_PATH = PROJECT_ROOT / "demo" / "watchchord_demo.db"


def display_title(title):
    return re.sub(r"^(.*), (The|An|A)( \(\d{4}\))$", r"\2 \1\3", title)


def connect():
    connection = sqlite3.connect(DATABASE_PATH)
    connection.row_factory = sqlite3.Row
    return connection


def load_catalogs():
    with closing(connect()) as connection:
        genres = [r[0] for r in connection.execute(
            "SELECT DISTINCT genre FROM movie_genres ORDER BY genre"
        )]
        titles = dict(sorted(
            [(r[0], display_title(r[1])) for r in connection.execute(
                "SELECT movie_id, title FROM movies"
            )],
            key=lambda item: (item[1].casefold(), item[0]),
        ))
        tables = {r[0] for r in connection.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        )}
        needed = {"tmdb_movies", "tmdb_genres", "tmdb_movie_genres", "movie_links"}
        recent_ready = needed <= tables
        recent, genre_names, recent_genres, links = [], {}, {}, {}
        if recent_ready:
            recent = [dict(r) for r in connection.execute(
                "SELECT * FROM tmdb_movies ORDER BY title, tmdb_id"
            )]
            genre_names = dict(connection.execute(
                "SELECT genre_id, name FROM tmdb_genres"
            ).fetchall())
            for row in connection.execute("SELECT tmdb_id, genre_id FROM tmdb_movie_genres"):
                recent_genres.setdefault(row[0], set()).add(
                    genre_names.get(row[1], "Unknown")
                )
            links = dict(connection.execute(
                "SELECT movie_id, tmdb_id FROM movie_links"
            ).fetchall())
    return genres, titles, recent_ready, recent, genre_names, recent_genres, links


def movielens_matches(preferred_a, preferred_b, excluded, watched):
    with closing(connect()) as connection:
        connection.execute("CREATE TEMP TABLE watched_movies (movie_id INTEGER PRIMARY KEY)")
        connection.executemany(
            "INSERT INTO watched_movies VALUES (?)", [(i,) for i in sorted(set(watched))]
        )
        connection.execute("""
            CREATE TEMP TABLE viewer_preferences (
                viewer TEXT, genre TEXT, PRIMARY KEY (viewer, genre)
            )
        """)
        connection.executemany(
            "INSERT INTO viewer_preferences VALUES (?, ?)",
            [("A", g) for g in preferred_a] + [("B", g) for g in preferred_b],
        )
        return [dict(r) for r in connection.execute(MOVIELENS_QUERY, (excluded,))]


def recent_matches(movies, genres, preferred_a, preferred_b, excluded, watched):
    matches = []
    for movie in movies:
        labels = genres.get(movie["tmdb_id"], set())
        if movie["tmdb_id"] in watched or excluded in labels:
            continue
        if not labels.intersection(preferred_a) or not labels.intersection(preferred_b):
            continue
        matches.append(movie)
    # Preserve the original newest-first order and deterministic ID tie-breaker.
    return sorted(matches, key=lambda m: (
        -date.fromisoformat(m["release_date"]).toordinal(), m["tmdb_id"]
    ))


def match_explanation(labels, preferred_a, preferred_b):
    a = ", ".join(sorted(labels.intersection(preferred_a)))
    b = ", ".join(sorted(labels.intersection(preferred_b)))
    st.caption(f"Matches A: {a}  ·  Matches B: {b}")


MOVIELENS_QUERY = """
            WITH overall AS (
                SELECT overall_average
                FROM rating_baseline
                WHERE id = 1
            ),
            movie_stats AS (
                SELECT
                    movie_id,
                    rating_count,
                    total_rating_points
                FROM movie_rating_summary
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
                SELECT 1
                FROM movie_genres AS g
                JOIN viewer_preferences AS p
                    ON p.genre = g.genre
                WHERE g.movie_id = m.movie_id
                  AND p.viewer = 'A'
            )
            AND EXISTS (
                SELECT 1
                FROM movie_genres AS g
                JOIN viewer_preferences AS p
                    ON p.genre = g.genre
                WHERE g.movie_id = m.movie_id
                  AND p.viewer = 'B'
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



def main():
    st.set_page_config(page_title="WatchChord", page_icon="🎬", layout="wide")
    st.markdown("""
        <style>
        .block-container {max-width: 1440px; padding-top: 2.5rem;}
        [data-testid="stVerticalBlockBorderWrapper"] {border-radius: 14px;}
        h1 {letter-spacing: -0.04em;}
        </style>
    """, unsafe_allow_html=True)
    st.title("WatchChord")
    st.write("Different tastes. One great movie night.")
    st.caption("Choose what you both enjoy. Explore familiar favorites and recent releases side by side.")

    if not DATABASE_PATH.exists():
        st.error("The demo movie database is missing. Please contact the app owner.")
        st.stop()
    try:
        genres, titles, recent_ready, recent, genre_names, recent_genres, links = load_catalogs()
    except sqlite3.Error:
        st.error("The movie catalog could not be loaded. Please contact the app owner.")
        st.stop()
    if not genres or not titles:
        st.error("The movie catalog is empty. Please contact the app owner.")
        st.stop()

    with st.container(border=True):
        st.subheader("Plan your movie night")
        st.caption("Each pick must match at least one genre from each viewer. Changes update both lists automatically.")
        a_col, b_col, avoid_col = st.columns([1, 1, 1], gap="medium")
        with a_col:
            viewer_a = st.multiselect(
                "Viewer A likes", genres, default=["Comedy"] if "Comedy" in genres else [],
                key="viewer_a_genres", placeholder="Choose genres",
            )
        with b_col:
            viewer_b = st.multiselect(
                "Viewer B likes", genres, default=["Adventure"] if "Adventure" in genres else [],
                key="viewer_b_genres", placeholder="Choose genres",
            )
        with avoid_col:
            excluded = st.selectbox(
                "Both want to avoid", [None] + genres,
                format_func=lambda g: "No exclusion" if g is None else g,
                key="excluded_genre",
            )

        with st.expander("Already watched? Exclude movies", expanded=False):
            st.caption("Select movies either viewer has seen. Linked titles are excluded from both lists.")
            watched_left, watched_right = st.columns(2, gap="medium")
            with watched_left:
                watched_ids = st.multiselect(
                    "From the MovieLens catalog", list(titles),
                    format_func=lambda i: titles[i], key="movielens_watched",
                    placeholder="Search movie titles",
                )
            with watched_right:
                recent_titles = {m["tmdb_id"]: m["title"] for m in recent}
                recent_watched = st.multiselect(
                    "From the recent TMDB sample", list(recent_titles),
                    format_func=lambda i: recent_titles[i], key="tmdb_watched",
                    placeholder="Search recent titles", disabled=not recent,
                )
        st.caption(
            f"Avoiding: {excluded or 'no genre'} · "
            f"Watched selections: {len(watched_ids)} from MovieLens, {len(recent_watched)} from TMDB"
        )

    effective_a = {g for g in viewer_a if g != excluded}
    effective_b = {g for g in viewer_b if g != excluded}
    blocked = not effective_a or not effective_b
    if not viewer_a or not viewer_b:
        st.info("Choose at least one genre for each viewer to see your shortlists.")
    elif blocked:
        st.warning("One viewer's only preferred genre is excluded. Add another genre or change the exclusion.")
    elif excluded in viewer_a or excluded in viewer_b:
        st.info(f"{excluded} is excluded. We'll use the remaining preferred genres.")

    all_watched_ids = set(watched_ids)

    # Connect watched movies across sources using the ID crosswalk.
    watched_tmdb = set(recent_watched) | {
        links[movie_id]
        for movie_id in all_watched_ids
        if links.get(movie_id) is not None
    }

    watched_movielens = all_watched_ids | {
        movie_id
        for movie_id, tmdb_id in links.items()
        if tmdb_id in watched_tmdb
    }

    aliases = {"Sci-Fi": "Science Fiction"}
    requested = set(viewer_a + viewer_b) | ({excluded} if excluded else set())
    unsupported = sorted(g for g in requested if aliases.get(g, g) not in set(genre_names.values()))

    st.subheader("Your shared shortlists")
    st.caption("Two sources, two ways to browse. The scores use different scales and are not directly comparable.")
    library_col, recent_col = st.columns(2, gap="medium")

    with library_col:
        st.subheader("MovieLens picks")
        st.caption("Best weighted ratings first · Scores out of 5 · Ratings through September 2018")
        if blocked:
            st.info("Your MovieLens picks will appear after you update the preferences above.")
        else:
            recommendations = movielens_matches(effective_a, effective_b, excluded, watched_movielens)
            st.caption(f"Showing {len(recommendations)} picks · Up to 10 movies")
            if not recommendations:
                st.info("No matches in this catalog. Try another preferred genre or review your exclusions.")
            for position, movie in enumerate(recommendations, 1):
                with st.container(border=True):
                    st.markdown(f"#### {position}. {display_title(movie['title'])}")
                    st.caption(movie["genres"].replace("|", " · "))
                    st.markdown(f"**{movie['weighted_score']:.3f} / 5** · Weighted rating")
                    st.caption(f"Based on {movie['rating_count']:,} ratings")
                    match_explanation(set(movie["genres"].split("|")), effective_a, effective_b)

    with recent_col:
        st.subheader("Recent discoveries")
        st.caption(f"Newest releases first · Scores out of 10 · {len(recent)} saved movies from 2024 onward")
        if not recent_ready or not recent:
            st.info("Recent movies aren't loaded yet. Your MovieLens shortlist is still available.")
        elif blocked:
            st.info("Your recent picks will appear after you update the preferences above.")
        elif unsupported:
            st.info("TMDB has no direct category match for: " + ", ".join(unsupported)
                    + ". Change those selections to browse recent movies. MovieLens still works on the left.")
        else:
            missing_links = sum(
                links.get(i) is None for i in all_watched_ids
            )
            if missing_links:
                st.warning(f"{missing_links} watched selection(s) couldn't be linked to TMDB. "
                           "If they appear in the recent watched list, select them there too.")
            preferred_a = {aliases.get(g, g) for g in effective_a}
            preferred_b = {aliases.get(g, g) for g in effective_b}
            matches = recent_matches(recent, recent_genres, preferred_a, preferred_b,
                                     aliases.get(excluded, excluded), watched_tmdb)
            st.caption(f"Showing {min(10, len(matches))} of {len(matches)} matches in this saved sample")
            if not matches:
                st.info("No matches in this small sample. The full TMDB catalog may have more options.")
            for position, movie in enumerate(matches[:10], 1):
                with st.container(border=True):
                    st.markdown(f"#### {position}. {movie['title']}")
                    labels = recent_genres.get(movie["tmdb_id"], set())
                    st.caption(" · ".join(sorted(labels)))
                    if movie["vote_count"]:
                        st.markdown(f"**{movie['vote_average']:.1f} / 10** · TMDB community score")
                    else:
                        st.markdown("**Not rated yet**")
                    st.caption(f"Released {movie['release_date']} · {movie['vote_count']:,} votes")
                    match_explanation(labels, preferred_a, preferred_b)
                    if movie.get("overview"):
                        with st.expander("Read synopsis"):
                            st.write(movie["overview"])
            fetched_dates = sorted({m["fetched_at_utc"][:10] for m in recent})
            if fetched_dates:
                dates_label = fetched_dates[0] if len(fetched_dates) == 1 else f"{fetched_dates[0]} to {fetched_dates[-1]}"
                st.caption(f"Sample fetched: {dates_label}. Release dates do not indicate streaming availability.")

    st.divider()
    with st.expander("About the scores and movie data"):
        st.write("MovieLens scores combine each movie's ratings with the overall average, "
                 "using a smoothing weight of 20. They are community rankings, not predictions of your enjoyment.")
        st.write("TMDB movies are ordered by release date. Their community scores are shown separately "
                 "and are not converted into MovieLens scores. Recent discovery searches the saved sample, not the live catalog.")
        st.caption("Genre exclusions follow source labels and are not content-safety guarantees. "
                   "Sci-Fi maps to Science Fiction. Categories without direct matches are explained above.")
        st.markdown("MovieLens data: [GroupLens](https://grouplens.org/datasets/movielens/). "
                    "Recent movie information: [TMDB](https://www.themoviedb.org/).")
        st.caption("This product uses the TMDB API but is not endorsed or certified by TMDB.")


if __name__ == "__main__":
    main()
