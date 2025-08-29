#!/bin/bash

# Server Management Utility Script for Prompt Portal
# This script provides common management tasks

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

print_header() {
    echo -e "${BLUE}================================================${NC}"
    echo -e "${BLUE}        Prompt Portal Server Management${NC}"
    echo -e "${BLUE}================================================${NC}"
    echo ""
}

print_step() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

show_status() {
    print_header
    print_step "Service Status:"
    echo ""
    
    # PM2 status
    echo -e "${YELLOW}PM2 Services:${NC}"
    pm2 status || echo "PM2 not running"
    echo ""
    
    # Nginx status
    echo -e "${YELLOW}Nginx Status:${NC}"
    sudo systemctl status nginx --no-pager -l || echo "Nginx not running"
    echo ""
    
    # Port usage
    echo -e "${YELLOW}Port Usage:${NC}"
    sudo netstat -tlnp | grep -E ':80|:443|:8000|:1883' || echo "No services found on standard ports"
    echo ""
    
    # Disk space
    echo -e "${YELLOW}Disk Usage:${NC}"
    df -h / | grep -E '^Filesystem|/'
    echo ""
    
    # Memory usage
    echo -e "${YELLOW}Memory Usage:${NC}"
    free -h
}

show_logs() {
    echo "Which logs would you like to view?"
    echo "1) Backend logs (PM2)"
    echo "2) Nginx access logs"
    echo "3) Nginx error logs"
    echo "4) System logs"
    echo "5) All logs (last 20 lines each)"
    
    read -p "Choose (1-5): " choice
    
    case $choice in
        1)
            print_step "Backend logs (last 50 lines):"
            pm2 logs prompt-portal-backend --lines 50
            ;;
        2)
            print_step "Nginx access logs (last 50 lines):"
            sudo tail -50 /var/log/nginx/access.log
            ;;
        3)
            print_step "Nginx error logs (last 50 lines):"
            sudo tail -50 /var/log/nginx/error.log
            ;;
        4)
            print_step "System logs (last 50 lines):"
            sudo journalctl -u prompt-portal --lines 50
            ;;
        5)
            print_step "All logs summary:"
            echo -e "${YELLOW}=== Backend Logs ===${NC}"
            pm2 logs prompt-portal-backend --lines 20 | tail -20
            echo -e "${YELLOW}=== Nginx Error Logs ===${NC}"
            sudo tail -20 /var/log/nginx/error.log
            echo -e "${YELLOW}=== System Logs ===${NC}"
            sudo journalctl -u nginx --lines 20 | tail -20
            ;;
        *)
            print_error "Invalid choice"
            ;;
    esac
}

restart_services() {
    print_step "Restarting services..."
    
    echo "What would you like to restart?"
    echo "1) Backend only"
    echo "2) Nginx only"
    echo "3) All services"
    
    read -p "Choose (1-3): " choice
    
    case $choice in
        1)
            print_step "Restarting backend..."
            pm2 restart prompt-portal-backend
            print_step "Backend restarted!"
            ;;
        2)
            print_step "Restarting Nginx..."
            sudo systemctl restart nginx
            print_step "Nginx restarted!"
            ;;
        3)
            print_step "Restarting all services..."
            pm2 restart all
            sudo systemctl restart nginx
            print_step "All services restarted!"
            ;;
        *)
            print_error "Invalid choice"
            ;;
    esac
}

backup_data() {
    print_step "Creating backup..."
    
    BACKUP_DIR="/opt/backups"
    DATE=$(date +%Y%m%d_%H%M%S)
    
    sudo mkdir -p $BACKUP_DIR
    
    # Backup database
    if [ -f "backend/app.db" ]; then
        sudo cp backend/app.db $BACKUP_DIR/app.db.$DATE
        print_step "Database backed up to: $BACKUP_DIR/app.db.$DATE"
    else
        print_warning "Database file not found"
    fi
    
    # Backup environment
    if [ -f "backend/.env" ]; then
        sudo cp backend/.env $BACKUP_DIR/.env.$DATE
        print_step "Environment backed up to: $BACKUP_DIR/.env.$DATE"
    fi
    
    # Show backup list
    echo -e "${YELLOW}Recent backups:${NC}"
    sudo ls -la $BACKUP_DIR/ | tail -10
}

