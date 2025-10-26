# Deployment Checklist - New Scoring System

## Pre-Deployment

- [ ] **Backup Database**
  ```bash
  # Create a backup of your current database
  # Location: Check your database configuration
  ```

- [ ] **Review Changes**
  - [ ] Read `IMPLEMENTATION_SUMMARY.md`
  - [ ] Review `NEW_SCORING_SYSTEM.md`
  - [ ] Check `SCORING_METRICS_GUIDE.md`

- [ ] **Test Environment Ready**
  - [ ] Backend server stopped
  - [ ] Database accessible
  - [ ] Python environment activated

## Deployment Steps

### Step 1: Database Migration
```bash
cd Z:\llama3_20250528\llama3\Hackathon\prompt-portal\backend
python add_new_score_column.py
```

**Expected Output:**
```
============================================================
Database Migration: Add New Score Columns
============================================================
Adding new_score and metrics columns to scores table...
✓ Added new_score column
✓ Added total_steps column
✓ Added optimal_steps column
✓ Added backtrack_count column
✓ Added collision_count column
✓ Added dead_end_entries column
✓ Added avg_latency_ms column

✅ Migration completed successfully!
```

- [ ] Migration completed without errors
- [ ] All 7 columns added successfully

### Step 2: Restart Backend
```bash
cd Z:\llama3_20250528\llama3\Hackathon\prompt-portal\backend
python run_server.py
```

**Check:**
- [ ] Server starts without errors
- [ ] No database schema errors in logs
- [ ] API accessible at expected port

### Step 3: Frontend Build (if needed)
```bash
cd Z:\llama3_20250528\llama3\Hackathon\prompt-portal\frontend
npm run build
# OR for development:
npm run dev
```

- [ ] Build completes successfully
- [ ] No TypeScript errors
- [ ] Frontend serves correctly

### Step 4: Functional Testing

#### Test 1: Play Manual Mode
- [ ] Start a new game in Manual mode
- [ ] Complete the game (win or lose)
- [ ] Score submission succeeds
- [ ] Both scores displayed in success message

#### Test 2: Play LAM Mode
- [ ] Start a new game in LAM mode
- [ ] Complete the game
- [ ] Higher score multiplier applied
- [ ] Metrics tracked correctly

#### Test 3: View Leaderboard
- [ ] Navigate to leaderboard
- [ ] See "New Score" column (green)
- [ ] See "Old Score" column (yellow, faded)
- [ ] See "Metrics" column
- [ ] Historical scores show NULL for new_score
- [ ] Recent scores show both values

#### Test 4: Score Calculation Verification
- [ ] Quick completion (< 40 sec) gives speed bonus
- [ ] Time deduction applies (-1 per 10 sec)
- [ ] Collision penalty applies
- [ ] Path efficiency bonus applies
- [ ] Oxygen collection counted correctly

#### Test 5: Edge Cases
- [ ] Game loss handled correctly
- [ ] Zero oxygen collection works
- [ ] Maximum collision scenario works
- [ ] Very fast completion works
- [ ] Very slow completion works

## Post-Deployment Verification

### Database Check
```bash
# Check if new columns exist
# Run SQL query or check via database admin tool
SELECT new_score, total_steps, collision_count 
FROM scores 
ORDER BY created_at DESC 
LIMIT 5;
```

- [ ] New columns exist
- [ ] Recent entries have values
- [ ] Historical entries have NULL (expected)
- [ ] No data corruption

### API Check
```bash
# Test score submission endpoint
curl -X POST http://localhost:8000/api/leaderboard/submit \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <token>" \
  -d '{
    "template_id": 1,
    "session_id": "test-123",
    "score": 1000,
    "new_score": 5000,
    "total_steps": 50,
    "optimal_steps": 40,
    "survival_time": 45.5,
    "oxygen_collected": 3,
    "germs": 5,
    "mode": "manual"
  }'
```

- [ ] Endpoint accepts new_score
- [ ] Metrics fields accepted
- [ ] Response includes all fields

### Frontend Check
- [ ] Leaderboard loads without errors
- [ ] Scores display correctly
- [ ] Sorting works (new_score priority)
- [ ] Responsive design intact
- [ ] Mobile view works

## Performance Monitoring

### First 24 Hours
- [ ] Monitor server CPU/memory usage
- [ ] Check database query performance
- [ ] Monitor API response times
- [ ] Review error logs

### First Week
- [ ] Collect player feedback
- [ ] Analyze score distributions
- [ ] Check for scoring anomalies
- [ ] Verify leaderboard accuracy

## Rollback Plan (if needed)

If critical issues arise:

1. **Stop accepting new scores**
   - Comment out new_score calculation in WebGame.tsx
   - Keep submitting old score only

2. **Revert leaderboard display**
   - Change sorting back to old score
   - Hide new_score column temporarily

3. **Database rollback** (last resort)
   ```sql
   -- Only if absolutely necessary
   ALTER TABLE scores DROP COLUMN new_score;
   ALTER TABLE scores DROP COLUMN total_steps;
   -- etc...
   ```

## Success Criteria

Deployment is successful if:
- [x] ✅ All tests pass
- [x] ✅ No database errors
- [x] ✅ No backend errors
- [x] ✅ No frontend errors
- [x] ✅ Scores submit correctly
- [x] ✅ Leaderboard displays both scores
- [x] ✅ Historical data preserved
- [x] ✅ Time deduction working
- [x] ✅ Metrics tracking accurate

## Common Issues & Solutions

### Issue: Migration fails
**Solution**: 
- Check database connection
- Verify write permissions
- Review migration script output
- Check if columns already exist

### Issue: Backend won't start
**Solution**:
- Check models.py syntax
- Verify all imports
- Check database connection string
- Review error logs

### Issue: Frontend shows errors
**Solution**:
- Clear browser cache
- Rebuild frontend
- Check console for errors
- Verify API responses

### Issue: Scores not submitting
**Solution**:
- Check network requests in browser DevTools
- Verify authentication token
- Check backend logs for errors
- Validate payload format

## Support Resources

- **Implementation Summary**: `IMPLEMENTATION_SUMMARY.md`
- **Scoring Documentation**: `NEW_SCORING_SYSTEM.md`
- **Metrics Guide**: `SCORING_METRICS_GUIDE.md`
- **Migration Script**: `backend/add_new_score_column.py`

## Sign-Off

- [ ] **Developer**: Changes reviewed and tested
- [ ] **QA**: All test cases passed
- [ ] **Database**: Migration successful
- [ ] **Deployment**: System operational

**Deployment Date**: _____________
**Deployed By**: _____________
**Status**: ☐ Success  ☐ Partial  ☐ Rollback

---

**Notes**:
_Add any deployment-specific notes here_
