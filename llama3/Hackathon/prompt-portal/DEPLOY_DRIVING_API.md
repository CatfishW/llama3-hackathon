# Deploy New /api/driving Endpoints to Production

## What Needs to be Deployed

### Backend Changes
1. **New router file**: `backend/app/routers/driving.py`
2. **Updated main**: `backend/app/main.py` (imports driving router)
3. **Models** (already deployed): `backend/app/models.py` (DrivingGameScore)
4. **Schemas** (already deployed): `backend/app/schemas.py`

### Frontend Changes
1. **New API**: `frontend/src/api.ts` (drivingStatsAPI)
2. **Updated pages**: `frontend/src/pages/DrivingStats.tsx`
3. **New build**: `frontend/dist/assets/index-PZf2rn-J.js`

## Deployment Steps

### Step 1: Deploy Backend

SSH into your production server:
```bash
ssh your-user@lammp.agaii.org
cd /path/to/prompt-portal/backend

# Pull latest code
git pull origin main

# Or manually copy the new files:
# - app/routers/driving.py (NEW FILE)
# - app/main.py (updated)

# Restart backend service
sudo systemctl restart prompt-portal-backend
# or
pm2 restart prompt-portal-backend
# or kill and restart uvicorn process
```

### Step 2: Deploy Frontend

```bash
# On production server
cd /path/to/prompt-portal/frontend

# Copy new dist files
# Upload the new dist folder from local to production

# Or rebuild on production:
npm run build

# Restart nginx/web server
sudo systemctl restart nginx
```

### Step 3: Verify

Test the new endpoints:
```bash
curl https://lammp.agaii.org/api/driving/stats
curl https://lammp.agaii.org/api/driving/leaderboard?limit=5&skip=0
```

## Quick Deploy Script

```bash
#!/bin/bash
# deploy_driving_api.sh

SERVER="your-user@lammp.agaii.org"
BACKEND_PATH="/path/to/prompt-portal/backend"
FRONTEND_PATH="/path/to/prompt-portal/frontend"

echo "Deploying /api/driving to production..."

# Copy backend files
scp backend/app/routers/driving.py $SERVER:$BACKEND_PATH/app/routers/
scp backend/app/main.py $SERVER:$BACKEND_PATH/app/

# Copy frontend build
scp -r frontend/dist/* $SERVER:$FRONTEND_PATH/dist/

# Restart services
ssh $SERVER "cd $BACKEND_PATH && sudo systemctl restart prompt-portal-backend"
ssh $SERVER "sudo systemctl restart nginx"

echo "Deployment complete!"
echo "Test: https://lammp.agaii.org/api/driving/stats"
```

## Alternative: Test Locally First

If you want to test before deploying to production:

1. **Start local backend**:
   ```bash
   cd backend
   uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
   ```

2. **Start local frontend dev server**:
   ```bash
   cd frontend
   npm run dev
   ```

3. **Access local site**:
   ```
   http://localhost:5173
   ```

4. **Update frontend API base** (if needed):
   Edit `frontend/src/api.ts`:
   ```typescript
   const API_BASE = 'http://localhost:8000'  // for local testing
   ```

## Database Migration (if not done)

Make sure the production database has the `driving_game_scores` table:

```bash
# On production server
cd /path/to/prompt-portal/backend
python -c "from app.database import Base, engine; from app import models; Base.metadata.create_all(bind=engine)"
```

## Troubleshooting

**If endpoints still return 405:**
1. Check backend logs: `journalctl -u prompt-portal-backend -f`
2. Verify driving router is loaded: `curl https://lammp.agaii.org/docs` (should show /api/driving)
3. Check nginx config doesn't block /api/driving paths
4. Restart both backend and nginx

**If frontend still shows old code:**
1. Clear nginx cache
2. Force browser refresh: Ctrl+Shift+R
3. Check dist folder has new build: `index-PZf2rn-J.js`