restore_backup() {
    print_step "Available backups:"
    
    BACKUP_DIR="/opt/backups"
    
    if [ ! -d "$BACKUP_DIR" ]; then
        print_error "No backup directory found"
        return 1
    fi
    
    sudo ls -la $BACKUP_DIR/app.db.* 2>/dev/null || {
        print_error "No database backups found"
        return 1
    }
    
    echo ""
    read -p "Enter the backup filename (e.g., app.db.20250829_143022): " backup_file
    
    if [ -f "$BACKUP_DIR/$backup_file" ]; then
        print_warning "This will replace the current database!"
        read -p "Are you sure? (y/N): " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            # Stop backend
            pm2 stop prompt-portal-backend
            
            # Restore backup
            sudo cp $BACKUP_DIR/$backup_file backend/app.db
            
            # Start backend
            pm2 start prompt-portal-backend
            
            print_step "Database restored from $backup_file"
        else
            print_step "Restore cancelled"
        fi
    else
        print_error "Backup file not found: $backup_file"
    fi
}

update_application() {
    print_step "Updating Prompt Portal..."
    
    print_warning "This will update the application and restart services"
    read -p "Continue? (y/N): " -n 1 -r
    echo
    
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        print_step "Update cancelled"
        return
    fi
    
    # Create backup before update
    backup_data
    
    # Update backend dependencies
    print_step "Updating backend dependencies..."
    cd backend
    source .venv/bin/activate
    pip install --upgrade -r requirements.txt
    cd ..
    
    # Update frontend dependencies and rebuild
    print_step "Updating frontend..."
    cd frontend
    npm install
    npm run build
    cd ..
    
    # Restart services
    print_step "Restarting services..."
    pm2 restart prompt-portal-backend
    sudo systemctl reload nginx
    
    print_step "Update completed successfully!"
}

check_health() {
    print_step "Running health checks..."
    
    SERVER_IP=$(curl -s ifconfig.me || hostname -I | awk '{print $1}')
    
    # Check backend
    echo -e "${YELLOW}Backend Health:${NC}"
    if curl -s "http://localhost:8000/docs" > /dev/null; then
        echo "✅ Backend is responding"
    else
        echo "❌ Backend is not responding"
    fi
    
    # Check frontend
    echo -e "${YELLOW}Frontend Health:${NC}"
    if curl -s "http://$SERVER_IP" > /dev/null; then
        echo "✅ Frontend is accessible"
    else
        echo "❌ Frontend is not accessible"
    fi
    
    # Check database
    echo -e "${YELLOW}Database Health:${NC}"
    if [ -f "backend/app.db" ]; then
        size=$(stat -c%s "backend/app.db")
        echo "✅ Database exists (${size} bytes)"
    else
        echo "❌ Database file not found"
    fi
    
    # Check disk space
    echo -e "${YELLOW}Disk Space:${NC}"
    usage=$(df / | grep -vE '^Filesystem' | awk '{print $5}' | sed 's/%//g')
    if [ $usage -lt 80 ]; then
        echo "✅ Disk space OK (${usage}% used)"
    else
        echo "⚠️  Disk space warning (${usage}% used)"
    fi
}

show_menu() {
    print_header
    echo "Choose an option:"
    echo ""
    echo "1) Show service status"
    echo "2) View logs"
    echo "3) Restart services"
    echo "4) Backup data"
    echo "5) Restore backup"
    echo "6) Update application"
    echo "7) Health check"
    echo "8) Exit"
    echo ""
}

main() {
    while true; do
        show_menu
        read -p "Enter your choice (1-8): " choice
        echo ""
        
        case $choice in
            1) show_status ;;
            2) show_logs ;;
            3) restart_services ;;
            4) backup_data ;;
            5) restore_backup ;;
            6) update_application ;;
            7) check_health ;;
            8) echo "Goodbye!"; exit 0 ;;
            *) print_error "Invalid choice. Please try again." ;;
        esac
        
        echo ""
        read -p "Press Enter to continue..."
        clear
    done
}

# Check if script is run with arguments
if [ $# -gt 0 ]; then
    case $1 in
        status) show_status ;;
        logs) show_logs ;;
        restart) restart_services ;;
        backup) backup_data ;;
        restore) restore_backup ;;
        update) update_application ;;
        health) check_health ;;
        *) echo "Usage: $0 [status|logs|restart|backup|restore|update|health]" ;;
    esac
else
    main
fi
