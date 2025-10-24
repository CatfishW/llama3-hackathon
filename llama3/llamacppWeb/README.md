# Llama.cpp Web Chat Server

A modern, ChatGPT-like web interface for the Llama.cpp MQTT system. Enables multi-user chat interactions with LLM models through a responsive web application.

## Overview

This is a complete full-stack web application that:

- **Frontend**: Interactive web UI with real-time messaging, project selection, and advanced options
- **Backend**: Flask server with WebSocket support for bidirectional communication
- **Integration**: MQTT-based communication with Llama.cpp backend infrastructure
- **Deployment**: Automated scripts for Linux and Windows production deployment

## Quick Features

✨ **Modern Chat Interface** - ChatGPT-like experience with message history
🎯 **Multi-Project Support** - Switch between maze, driving, bloodcell, racing, and general projects
⚙️ **Advanced Options** - Control temperature, top-p sampling, max tokens
💾 **Local Chat History** - Persistent chat storage using browser localStorage
🌙 **Dark/Light Theme** - Toggle between dark and light themes
📱 **Responsive Design** - Works seamlessly on desktop, tablet, and mobile
🔐 **MQTT-Based** - Secure topic-based message routing
🚀 **WebSocket Support** - Real-time bidirectional communication

## Quick Start

### For Development

```bash
# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate.bat

# Install dependencies
pip install -r requirements.txt

# Run server
python app.py

# Open browser to http://localhost:5000
```

### For Production (Linux)

```bash
# Make deployment script executable
chmod +x deploy/deploy.sh

# Run automated installation (requires sudo)
sudo ./deploy/deploy.sh install

# Start service
sudo ./deploy/deploy.sh start

# View logs
sudo ./deploy/deploy.sh logs
```

### For Production (Windows)

```cmd
# Run as Administrator
deploy\deploy.bat install
deploy\deploy.bat start
```

## Project Structure

```
llamacppWeb/
├── app.py                          # Flask backend server
├── requirements.txt                # Python dependencies
├── DEPLOYMENT_GUIDE.md            # Comprehensive deployment guide
├── README.md                       # This file
├── templates/
│   └── index.html                 # Main HTML interface
├── static/
│   ├── css/
│   │   └── style.css              # Application styling
│   └── js/
│       ├── mqtt.js                # MQTT client wrapper
│       ├── storage.js             # Local storage management
│       └── app.js                 # Main application logic
├── config/
│   └── .env.example               # Environment configuration template
└── deploy/
    ├── deploy.sh                  # Linux/Ubuntu deployment script
    └── deploy.bat                 # Windows deployment script
```

## Architecture

### Frontend
- **Vanilla JavaScript** - No framework dependencies, lightweight
- **Paho-MQTT** - Direct MQTT communication from browser
- **LocalStorage API** - Client-side data persistence

### Backend
- **Flask** - Lightweight Python web framework
- **Flask-SocketIO** - WebSocket support for real-time updates
- **Flask-CORS** - Cross-Origin Resource Sharing
- **Paho-MQTT** - MQTT client for broker communication

### Communication Flow
```
Browser (WebSocket)
    ↓
Flask Server
    ↓
MQTT Broker (47.89.252.2:1883)
    ↓
Llama.cpp Backend (llamacpp_mqtt_deploy.py)
    ↓
LLM Model (Inference)
```

## Environment Configuration

Copy `.env.example` to `.env` and update settings:

```bash
# Flask
FLASK_ENV=production
SECRET_KEY=your-secret-key

# Server
HOST=0.0.0.0
PORT=5000

# MQTT
MQTT_BROKER=47.89.252.2
MQTT_PORT=1883
```

## Available Endpoints

