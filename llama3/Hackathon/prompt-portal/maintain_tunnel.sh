#!/bin/bash
# LLM Server Reverse SSH Tunnel Maintainer
# This script establishes and maintains a reverse SSH tunnel from your LLM server
# (Machine A with GPU) to your web server (Machine B with public IP)

set -e

# ============================================================================
# CONFIGURATION - Edit these values for your setup
# ============================================================================

# Machine B (Web Server) Configuration
REMOTE_USER="user"                    # SSH user on Machine B
REMOTE_HOST="your-server-ip"          # Machine B IP or domain
REMOTE_PORT=8080                      # Port on Machine B to bind (localhost:8080)

# Local LLM Server Configuration
LOCAL_PORT=8080                       # Local llama.cpp server port

# Connection Settings
KEEPALIVE_INTERVAL=30                 # Send keepalive every N seconds
KEEPALIVE_MAX=3                       # Reconnect after N failed keepalives
RECONNECT_DELAY=5                     # Wait N seconds before reconnecting

# ============================================================================
# Colors for output
# ============================================================================
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# ============================================================================
# Functions
# ============================================================================

print_banner() {
    echo -e "${BLUE}╔════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${BLUE}║       LLM Server Reverse SSH Tunnel Maintainer            ║${NC}"
    echo -e "${BLUE}╚════════════════════════════════════════════════════════════╝${NC}"
    echo ""
}

print_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

check_prerequisites() {
    print_info "Checking prerequisites..."
    
    # Check if SSH is available
    if ! command -v ssh &> /dev/null; then
        print_error "SSH is not installed. Please install openssh-client."
        exit 1
    fi
    
    # Check if local LLM server is running
    if ! curl -s --max-time 2 http://localhost:${LOCAL_PORT}/health &> /dev/null; then
        print_warning "Local LLM server not responding on port ${LOCAL_PORT}"
        print_warning "Make sure llama.cpp server is running before starting tunnel"
        read -p "Continue anyway? (y/N): " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            exit 1
        fi
    else
        print_success "Local LLM server is running on port ${LOCAL_PORT}"
    fi
    
    # Check SSH key
    if [ ! -f ~/.ssh/id_rsa ] && [ ! -f ~/.ssh/id_ed25519 ]; then
        print_warning "No SSH key found. You'll need to enter password for each connection."
        print_info "Generate a key with: ssh-keygen -t rsa -b 4096"
        print_info "Then copy it to remote: ssh-copy-id ${REMOTE_USER}@${REMOTE_HOST}"
    fi
    
    # Test SSH connection
    print_info "Testing SSH connection to ${REMOTE_USER}@${REMOTE_HOST}..."
    if ssh -o BatchMode=yes -o ConnectTimeout=5 ${REMOTE_USER}@${REMOTE_HOST} exit 2>/dev/null; then
        print_success "SSH connection successful"
    else
        print_error "Cannot connect to ${REMOTE_USER}@${REMOTE_HOST}"
        print_info "Make sure you can SSH to the remote server and have copied your SSH key"
        exit 1
    fi
}

start_tunnel() {
    local attempt=0
    
    while true; do
        attempt=$((attempt + 1))
        
        echo ""
        print_info "$(date '+%Y-%m-%d %H:%M:%S') - Starting tunnel (attempt #${attempt})..."
        print_info "Forwarding: ${REMOTE_HOST}:${REMOTE_PORT} → localhost:${LOCAL_PORT}"
        
        # Start SSH tunnel with keepalive and auto-reconnect settings
        ssh -R ${REMOTE_PORT}:localhost:${LOCAL_PORT} \
            -o ServerAliveInterval=${KEEPALIVE_INTERVAL} \
            -o ServerAliveCountMax=${KEEPALIVE_MAX} \
            -o ExitOnForwardFailure=yes \
            -o StrictHostKeyChecking=no \
            -N \
            ${REMOTE_USER}@${REMOTE_HOST}
        
        EXIT_CODE=$?
        
        print_warning "$(date '+%Y-%m-%d %H:%M:%S') - Tunnel disconnected (exit code: ${EXIT_CODE})"
        
        # Check if we should reconnect
        if [ $EXIT_CODE -eq 130 ]; then
            # Ctrl+C was pressed
            print_info "Tunnel stopped by user"
            break
        fi
        
        print_info "Reconnecting in ${RECONNECT_DELAY} seconds..."
        sleep ${RECONNECT_DELAY}
    done
}

show_config() {
    echo ""
    print_info "Configuration:"
    echo "  Remote Server: ${REMOTE_USER}@${REMOTE_HOST}"
    echo "  Remote Port:   ${REMOTE_PORT} (localhost on Machine B)"
    echo "  Local Port:    ${LOCAL_PORT} (llama.cpp server)"
    echo "  Keepalive:     ${KEEPALIVE_INTERVAL}s interval, ${KEEPALIVE_MAX} max failures"
    echo "  Reconnect:     ${RECONNECT_DELAY}s delay"
    echo ""
}

show_instructions() {
    echo ""
    print_success "Tunnel is now running!"
    echo ""
    print_info "What's happening:"
    echo "  • Your LLM server (localhost:${LOCAL_PORT}) is now accessible on Machine B"
    echo "  • Machine B can connect to http://localhost:${REMOTE_PORT}"
    echo "  • This connection is encrypted and secure"
    echo ""
    print_info "To verify on Machine B:"
    echo "  ssh ${REMOTE_USER}@${REMOTE_HOST}"
    echo "  curl http://localhost:${REMOTE_PORT}/health"
    echo ""
    print_info "To stop the tunnel:"
    echo "  Press Ctrl+C"
    echo ""
    print_warning "Keep this terminal open! Closing it will stop the tunnel."
    echo ""
}

# ============================================================================
# Main
# ============================================================================

print_banner
show_config

# Check if configuration is default
if [ "$REMOTE_HOST" = "your-server-ip" ]; then
    print_error "Please edit this script and update the CONFIGURATION section!"
    print_info "Set REMOTE_USER and REMOTE_HOST to match your web server"
    exit 1
fi

check_prerequisites

# Handle Ctrl+C gracefully
trap 'echo ""; print_info "Shutting down tunnel..."; exit 0' SIGINT SIGTERM

show_instructions

# Start the tunnel (will reconnect automatically if disconnected)
start_tunnel

print_info "Tunnel stopped"
