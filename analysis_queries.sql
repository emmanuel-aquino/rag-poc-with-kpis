-- 1. overall pipeline health
SELECT
    COUNT(*)                            AS total_queries,
    AVG(latency_ms)                     AS avg_latency_ms,
    MAX(latency_ms)                     AS max_latency_ms,
    AVG(CAST(retrieved_chunks AS FLOAT)) AS avg_chunks_retrieved
FROM query_log;

-- 2. query volume over time
SELECT
    CAST(timestamp AS DATE)     AS query_date,
    COUNT(*)                    AS queries_per_day
FROM query_log
GROUP BY CAST(timestamp AS DATE)
ORDER BY query_date;

-- 3. most frequently retrieved documents
SELECT
    source_doc,
    COUNT(*)                    AS retrieval_count,
    AVG(relevance_score)        AS avg_relevance_score
FROM retrieval_log
GROUP BY source_doc
ORDER BY retrieval_count DESC;

-- 4. most retrieved sections across all documents
SELECT
    section,
    COUNT(*)                    AS times_retrieved,
    AVG(relevance_score)        AS avg_score
FROM retrieval_log
GROUP BY section
ORDER BY times_retrieved DESC;

-- 5. KPI dashboard — all extracted metrics
SELECT
    company,
    metric_name,
    metric_value,
    period,
    source_doc,
    timestamp
FROM kpi_extractions
ORDER BY company, metric_name, period;

-- 6. KPI coverage by document
SELECT
    source_doc,
    COUNT(DISTINCT metric_name)  AS distinct_metrics,
    COUNT(*)                     AS total_kpi_mentions
FROM kpi_extractions
GROUP BY source_doc
ORDER BY total_kpi_mentions DESC;

-- 7. latency distribution
SELECT
    CASE
        WHEN latency_ms < 2000  THEN 'under 2s'
        WHEN latency_ms < 4000  THEN '2-4s'
        WHEN latency_ms < 6000  THEN '4-6s'
        ELSE 'over 6s'
    END                         AS latency_bucket,
    COUNT(*)                    AS query_count
FROM query_log
GROUP BY
    CASE
        WHEN latency_ms < 2000  THEN 'under 2s'
        WHEN latency_ms < 4000  THEN '2-4s'
        WHEN latency_ms < 6000  THEN '4-6s'
        ELSE 'over 6s'
    END;