### HTTP API

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/` | GET | Main chat interface |
| `/api/config` | GET | Server configuration |
| `/api/health` | GET | Health check |
| `/api/projects` | GET | Available projects |
| `/api/stats` | GET | Server statistics |
| `/static/*` | GET | Static assets |

### WebSocket Events

**Client to Server:**
- `send_message` - Send chat message
- `create_session` - Create new session
- `subscribe_response` - Subscribe to responses

**Server to Client:**
- `message_sent` - Confirmation
- `response_received` - LLM response
- `error` - Error notification

## Configuration Options

### Generation Parameters

| Parameter | Default | Range | Description |
|-----------|---------|-------|-------------|
| Temperature | 0.6 | 0-2 | Randomness in responses |
| Top-P | 0.9 | 0-1 | Diversity of word choices |
| Max Tokens | 512 | 100-4000 | Maximum response length |

### Projects

| Project | Description | Use Case |
|---------|-------------|----------|
| General | General-purpose AI | Default conversations |
| Maze | Maze game hints | Strategic guidance |
| Driving | Physics learning | Driving simulator education |
| Bloodcell | Cell education | Biology learning |
| Racing | Physics racing | Physics concepts |

## Key Features Explained

### Chat History
- Auto-saves to browser localStorage
- Organize by project
- Easy chat switching
- Export/import functionality

### Advanced Options
- Fine-tune generation parameters
- Custom system prompts
- Per-session overrides
- Real-time adjustments

### Multi-Project Support
- Switch projects anytime
- Project-specific system prompts
- Separate conversation threads
- Project filtering

### Session Management
- Automatic session creation
- Persistent session tracking
- Multi-user support
- Rate limiting

## Deployment Guides

### Quick Deployment

**Linux (Ubuntu 20.04+):**
```bash
sudo ./deploy/deploy.sh install
sudo ./deploy/deploy.sh start
```

**Windows (10/11):**
```cmd
deploy\deploy.bat install
deploy\deploy.bat start
```

### Production Checklist

- [ ] Install on separate server/VM
- [ ] Configure MQTT broker address
- [ ] Set strong SECRET_KEY
- [ ] Enable HTTPS with SSL certificate
- [ ] Configure Nginx reverse proxy
- [ ] Setup firewall rules
- [ ] Configure automatic backups
- [ ] Setup monitoring/alerting
- [ ] Test failover procedures

For detailed deployment instructions, see [DEPLOYMENT_GUIDE.md](DEPLOYMENT_GUIDE.md).

## Troubleshooting

### Common Issues

**Cannot connect to MQTT broker**
- Verify broker is running
- Check MQTT_BROKER and MQTT_PORT environment variables
- Ensure firewall allows MQTT port (1883)

**WebSocket connection failed**
- Check Nginx config has WebSocket headers
- Verify socket.io configuration
- Check browser console for errors

**Messages not sending**
- Verify MQTT connection status (indicator in UI)
- Check browser network tab
- Review server logs

**High latency/slow responses**
- Check LLM backend is running properly
- Verify MQTT broker performance
- Monitor server CPU/memory usage

See [DEPLOYMENT_GUIDE.md](DEPLOYMENT_GUIDE.md#troubleshooting) for more solutions.

## Performance Optimization

### Frontend
- Minimized CSS and JavaScript
- Lazy loading of messages
- Local caching of configurations
- Debounced resize handlers

### Backend
- Connection pooling for MQTT
- Message queue for throughput
- Worker threads for concurrency
- Session timeout cleanup

### Infrastructure
- Nginx reverse proxy with gzip compression
- CDN for static assets (optional)
- Database query optimization
- Load balancing support

## Security

### Authentication
- Uses MQTT client ID for session tracking
- Optional MQTT username/password
- Secret key for Flask session

### Transport
- HTTPS support via Nginx
- Secure WebSocket (WSS) capable
- MQTT over TLS (configurable)
- CORS restrictions

### Application
- Input validation
- MQTT message validation
- SQL injection protection (no SQL used)
- XSS protection via template escaping

## Monitoring

### Key Metrics
- Active WebSocket connections
- MQTT message throughput
- Average response latency
- Error rate
- Server resource usage

### Logging
- Application logs: `/var/log/llamacpp-web/app.log`
- Error logs: `/var/log/llamacpp-web/error.log`
- Access logs: `/var/log/nginx/llamacpp_web_access.log`

### Health Checks
```bash
# API health check
curl http://localhost:5000/api/health

# MQTT connectivity test
mosquitto_pub -h 47.89.252.2 -t test -m "ping"
```

## API Examples

### Send Message via HTTP

```bash
# Create session
curl -X POST http://localhost:5000/api/session \
  -H "Content-Type: application/json" \
  -d '{"project":"maze"}'

# Send message
curl -X POST http://localhost:5000/api/message \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": "uuid",
    "message": "How do I solve this maze?",
    "temperature": 0.7
  }'
```

### WebSocket Communication

```javascript
const socket = io('http://localhost:5000');

// Send message
socket.emit('send_message', {
  session_id: 'uuid',
  project: 'maze',
  message: 'Hello!',
  temperature: 0.6,
  topP: 0.9,
  maxTokens: 512
});

// Receive response
socket.on('response_received', (data) => {
  console.log('Response:', data.message);
});
```

## Development

### Prerequisites
- Python 3.8+
- pip and virtualenv
- Modern web browser
- Text editor or IDE

### Development Setup

```bash
# Clone/navigate to project
cd llamacppWeb

# Create virtual environment
python3 -m venv venv

# Activate
source venv/bin/activate

# Install dev dependencies
pip install -r requirements.txt

# Run with debug mode
FLASK_ENV=development FLASK_DEBUG=True python app.py
```

### Code Structure

**Backend (app.py)**
- Configuration management
- Flask app initialization
- HTTP route handlers
- WebSocket event handlers
- MQTT client wrapper

**Frontend (static/js)**
- `mqtt.js` - MQTT client abstraction
- `storage.js` - LocalStorage management
- `app.js` - Main application logic
- `index.html` - HTML structure
- `style.css` - Styling

### Contributing

1. Create feature branch
2. Make changes
3. Test thoroughly
4. Submit pull request

## Future Enhancements

- [ ] User authentication and authorization
- [ ] Message search and filtering
- [ ] Chat sharing and collaboration
- [ ] Mobile native apps
- [ ] Voice input/output
- [ ] Image support
- [ ] Plugin system
- [ ] Analytics dashboard

## License

Part of the Llama3 Hackathon project.

## Support

- 📖 [Deployment Guide](DEPLOYMENT_GUIDE.md)
- 🐛 [GitHub Issues](https://github.com/CatfishW/llama3-hackathon/issues)
- 💬 [Discussions](https://github.com/CatfishW/llama3-hackathon/discussions)

## Related Projects

- [Llama.cpp MQTT Deploy](../llamacpp_mqtt_deploy.py) - Backend LLM server
- [Llama.cpp Repository](https://github.com/ggerganov/llama.cpp)
- [MQTT Broker](https://mosquitto.org/)
- [Flask Web Framework](https://flask.palletsprojects.com/)
