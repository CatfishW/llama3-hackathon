#!/bin/bash
# Quick Setup Script for LLM Integration

echo "========================================="
echo "Prompt Portal LLM Integration Setup"
echo "========================================="
echo ""

# Check if we're in the right directory
if [ ! -f "backend/requirements.txt" ]; then
    echo "Error: Must run from prompt-portal directory"
    echo "Current directory: $(pwd)"
    exit 1
fi

# Install backend dependencies
echo "📦 Installing backend dependencies..."
cd backend
pip install -r requirements.txt
if [ $? -ne 0 ]; then
    echo "❌ Failed to install dependencies"
    exit 1
fi
echo "✅ Dependencies installed"
echo ""

# Setup environment file
if [ ! -f ".env" ]; then
    echo "📝 Creating .env file from template..."
    cp .env.example .env
    echo "✅ Created .env file"
    echo "⚠️  Please edit backend/.env and set your LLM_SERVER_URL"
else
    echo "ℹ️  .env file already exists"
fi
echo ""

# Check if LLM server is configured
echo "🔍 Checking LLM configuration..."
if grep -q "LLM_SERVER_URL=http://localhost:8080" .env 2>/dev/null; then
    echo "⚠️  Using default LLM_SERVER_URL (http://localhost:8080)"
    echo "   Edit backend/.env if your server is on a different URL"
fi
echo ""

# Test LLM server connectivity
echo "🔌 Testing LLM server connectivity..."
LLM_URL=$(grep LLM_SERVER_URL .env 2>/dev/null | cut -d '=' -f2)
if [ -z "$LLM_URL" ]; then
    LLM_URL="http://localhost:8080"
fi

curl -s --max-time 2 "$LLM_URL/health" > /dev/null 2>&1
if [ $? -eq 0 ]; then
    echo "✅ LLM server is accessible at $LLM_URL"
else
    echo "⚠️  Cannot connect to LLM server at $LLM_URL"
    echo ""
    echo "To start a local llama.cpp server:"
    echo "  llama-server -m ./your-model.gguf --port 8080"
    echo ""
    echo "Or use the MQTT deployment script:"
    echo "  cd ../.."
    echo "  python llamacpp_mqtt_deploy.py --projects prompt_portal"
fi
echo ""

echo "========================================="
echo "Setup Complete!"
echo "========================================="
echo ""
echo "Next steps:"
echo "1. Make sure your LLM server is running"
echo "2. Start the backend:"
echo "   cd backend"
echo "   python run_server.py"
echo ""
echo "3. Test the API:"
echo "   curl http://localhost:8000/api/llm/health"
echo ""
echo "4. See LLM_INTEGRATION_GUIDE.md for usage examples"
echo ""
