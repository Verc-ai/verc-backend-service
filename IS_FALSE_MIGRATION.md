# IS_FALSE Column Migration Guide

## Overview
The `IS_FALSE` column is used to mark invalid/test calls that should be excluded from all metrics, analytics, and call history.

## ⚠️ CRITICAL BEHAVIOR
- **Default Value**: `TRUE` (all calls are marked as INVALID by default)
- **ALL EXISTING CALLS** will be excluded from metrics until manually marked as valid
- **IS_FALSE = TRUE**: Invalid/test call - EXCLUDED from all metrics and call history
- **IS_FALSE = FALSE**: Valid call - INCLUDED in metrics and call history

## Database Migration

### Step 1: Add the Column to Supabase

Run this SQL in your Supabase SQL Editor:

```sql
-- Add IS_FALSE column with default TRUE
ALTER TABLE transcription_sessions
ADD COLUMN "IS_FALSE" BOOLEAN NOT NULL DEFAULT TRUE;

-- Verify the column was added
SELECT column_name, data_type, column_default
FROM information_schema.columns
WHERE table_name = 'transcription_sessions'
AND column_name = 'IS_FALSE';
```

### Step 2: Mark Valid Calls

After adding the column, **ALL calls will be excluded** from metrics. You must manually mark valid calls:

#### Option A: Mark ALL calls as valid
```sql
UPDATE transcription_sessions
SET "IS_FALSE" = FALSE;
```

#### Option B: Mark calls from a specific date range as valid
```sql
UPDATE transcription_sessions
SET "IS_FALSE" = FALSE
WHERE created_at >= '2024-01-01' AND created_at < '2025-01-01';
```

#### Option C: Mark specific calls as valid
```sql
UPDATE transcription_sessions
SET "IS_FALSE" = FALSE
WHERE id IN (
    '00000000-0000-0000-0000-000000000001',
    '00000000-0000-0000-0000-000000000002',
    '00000000-0000-0000-0000-000000000003'
);
```

#### Option D: Mark calls NOT matching test patterns as valid
```sql
-- Example: Mark all calls as valid except those with 'test' in phone number
UPDATE transcription_sessions
SET "IS_FALSE" = FALSE
WHERE phone_number NOT LIKE '%test%';
```

## Implementation Details

### Code Changes Made
The following query functions now filter by `IS_FALSE = FALSE`:

1. `get_sessions_count()` - Total calls count
2. `get_acceptance_rate()` - Acceptance rate calculation
3. `get_avg_handle_time()` - Average handle time
4. `get_daily_metrics()` - Daily trends
5. `get_call_intents()` - Call intents distribution
6. `get_sentiment_distribution()` - Sentiment analysis
7. `get_compliance_scorecard_summary()` - Compliance pass/fail
8. `get_servicing_scorecard_summary()` - Servicing pass/fail
9. `get_collections_scorecard_summary()` - Collections pass/fail

**File Modified**: `apps/analytics/services/queries.py`

### Filter Pattern
All queries now include:
```python
.eq("IS_FALSE", False)  # Only include valid calls (IS_FALSE=FALSE)
```

## Usage Examples

### Mark a single call as invalid (exclude from metrics)
```sql
UPDATE transcription_sessions
SET "IS_FALSE" = TRUE
WHERE id = 'call-id-here';
```

### Mark a single call as valid (include in metrics)
```sql
UPDATE transcription_sessions
SET "IS_FALSE" = FALSE
WHERE id = 'call-id-here';
```

### Find all invalid calls
```sql
SELECT id, created_at, phone_number
FROM transcription_sessions
WHERE "IS_FALSE" = TRUE
ORDER BY created_at DESC;
```

### Find all valid calls
```sql
SELECT id, created_at, phone_number
FROM transcription_sessions
WHERE "IS_FALSE" = FALSE
ORDER BY created_at DESC;
```

### Count valid vs invalid calls
```sql
SELECT
    "IS_FALSE",
    COUNT(*) as count
FROM transcription_sessions
GROUP BY "IS_FALSE";
```

## Testing the Migration

### Before Migration:
1. Note current total_calls in analytics dashboard
2. Note current scorecard pass/fail counts

### After Migration (with all calls still TRUE):
1. Check analytics dashboard - should show 0 calls
2. Check scorecard summaries - should show 0 passes/fails
3. Verify call history is empty (if call history also filters)

### After Marking Calls as Valid (FALSE):
1. Check analytics dashboard - should show only marked calls
2. Verify counts match the number of calls marked as valid
3. Test that newly marked calls appear immediately

## Rollback Plan

### Option 1: Set all calls to valid
```sql
UPDATE transcription_sessions
SET "IS_FALSE" = FALSE;
```

### Option 2: Drop the column entirely
```sql
ALTER TABLE transcription_sessions
DROP COLUMN "IS_FALSE";
```

**Note**: If you drop the column, you must also revert the code changes in `apps/analytics/services/queries.py` to remove the `.eq("IS_FALSE", False)` filters, otherwise all queries will fail.

## Monitoring

### Check which calls are excluded
```sql
SELECT
    id,
    created_at,
    phone_number,
    "IS_FALSE" as is_invalid
FROM transcription_sessions
WHERE "IS_FALSE" = TRUE
ORDER BY created_at DESC
LIMIT 100;
```

### Verify filter is working
```sql
-- This should match the count shown in analytics dashboard
SELECT COUNT(*) as valid_calls
FROM transcription_sessions
WHERE "IS_FALSE" = FALSE;
```

## Important Notes

1. **No API endpoint** provided - flag must be managed via direct SQL
2. **New calls default to TRUE** (invalid) - must be explicitly marked as FALSE to appear
3. **Historical data**: All existing calls are marked TRUE (invalid) by default
4. **Case sensitive**: Column name is uppercase `"IS_FALSE"` (requires quotes in SQL)
5. **Performance**: Filter adds minimal overhead as it's a simple boolean check

## Support

If you need to bulk update the IS_FALSE flag based on specific criteria, write custom SQL queries following the patterns above.
