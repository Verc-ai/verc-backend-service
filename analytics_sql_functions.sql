-- Analytics SQL Functions for Supabase
-- These functions perform aggregations at the database level for better performance
-- Run these in your Supabase SQL Editor

-- =============================================================================
-- 1. Get Average Call Duration
-- =============================================================================
CREATE OR REPLACE FUNCTION get_avg_call_duration(
    start_date_param TIMESTAMPTZ,
    end_date_param TIMESTAMPTZ
)
RETURNS NUMERIC
LANGUAGE plpgsql
AS $$
DECLARE
    avg_duration NUMERIC;
BEGIN
    SELECT AVG(call_duration)
    INTO avg_duration
    FROM transcription_sessions
    WHERE call_start_time >= start_date_param
      AND call_start_time <= end_date_param
      AND "IS_FALSE" = FALSE
      AND call_duration IS NOT NULL
      AND call_duration > 0;

    RETURN COALESCE(avg_duration, 0);
END;
$$;

-- =============================================================================
-- 2. Get Total Call Duration (Sum)
-- =============================================================================
CREATE OR REPLACE FUNCTION get_total_call_duration(
    start_date_param TIMESTAMPTZ,
    end_date_param TIMESTAMPTZ
)
RETURNS BIGINT
LANGUAGE plpgsql
AS $$
DECLARE
    total_duration BIGINT;
BEGIN
    SELECT SUM(call_duration)
    INTO total_duration
    FROM transcription_sessions
    WHERE call_start_time >= start_date_param
      AND call_start_time <= end_date_param
      AND "IS_FALSE" = FALSE
      AND call_duration IS NOT NULL
      AND call_duration > 0;

    RETURN COALESCE(total_duration, 0);
END;
$$;

-- =============================================================================
-- 3. Get Daily Call Metrics (for trend charts)
-- =============================================================================
CREATE OR REPLACE FUNCTION get_daily_call_counts(
    start_date_param TIMESTAMPTZ,
    end_date_param TIMESTAMPTZ
)
RETURNS TABLE(
    call_date DATE,
    call_count BIGINT
)
LANGUAGE plpgsql
AS $$
BEGIN
    RETURN QUERY
    SELECT
        DATE(call_start_time) as call_date,
        COUNT(*) as call_count
    FROM transcription_sessions
    WHERE call_start_time >= start_date_param
      AND call_start_time <= end_date_param
      AND "IS_FALSE" = FALSE
    GROUP BY DATE(call_start_time)
    ORDER BY call_date;
END;
$$;

-- =============================================================================
-- 4. Get Compliance Scorecard Summary
-- =============================================================================
CREATE OR REPLACE FUNCTION get_compliance_summary(
    start_date_param TIMESTAMPTZ,
    end_date_param TIMESTAMPTZ,
    threshold_param NUMERIC DEFAULT 80
)
RETURNS TABLE(
    pass_count BIGINT,
    fail_count BIGINT,
    total_count BIGINT
)
LANGUAGE plpgsql
AS $$
BEGIN
    RETURN QUERY
    SELECT
        COUNT(*) FILTER (
            WHERE
                (call_scorecard->'categories'->'compliance'->>'pass')::boolean = true
                OR (
                    (call_scorecard->'categories'->'compliance'->>'pass') IS NULL
                    AND (call_scorecard->'categories'->'compliance'->>'score')::numeric >= threshold_param
                )
        ) as pass_count,
        COUNT(*) FILTER (
            WHERE
                (call_scorecard->'categories'->'compliance'->>'pass')::boolean = false
                OR (
                    (call_scorecard->'categories'->'compliance'->>'pass') IS NULL
                    AND (call_scorecard->'categories'->'compliance'->>'score')::numeric < threshold_param
                )
        ) as fail_count,
        COUNT(*) as total_count
    FROM transcription_sessions
    WHERE call_start_time >= start_date_param
      AND call_start_time <= end_date_param
      AND "IS_FALSE" = FALSE
      AND call_scorecard IS NOT NULL
      AND call_scorecard->'categories'->'compliance' IS NOT NULL;
END;
$$;

