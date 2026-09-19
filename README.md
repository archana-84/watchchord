# WatchChord

### Finding a movie two people can agree on

Choosing a movie can take longer than expected when two people enjoy different things. I built WatchChord to make that choice easier. Each viewer selects the genres they like, and the app creates a shortlist of movies that match both people's choices.

The project brings together data cleaning, SQL, movie ratings, and API data in a simple Streamlit app.

**Tools:** Python, SQL, SQLite, Streamlit, and the TMDB API.

## What the app does

- Lets each viewer choose one or more preferred genres.
- Finds movies that match at least one selected genre from each viewer.
- Removes movies with an unwanted genre and movies either person has already watched.
- Explains which genres match each person's choices.
- Shows older catalog recommendations and newer movie discoveries side by side.

For example, if Viewer A chooses **Comedy** and Viewer B chooses **Adventure**, a movie must include both genres to appear. If they also exclude **Horror**, any movie labeled Horror is removed, even if it matches their other choices.

When there are no matches, the app explains that instead of showing movies that ignore the selections.

## The two movie lists

| | MovieLens picks | Recent discoveries |
| --- | --- | --- |
| Source | MovieLens | Saved TMDB sample |
| Purpose | Explore the older movie catalog | Discover releases from 2024 onward |
| Order | Highest weighted community rating first | Newest release date first |
| Score shown | Weighted score out of 5 | TMDB community score out of 10 |
| Results displayed | Up to 10 matching movies | Up to 10 matching movies |

I kept these lists separate because their scores come from different rating communities and use different methods. A TMDB score of 8/10 should not be treated as equivalent to a MovieLens weighted score of 4/5.

Recent discoveries also include a movie summary when one is available. The app reads saved data from SQLite, so this section is a snapshot rather than a live search of the full TMDB catalog.

## How I built it

### Preparing the data

I started with the MovieLens CSV files, checked the records, and loaded the movies, ratings, and genres into SQLite. I used separate tables so that each movie could connect to its ratings and multiple genres.

The current version contains:

| Data | Count |
| --- | ---: |
| MovieLens movies | 9,742 |
| MovieLens ratings | 100,836 |
| MovieLens movies with a TMDB link | 9,734 |
| Saved TMDB movies | 291 |

The TMDB download requested popular movies from each year, starting in 2024. The recorded run returned 300 records across 15 requests, leaving **291 unique movies** after repeated IDs were removed. These counts describe the saved sample and can change after another download.

### Ranking the MovieLens results

A movie with one five-star rating has less supporting evidence than a movie rated highly by hundreds of people. To account for this, I used a weighted rating that combines a movie's average rating with the overall dataset average.

Movies with fewer ratings are pulled more toward the overall average. As the number of ratings increases, the movie's own average has more influence. This helps reduce the advantage of a high score based on very few ratings.

The app first applies both viewers' genre choices and watched-movie exclusions, then ranks the eligible MovieLens movies. Recent TMDB movies follow a different rule: they are ordered by release date, not by score.

### Connecting the two sources

MovieLens and TMDB use different IDs for the same movie. For example, **Toy Story (1995)** has MovieLens ID **1** and TMDB ID **862**. I used the MovieLens links file to connect these IDs so that watched selections can apply across both lists where a link exists.

Genre names also differ. I mapped **Sci-Fi** to **Science Fiction**, but did not assume that categories such as **Children** and **Family** mean exactly the same thing. If a selected category has no direct match in TMDB, the app explains the limitation.

## Data checks

Before using the data, I checked movie IDs, duplicate records, rating values, and links between records. For the TMDB sample, I also checked titles, release dates, genre lists, and vote counts.

The expanded TMDB sample had:

- No invalid or repeated movie IDs after deduplication.
- No missing titles, invalid release dates, or dates outside the requested range.
- No invalid vote averages or vote counts.
- **One movie without genres:** it can be stored, but cannot match genre preferences.
- **Six movies with zero votes:** these appear as **Not rated yet**.

These checks help catch data problems; they do not independently verify every detail supplied by the sources.

## Limitations

WatchChord uses genre rules and community ratings. It does not predict how much either viewer will enjoy a movie, and I have not measured recommendation quality through a user study.

MovieLens covers an older catalog, while recent discovery uses a limited, popularity-based TMDB sample. The app does not cover every movie, and no matches in the sample does not mean no suitable movies exist.

Watched-movie exclusions across sources depend on the available ID links. Genre exclusions depend on the supplied labels and are not detailed content filters. A movie's release date also does not confirm availability on a streaming service.

This version runs locally, with no accounts or saved personal profiles.

## Data credits

MovieLens data is provided by [GroupLens](https://grouplens.org/datasets/movielens/). Recent movie information is provided by [TMDB](https://www.themoviedb.org/).

This product uses the TMDB API but is not endorsed or certified by TMDB.
