#!/bin/bash

# Stop Prompt Portal Services
echo "🛑 Stopping Prompt Portal services..."

# Stop backend
if [ -f "backend/backend.pid" ]; then
    BACKEND_PID=$(cat backend/backend.pid)
    if ps -p $BACKEND_PID > /dev/null 2>&1; then
        kill $BACKEND_PID
        echo "✅ Backend stopped (PID: $BACKEND_PID)"
    else
        echo "⚠️ Backend was not running"
    fi
    rm -f backend/backend.pid
else
    echo "⚠️ Backend PID file not found"
fi

# Stop frontend
if [ -f "frontend/frontend.pid" ]; then
    FRONTEND_PID=$(cat frontend/frontend.pid)
    if ps -p $FRONTEND_PID > /dev/null 2>&1; then
        kill $FRONTEND_PID
        echo "✅ Frontend stopped (PID: $FRONTEND_PID)"
    else
        echo "⚠️ Frontend was not running"
    fi
    rm -f frontend/frontend.pid
else
    echo "⚠️ Frontend PID file not found"
fi

# Also kill any processes on the ports as backup
lsof -ti:3000 | xargs kill -9 2>/dev/null || true
lsof -ti:3001 | xargs kill -9 2>/dev/null || true

echo "🏁 All services stopped!"
