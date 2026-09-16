SELECT
    m.movie_id,
    m.title,
    COUNT(*) AS rating_count,
    ROUND(AVG(r.rating), 2) AS average_rating
FROM movies AS m
JOIN ratings AS r
    ON m.movie_id = r.movie_id
GROUP BY
    m.movie_id,
    m.title
HAVING COUNT(*) <= 5
ORDER BY
    AVG(r.rating) DESC,
    rating_count ASC,
    m.movie_id ASC
LIMIT 15;