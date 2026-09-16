WITH overall AS (
    SELECT AVG(rating) AS overall_average
    FROM ratings
),
movie_stats AS (
    SELECT
        movie_id,
        COUNT(*) AS rating_count,
        AVG(rating) AS average_rating,
        SUM(rating) AS total_rating_points
    FROM ratings
    GROUP BY movie_id
),
scored_movies AS (
    SELECT
        m.movie_id,
        m.title,
        s.rating_count,
        s.average_rating,
        (
            s.total_rating_points
            + 20.0 * o.overall_average
        ) / (s.rating_count + 20.0) AS weighted_score
    FROM movie_stats AS s
    JOIN movies AS m
        ON s.movie_id = m.movie_id
    CROSS JOIN overall AS o
)
SELECT
    movie_id,
    title,
    rating_count,
    ROUND(average_rating, 2) AS average_rating,
    ROUND(weighted_score, 3) AS weighted_score
FROM scored_movies
ORDER BY
    scored_movies.weighted_score DESC,
    rating_count DESC,
    movie_id ASC
LIMIT 10;