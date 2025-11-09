#!/bin/bash
# Quick Start Script for Machine A (LLM Server with GPU)
# This script starts the llama.cpp server and creates the reverse SSH tunnel

set -e

# ============================================================================
# CONFIGURATION - Edit these values
# ============================================================================

# LLM Server Configuration
LLAMACPP_DIR="$HOME/llama.cpp"        # Path to llama.cpp directory
MODEL_PATH="models/qwen3-30b-a3b-instruct-2507-Q4_K_M.gguf"  # Model file
CONTEXT_SIZE=28192                     # Context window size
GPU_LAYERS=35                          # Number of layers to offload to GPU
THREADS=8                              # CPU threads
PARALLEL=8                             # Parallel requests
SERVER_PORT=8080                       # Local server port

# Remote Server Configuration (Machine B)
REMOTE_USER="user"                     # SSH user on Machine B
REMOTE_HOST="your-server-ip"          # Machine B IP or domain
REMOTE_PORT=8080                       # Port on Machine B

# ============================================================================
# Colors
# ============================================================================
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

print_banner() {
    echo -e "${BLUE}╔════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${BLUE}║         LLM Server + Tunnel Quick Start                   ║${NC}"
    echo -e "${BLUE}╚════════════════════════════════════════════════════════════╝${NC}"
    echo ""
}

print_info() { echo -e "${BLUE}[INFO]${NC} $1"; }
print_success() { echo -e "${GREEN}[SUCCESS]${NC} $1"; }
print_warning() { echo -e "${YELLOW}[WARNING]${NC} $1"; }
print_error() { echo -e "${RED}[ERROR]${NC} $1"; }

# ============================================================================
# Main
# ============================================================================

print_banner

# Check if configuration is set
if [ "$REMOTE_HOST" = "your-server-ip" ]; then
    print_error "Please edit this script and update the CONFIGURATION section!"
    exit 1
fi

# Check if llama.cpp exists
if [ ! -d "$LLAMACPP_DIR" ]; then
    print_error "llama.cpp directory not found: $LLAMACPP_DIR"
    print_info "Clone it with: git clone https://github.com/ggerganov/llama.cpp"
    exit 1
fi

# Check if model exists
if [ ! -f "$LLAMACPP_DIR/$MODEL_PATH" ]; then
    print_error "Model not found: $LLAMACPP_DIR/$MODEL_PATH"
    print_info "Download a GGUF model and place it in the models directory"
    exit 1
fi

# Check if screen is installed
if ! command -v screen &> /dev/null; then
    print_error "screen is not installed. Install it with: sudo apt install screen"
    exit 1
fi

print_info "Configuration:"
echo "  LLM Server: $LLAMACPP_DIR"
echo "  Model:      $MODEL_PATH"
echo "  Context:    $CONTEXT_SIZE tokens"
echo "  GPU Layers: $GPU_LAYERS"
echo "  Remote:     $REMOTE_USER@$REMOTE_HOST:$REMOTE_PORT"
echo ""

# Kill existing sessions if they exist
print_info "Stopping existing sessions..."
screen -S llama -X quit 2>/dev/null || true
screen -S tunnel -X quit 2>/dev/null || true
sleep 1

# Start LLM server in screen
print_info "Starting llama.cpp server..."
screen -dmS llama bash -c "
cd '$LLAMACPP_DIR'
./llama-server \
  -m '$MODEL_PATH' \
  --host 0.0.0.0 \
  --port $SERVER_PORT \
  -c $CONTEXT_SIZE \
  -ngl $GPU_LAYERS \
  -t $THREADS \
  --parallel $PARALLEL
"

print_info "Waiting for server to start (15 seconds)..."
sleep 15

# Test if server is running
if curl -s --max-time 2 http://localhost:$SERVER_PORT/health &> /dev/null; then
    print_success "LLM server is running!"
else
    print_error "LLM server failed to start"
    print_info "Check logs with: screen -r llama"
    exit 1
fi

# Start reverse SSH tunnel in screen
print_info "Creating reverse SSH tunnel..."
screen -dmS tunnel bash -c "
while true; do
    echo \"\$(date): Starting SSH tunnel...\"
    ssh -R $REMOTE_PORT:localhost:$SERVER_PORT \
        -o ServerAliveInterval=30 \
        -o ServerAliveCountMax=3 \
        -o ExitOnForwardFailure=yes \
        -o StrictHostKeyChecking=no \
        $REMOTE_USER@$REMOTE_HOST -N
    
    echo \"\$(date): Tunnel disconnected. Reconnecting in 5 seconds...\"
    sleep 5
done
"

sleep 2

print_success "All services started!"
echo ""
echo -e "${GREEN}╔════════════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║                   🎉 Setup Complete! 🎉                    ║${NC}"
echo -e "${GREEN}╚════════════════════════════════════════════════════════════╝${NC}"
echo ""
print_info "Services running in background:"
echo "  • LLM Server (screen session 'llama')"
echo "  • SSH Tunnel (screen session 'tunnel')"
echo ""
print_info "Useful commands:"
echo "  screen -ls                    # List all sessions"
echo "  screen -r llama               # Attach to LLM server (Ctrl+A, D to detach)"
echo "  screen -r tunnel              # Attach to tunnel (Ctrl+A, D to detach)"
echo "  curl http://localhost:$SERVER_PORT/health  # Test server locally"
echo ""
print_info "On Machine B (web server), verify tunnel:"
echo "  ssh $REMOTE_USER@$REMOTE_HOST"
echo "  curl http://localhost:$REMOTE_PORT/health"
echo ""
print_info "To stop everything:"
echo "  screen -S llama -X quit"
echo "  screen -S tunnel -X quit"
echo ""
print_success "Your LLM server is now accessible from Machine B via SSH tunnel!"
