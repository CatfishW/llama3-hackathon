#!/bin/bash
set -e

DOMAIN_NAME="lammp.agaii.org"
NGINX_CONFIG="/etc/nginx/sites-available/${DOMAIN_NAME}"
BACKUP_PATTERN="${NGINX_CONFIG}.backup"

if [ ! -f "$NGINX_CONFIG" ]; then
  echo "❌ Nginx config not found at $NGINX_CONFIG" >&2
  exit 1
fi

LATEST_BACKUP=$(ls -t ${BACKUP_PATTERN}* 2>/dev/null | head -n1)
if [ -z "$LATEST_BACKUP" ]; then
  echo "❌ No backup files found for $NGINX_CONFIG" >&2
  exit 1
fi

echo "📦 Backing up current nginx config before revert..."
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
sudo cp "$NGINX_CONFIG" "${NGINX_CONFIG}.restore_${TIMESTAMP}"

echo "⏪ Restoring nginx config from: $LATEST_BACKUP"
sudo cp "$LATEST_BACKUP" "$NGINX_CONFIG"

echo "🧪 Testing nginx configuration..."
if sudo nginx -t; then
  echo "✅ Config test passed"
  echo "🔄 Reloading nginx"
  sudo systemctl reload nginx
  echo "✅ Nginx reloaded. Current config restored from $LATEST_BACKUP"
else
  echo "❌ Config test failed. Keeping previous restore backup at ${NGINX_CONFIG}.restore_${TIMESTAMP}" >&2
  exit 1
fi
