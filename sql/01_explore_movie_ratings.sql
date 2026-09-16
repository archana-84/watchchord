
SELECT
    m.movie_id,
    m.title,
    COUNT(r.user_id) AS rating_count,
    ROUND(AVG(r.rating), 2) AS average_rating
FROM movies AS m
JOIN ratings AS r
    ON m.movie_id = r.movie_id
GROUP BY
    m.movie_id,
    m.title
ORDER BY
    rating_count DESC,
    m.movie_id ASC
LIMIT 10;