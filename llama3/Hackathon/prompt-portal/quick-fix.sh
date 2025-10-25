#!/bin/bash

# Quick fix script - run this if you're already on the server
# This is a simplified version that you can copy-paste

echo "🔧 Quick Routing Fix"
echo "===================="

cd /root/prompt-portal/frontend

# Fix environment files
echo "Fixing environment files..."
echo "VITE_API_BASE=https://lammp.agaii.org" > .env.production
echo "VITE_WS_BASE=wss://lammp.agaii.org" >> .env.production
echo "VITE_API_BASE=https://lammp.agaii.org" > .env.local
echo "VITE_WS_BASE=wss://lammp.agaii.org" >> .env.local

# Rebuild
echo "Rebuilding frontend..."
npm run build

# Restart frontend
echo "Restarting frontend..."
kill $(cat frontend.pid) 2>/dev/null || true
nohup npm run preview -- --host 0.0.0.0 --port 3001 > /dev/null 2>&1 &
echo $! > frontend.pid

echo ""
echo "✅ Frontend fixed and restarted!"
echo ""
echo "Now fix Nginx manually:"
echo "  sudo nano /etc/nginx/sites-available/lammp.agaii.org"
echo ""
echo "Change these lines:"
echo "  OLD: location /api {"
echo "  NEW: location /api/ {"
echo ""
echo "  OLD: rewrite ^/api/(.*) /\$1 break;"
echo "  NEW: (remove this line completely)"
echo ""
echo "Then reload:"
echo "  sudo nginx -t"
echo "  sudo systemctl reload nginx"