-- =============================================================================
-- 5. Get Servicing Scorecard Summary
-- =============================================================================
CREATE OR REPLACE FUNCTION get_servicing_summary(
    start_date_param TIMESTAMPTZ,
    end_date_param TIMESTAMPTZ,
    threshold_param NUMERIC DEFAULT 70
)
RETURNS TABLE(
    pass_count BIGINT,
    fail_count BIGINT,
    total_count BIGINT
)
LANGUAGE plpgsql
AS $$
BEGIN
    RETURN QUERY
    SELECT
        COUNT(*) FILTER (
            WHERE
                (call_scorecard->'categories'->'servicing'->>'pass')::boolean = true
                OR (
                    (call_scorecard->'categories'->'servicing'->>'pass') IS NULL
                    AND (call_scorecard->'categories'->'servicing'->>'score')::numeric >= threshold_param
                )
        ) as pass_count,
        COUNT(*) FILTER (
            WHERE
                (call_scorecard->'categories'->'servicing'->>'pass')::boolean = false
                OR (
                    (call_scorecard->'categories'->'servicing'->>'pass') IS NULL
                    AND (call_scorecard->'categories'->'servicing'->>'score')::numeric < threshold_param
                )
        ) as fail_count,
        COUNT(*) as total_count
    FROM transcription_sessions
    WHERE call_start_time >= start_date_param
      AND call_start_time <= end_date_param
      AND "IS_FALSE" = FALSE
      AND call_scorecard IS NOT NULL
      AND call_scorecard->'categories'->'servicing' IS NOT NULL;
END;
$$;

-- =============================================================================
-- 6. Get Collections Scorecard Summary
-- =============================================================================
CREATE OR REPLACE FUNCTION get_collections_summary(
    start_date_param TIMESTAMPTZ,
    end_date_param TIMESTAMPTZ,
    threshold_param NUMERIC DEFAULT 75
)
RETURNS TABLE(
    pass_count BIGINT,
    fail_count BIGINT,
    total_count BIGINT
)
LANGUAGE plpgsql
AS $$
BEGIN
    RETURN QUERY
    SELECT
        COUNT(*) FILTER (
            WHERE
                (call_scorecard->'categories'->'collections'->>'pass')::boolean = true
                OR (
                    (call_scorecard->'categories'->'collections'->>'pass') IS NULL
                    AND (call_scorecard->'categories'->'collections'->>'score')::numeric >= threshold_param
                )
        ) as pass_count,
        COUNT(*) FILTER (
            WHERE
                (call_scorecard->'categories'->'collections'->>'pass')::boolean = false
                OR (
                    (call_scorecard->'categories'->'collections'->>'pass') IS NULL
                    AND (call_scorecard->'categories'->'collections'->>'score')::numeric < threshold_param
                )
        ) as fail_count,
        COUNT(*) as total_count
    FROM transcription_sessions
    WHERE call_start_time >= start_date_param
      AND call_start_time <= end_date_param
      AND "IS_FALSE" = FALSE
      AND call_scorecard IS NOT NULL
      AND call_scorecard->'categories'->'collections' IS NOT NULL;
END;
$$;

-- =============================================================================
-- 7. Get Sentiment Distribution
-- =============================================================================
CREATE OR REPLACE FUNCTION get_sentiment_distribution(
    start_date_param TIMESTAMPTZ,
    end_date_param TIMESTAMPTZ
)
RETURNS TABLE(
    sentiment_category TEXT,
    count_value BIGINT
)
LANGUAGE plpgsql
AS $$
BEGIN
    RETURN QUERY
    SELECT
        COALESCE(call_scorecard->>'sentiment_shift_category', 'neutral') as sentiment_category,
        COUNT(*) as count_value
    FROM transcription_sessions
    WHERE call_start_time >= start_date_param
      AND call_start_time <= end_date_param
      AND "IS_FALSE" = FALSE
      AND call_scorecard IS NOT NULL
    GROUP BY call_scorecard->>'sentiment_shift_category';
END;
$$;

-- =============================================================================
-- Grant execute permissions (adjust role name as needed)
-- =============================================================================
-- GRANT EXECUTE ON FUNCTION get_avg_call_duration TO authenticated;
-- GRANT EXECUTE ON FUNCTION get_total_call_duration TO authenticated;
-- GRANT EXECUTE ON FUNCTION get_daily_call_counts TO authenticated;
-- GRANT EXECUTE ON FUNCTION get_compliance_summary TO authenticated;
-- GRANT EXECUTE ON FUNCTION get_servicing_summary TO authenticated;
-- GRANT EXECUTE ON FUNCTION get_collections_summary TO authenticated;
-- GRANT EXECUTE ON FUNCTION get_sentiment_distribution TO authenticated;

-- =============================================================================
-- Test queries (uncomment to test)
-- =============================================================================
-- SELECT * FROM get_avg_call_duration('2025-01-01'::timestamptz, NOW()::timestamptz);
-- SELECT * FROM get_total_call_duration('2025-01-01'::timestamptz, NOW()::timestamptz);
-- SELECT * FROM get_daily_call_counts('2025-01-01'::timestamptz, NOW()::timestamptz);
-- SELECT * FROM get_compliance_summary('2025-01-01'::timestamptz, NOW()::timestamptz, 80);
-- SELECT * FROM get_servicing_summary('2025-01-01'::timestamptz, NOW()::timestamptz, 70);
-- SELECT * FROM get_collections_summary('2025-01-01'::timestamptz, NOW()::timestamptz, 75);
-- SELECT * FROM get_sentiment_distribution('2025-01-01'::timestamptz, NOW()::timestamptz);
