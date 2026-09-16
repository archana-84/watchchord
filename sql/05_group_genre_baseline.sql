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
group_candidates AS (
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

    -- Match Viewer A's preference.
    WHERE EXISTS (
        SELECT 1
        FROM movie_genres AS g
        WHERE g.movie_id = m.movie_id
          AND g.genre = 'Comedy'
    )

    -- Also match Viewer B's preference.
    AND EXISTS (
        SELECT 1
        FROM movie_genres AS g
        WHERE g.movie_id = m.movie_id
          AND g.genre = 'Adventure'
    )

    -- Respect the group's exclusion.
    AND NOT EXISTS (
        SELECT 1
        FROM movie_genres AS g
        WHERE g.movie_id = m.movie_id
          AND g.genre = 'Horror'
    )
)
SELECT
    movie_id,
    title,
    genres,
    rating_count,
    ROUND(weighted_score, 3) AS weighted_score
FROM group_candidates
ORDER BY
    group_candidates.weighted_score DESC,
    rating_count DESC,
    movie_id ASC
LIMIT 10;