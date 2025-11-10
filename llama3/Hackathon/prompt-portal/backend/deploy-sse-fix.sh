#!/bin/bash
# Quick fix deployment script for SSE mode maze game issue

echo "=========================================="
echo "  Maze Game SSE Mode Fix - Deployment"
echo "=========================================="
echo ""

# Check if running in backend directory
if [ ! -f "app/main.py" ]; then
    echo "❌ Error: Must run from backend directory"
    echo "   cd to: prompt-portal/backend"
    exit 1
fi

echo "✅ Running in backend directory"
echo ""

# Check .env configuration
echo "Checking configuration..."
if [ -f ".env" ]; then
    source .env
    
    if [ "$LLM_COMM_MODE" != "sse" ] && [ "$LLM_COMM_MODE" != "SSE" ]; then
        echo "⚠️  Warning: LLM_COMM_MODE is not set to 'sse'"
        echo "   Current value: $LLM_COMM_MODE"
        echo "   This fix is specifically for SSE mode"
        read -p "   Continue anyway? (y/n) " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            exit 1
        fi
    else
        echo "✅ LLM_COMM_MODE=sse"
    fi
    
    if [ -z "$LLM_SERVER_URL" ]; then
        echo "⚠️  Warning: LLM_SERVER_URL not set"
    else
        echo "✅ LLM_SERVER_URL=$LLM_SERVER_URL"
    fi
else
    echo "⚠️  Warning: .env file not found"
    echo "   Make sure configuration is set via environment variables"
fi

echo ""

# Test llama.cpp connectivity (if URL is set)
if [ ! -z "$LLM_SERVER_URL" ]; then
    echo "Testing llama.cpp server connectivity..."
    # Extract hostname and port
    SERVER_URL="${LLM_SERVER_URL#http://}"
    SERVER_URL="${SERVER_URL#https://}"
    
    if curl -s -f "${LLM_SERVER_URL}/health" > /dev/null 2>&1; then
        echo "✅ llama.cpp server is reachable"
    else
        echo "⚠️  Warning: Cannot reach llama.cpp server at $LLM_SERVER_URL"
        echo "   Make sure:"
        echo "   1. SSH tunnel is active: ssh -R 8080:127.0.0.1:8080 root@vpn.agaii.org -N"
        echo "   2. llama-server is running on the 4090 machine"
        read -p "   Continue anyway? (y/n) " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            exit 1
        fi
    fi
fi

echo ""

# Find running backend processes
echo "Checking for running backend processes..."
BACKEND_PIDS=$(ps aux | grep "uvicorn app.main:app" | grep -v grep | awk '{print $2}')

if [ ! -z "$BACKEND_PIDS" ]; then
    echo "Found running backend process(es): $BACKEND_PIDS"
    read -p "Stop existing backend? (y/n) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        echo "Stopping backend processes..."
        echo "$BACKEND_PIDS" | xargs kill
        sleep 2
        echo "✅ Backend stopped"
    fi
else
    echo "No running backend found"
fi

echo ""

# Start backend
echo "Starting backend with SSE mode fix..."
echo "Command: uvicorn app.main:app --host 0.0.0.0 --port 3000 --reload"
echo ""
echo "📝 Watch for these log messages:"
echo "   - 'UnifiedLLMService initialized in SSE mode'"
echo "   - '[SSE MODE] Auto-generating hint for publish_state'"
echo ""
echo "Press Ctrl+C to stop the server"
echo ""
sleep 2

# Start with reload for development
uvicorn app.main:app --host 0.0.0.0 --port 3000 --reload
