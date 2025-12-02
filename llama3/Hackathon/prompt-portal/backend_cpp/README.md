# Prompt Portal - C++ Backend

A high-performance alternative backend implementation for Prompt Portal using modern C++20 and the Crow web framework.

## Features

- **High Performance**: Native C++ execution with minimal overhead
- **API Compatible**: Drop-in replacement for the Python/FastAPI backend
- **Modern C++20**: Uses latest C++ standards and best practices
- **SQLite Database**: Same database schema as the Python backend
- **JWT Authentication**: Secure token-based authentication
- **CORS Support**: Full CORS handling for frontend integration
- **LLM Integration**: OpenAI-compatible chat completions with streaming
- **Session Management**: Conversation history with auto-trimming

## Requirements

### Build Requirements

- **CMake** 3.16 or higher
- **C++ Compiler** with C++20 support:
  - GCC 10+ (Linux)
  - Clang 12+ (Linux/macOS)
  - MSVC 2019+ (Windows with Visual Studio)
  - MinGW-w64 (Windows alternative)

### System Dependencies

**Windows:**
- Visual Studio 2019+ with C++ workload, OR
- MinGW-w64 (can be installed via MSYS2)

**Linux (Ubuntu/Debian):**
```bash
sudo apt update
sudo apt install build-essential cmake libsqlite3-dev
```

**macOS:**
```bash
xcode-select --install
brew install cmake sqlite
```

## Building

### Windows (PowerShell)

```powershell
# Debug build
.\build.ps1

# Release build
.\build.ps1 -Release

# Clean and build
.\build.ps1 -Clean

# Build and run
.\build.ps1 -Run
```

### Linux/macOS

```bash
# Make script executable
chmod +x build.sh

# Debug build
./build.sh

# Release build
./build.sh --release

# Clean and build
./build.sh --clean

# Build and run
./build.sh --run
```

### Manual Build

```bash
mkdir build && cd build
cmake .. -DCMAKE_BUILD_TYPE=Release
cmake --build . --parallel
```

## Running

```bash
# From the build directory
./prompt_portal_cpp

# Or with custom config
./prompt_portal_cpp /path/to/config.json
```

The server will start on `http://0.0.0.0:8000` by default.

## Configuration

Edit `config/config.json` to customize settings:

```json
{
    "server": {
        "host": "0.0.0.0",
        "port": 8000,
        "threads": 4
    },
    "database": {
        "path": "./app.db"
    },
    "auth": {
        "secret_key": "change_me_in_production",
        "algorithm": "HS256",
        "token_expire_minutes": 60
    },
    "cors": {
        "allowed_origins": [
            "http://localhost:5173",
            "http://localhost:3000"
        ],
        "allow_credentials": true
    }
}
```

## API Endpoints

### Authentication
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/auth/register` | Register new user |
| POST | `/api/auth/login` | Login and get token |
| POST | `/api/auth/change-password` | Change password |
| DELETE | `/api/auth/account` | Delete account |

### Users
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/users/me` | Get current user |
| GET | `/api/users/search` | Search users |
| GET | `/api/users/<id>` | Get user by ID |

### Templates
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/templates` | List templates |
| POST | `/api/templates` | Create template |
| GET | `/api/templates/<id>` | Get template |
| GET | `/api/templates/public/<id>` | Get public template |
| PATCH | `/api/templates/<id>` | Update template |
| DELETE | `/api/templates/<id>` | Delete template |

### Leaderboard
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/leaderboard` | Get leaderboard |
| POST | `/api/leaderboard/submit` | Submit maze score |
| POST | `/api/leaderboard/driving-game/submit` | Submit driving score |
| GET | `/api/leaderboard/stats` | Get statistics |

### Health
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/health` | Health check |

### LLM (Chat Completion)
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/llm/chat` | Single-shot chat completion |
| POST | `/api/llm/chat/session` | Session-based chat |
| POST | `/api/llm/chat/stream` | Streaming chat (SSE) |
| POST | `/api/llm/chat/session/stream` | Session streaming chat |
| GET | `/api/llm/chat/session/{id}/history` | Get session history |
| POST | `/api/llm/chat/session/history` | Get history (POST variant) |
| DELETE | `/api/llm/chat/session/{id}` | Clear session |
| GET | `/api/llm/health` | LLM service health |

## Dependencies (Auto-downloaded by CMake)

- **[Crow](https://github.com/CrowCpp/Crow)** - C++ micro web framework
- **[nlohmann/json](https://github.com/nlohmann/json)** - JSON for Modern C++
- **[SQLiteCpp](https://github.com/SRombauts/SQLiteCpp)** - C++ SQLite wrapper
- **[jwt-cpp](https://github.com/Thalhammer/jwt-cpp)** - JWT library (headers only, signature implementation built-in)

## Differences from Python Backend

| Feature | Python Backend | C++ Backend |
|---------|---------------|-------------|
| MQTT Support | ✅ Full support | ❌ Not implemented |
| WebSocket | ✅ Full support | ❌ Not implemented |
| Voice Chat | ✅ Full support | ❌ Not implemented |
| SSE Mode | ✅ Supported | ✅ Recommended |
| Performance | Good | Excellent |
| Memory Usage | Higher | Lower |
| Build Time | None (interpreted) | Requires compilation |

## Switching Between Backends

Both backends are API-compatible. To switch:

1. Stop the current backend
2. Start the other backend
3. Ensure both use the same `app.db` database file

```bash
# Stop Python backend and start C++ backend
# From backend_cpp directory:
./build/prompt_portal_cpp

# Or vice versa - from backend directory:
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```

## Development

### Project Structure

```
backend_cpp/
├── CMakeLists.txt          # Build configuration
├── config/
│   └── config.json         # Server configuration
├── include/
│   ├── auth.hpp            # Authentication
│   ├── config.hpp          # Configuration loading
│   ├── database.hpp        # Database operations
│   ├── models.hpp          # Data models
│   ├── handlers/           # Request handlers
│   ├── middleware/         # Middleware (CORS)
│   └── utils/              # Utilities (JWT, password)
├── src/
│   ├── main.cpp            # Entry point
│   ├── auth.cpp            # Auth implementation
│   ├── database.cpp        # Database implementation
│   ├── handlers/           # Handler implementations
│   └── utils/              # Utility implementations
├── build.ps1               # Windows build script
├── build.sh                # Linux/macOS build script
└── README.md               # This file
```

### Adding New Endpoints

1. Add handler declaration in `include/handlers/`
2. Implement handler in `src/handlers/`
3. Register route in `src/main.cpp`

## License

Same license as the main Prompt Portal project.

## Troubleshooting

### Build Errors

**"CMake not found"**
- Install CMake from https://cmake.org/download/

**"No C++ compiler found"**
- Windows: Install Visual Studio with C++ workload
- Linux: `sudo apt install build-essential`
- macOS: `xcode-select --install`

**"SQLite not found"**
- CMake will download SQLiteCpp which includes SQLite
- If issues persist on Linux: `sudo apt install libsqlite3-dev`

### Runtime Errors

**"Database locked"**
- Ensure only one backend instance is running
- Check no other process is accessing `app.db`

**"Connection refused"**
- Verify the server is running
- Check firewall settings
- Ensure correct port in config

