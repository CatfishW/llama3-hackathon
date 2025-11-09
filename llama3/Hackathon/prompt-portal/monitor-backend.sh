#!/bin/bash
# Backend health monitoring script
# Automatically restarts backend if health check fails multiple times

HEALTH_URL="http://localhost:8000/api/health"
MAX_FAILURES=3
FAILURE_COUNT=0
LOG_FILE="/var/log/prompt-portal/health-monitor.log"

log_message() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" >> "$LOG_FILE"
}

check_health() {
    response=$(curl -s -o /dev/null -w "%{http_code}" --max-time 10 "$HEALTH_URL" 2>&1)
    echo "$response"
}

log_message "Health monitor started"

while true; do
    HTTP_CODE=$(check_health)
    
    if [ "$HTTP_CODE" != "200" ]; then
        FAILURE_COUNT=$((FAILURE_COUNT + 1))
        log_message "Health check failed: HTTP $HTTP_CODE (failures: $FAILURE_COUNT/$MAX_FAILURES)"
        
        if [ $FAILURE_COUNT -ge $MAX_FAILURES ]; then
            log_message "Max failures reached. Restarting backend service..."
            systemctl restart prompt-portal-backend
            
            # Wait for restart
            sleep 10
            
            # Verify restart
            NEW_CODE=$(check_health)
            if [ "$NEW_CODE" = "200" ]; then
                log_message "Backend successfully restarted and healthy"
                FAILURE_COUNT=0
            else
                log_message "Backend restart failed! Manual intervention required."
                # Optional: Send alert
                # curl -X POST "https://api.telegram.org/bot<TOKEN>/sendMessage" \
                #      -d "chat_id=<CHAT_ID>&text=🚨 Backend restart failed at lammp.agaii.org"
            fi
        fi
    else
        if [ $FAILURE_COUNT -gt 0 ]; then
            log_message "Health check recovered (was failing)"
        fi
        FAILURE_COUNT=0
    fi
    
    sleep 30  # Check every 30 seconds
done
