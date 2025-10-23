# vLLM Multi-Project MQTT Deployment

A production-ready deployment script for running LLMs (specifically QWQ-32B) with vLLM, supporting multiple concurrent users across different projects via MQTT.

## Features

- **vLLM-Powered**: Leverages vLLM's high-performance inference engine with automatic batching
- **Multi-User Support**: Handles multiple concurrent users efficiently with thread-safe session management
- **Project-Based Routing**: Toggle which topics/projects are active at launch time
- **Session Management**: Per-session conversation history with automatic token limit management
- **MQTT Communication**: Industry-standard MQTT protocol for reliable message delivery
- **Flexible Configuration**: Comprehensive command-line configuration options
- **Production-Ready**: Comprehensive logging, error handling, and graceful shutdown

## Architecture

```
┌─────────────────┐
│  MQTT Clients   │
│  (Various Apps) │
└────────┬────────┘
         │ MQTT Topics
         │ {project}/user_input
         │ {project}/assistant_response
         ▼
┌─────────────────┐
│  MQTT Handler   │
│ - Connection    │
│ - Topic Routing │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Message Queue   │
│ (Priority Queue)│
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Worker Threads  │
│ (Thread Pool)   │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│Session Manager  │
│ - Dialog History│
│ - Token Limits  │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ vLLM Inference  │
│ - Auto Batching │
│ - CUDA Graphs   │
│ - KV Cache      │
└─────────────────┘
```

## Prerequisites

### System Requirements
- Python 3.8+
- CUDA-capable GPU (recommended: NVIDIA A100, RTX 4090, or better)
- 16GB+ GPU VRAM (for QWQ-32B)
- Linux/Windows with CUDA 11.8+

### Python Dependencies
```bash
pip install vllm fire paho-mqtt
```

Or install all requirements:
```bash
pip install -r requirements.txt
```

## Quick Start

### 1. Basic Deployment (Single Project)

Deploy for maze game:
```bash
python vLLMDeploy.py --projects maze
```

### 2. Multi-Project Deployment

Deploy for multiple projects simultaneously:
```bash
python vLLMDeploy.py --projects maze driving bloodcell racing
```

### 3. With Authentication

Deploy with MQTT credentials:
```bash
python vLLMDeploy.py \
  --projects driving \
  --mqtt_username TangClinic \
  --mqtt_password Tang123
```

### 4. Custom Model Configuration

Deploy with custom settings:
```bash
python vLLMDeploy.py \
  --projects general \
  --model Qwen/QwQ-32B \
  --max_model_len 8192 \
  --tensor_parallel_size 2 \
  --gpu_memory_utilization 0.95 \
  --temperature 0.7 \
  --max_tokens 1024
```

### 5. With Quantization (For Limited VRAM)

Deploy with AWQ quantization:
```bash
python vLLMDeploy.py \
  --projects general \
  --quantization awq \
  --gpu_memory_utilization 0.85
```

## Configuration Reference

### Project Selection
- `--projects`: List of projects to enable (space-separated)
  - Available: `maze`, `driving`, `bloodcell`, `racing`, `general`
  - Example: `--projects maze driving bloodcell`

### Model Configuration
- `--model`: Model name or path (default: `Qwen/QwQ-32B`)
- `--max_model_len`: Maximum context length (default: `4096`)
- `--tensor_parallel_size`: Number of GPUs for tensor parallelism (default: `1`)
- `--gpu_memory_utilization`: GPU memory utilization 0.0-1.0 (default: `0.90`)
- `--quantization`: Quantization method (`awq`, `gptq`, `None`)

### Generation Parameters
- `--temperature`: Sampling temperature (default: `0.6`)
- `--top_p`: Top-p sampling (default: `0.9`)
- `--max_tokens`: Maximum tokens to generate (default: `512`)

### Session Management
- `--max_history_tokens`: Max tokens in conversation history (default: `3000`)
- `--max_concurrent_sessions`: Max concurrent sessions (default: `100`)

### MQTT Configuration
- `--mqtt_broker`: MQTT broker address (default: `47.89.252.2`)
- `--mqtt_port`: MQTT broker port (default: `1883`)
- `--mqtt_username`: MQTT username (optional)
- `--mqtt_password`: MQTT password (optional)

### Performance
- `--num_workers`: Number of worker threads (default: `4`)

## MQTT Message Format

### Sending Messages (User Input)

**Topic**: `{project_name}/user_input`

**Payload** (JSON):
```json
{
  "sessionId": "user123",
  "message": "What should I do next?",
  "temperature": 0.7,
  "topP": 0.9,
  "maxTokens": 256
}
```

**Minimal Payload** (Plain text):
```
What should I do next?
```

### Receiving Responses

**Topic**: `{project_name}/assistant_response/{sessionId}`

**Payload** (Plain text):
```
Based on your position, I recommend taking the left path...
```

## Project-Specific System Prompts

### Maze
Provides strategic hints and pathfinding advice for maze navigation.
- Topics: `maze/user_input`, `maze/assistant_response`
- Format: JSON responses with "hint" and "suggestion"

### Driving
Educational physics game focused on forces and motion. The agent learns from player explanations.
- Topics: `driving/user_input`, `driving/assistant_response`
- Format: Conversational with state tags `<Cont or EOS><PlayerOp:x><AgentOP:y>`
- Max response: 50 words

### Blood Cell
Educational game about red blood cells. Peer learning agent that asks questions.
- Topics: `bloodcell/user_input`, `bloodcell/assistant_response`
- Style: Junior high school student with Gen-Z slang
- Max response: 20 words

### Racing
Physics-focused racing game assistant. Explains force, mass, and acceleration.
- Topics: `racing/user_input`, `racing/assistant_response`
- Style: Supportive peer learning

### General
General-purpose helpful assistant.
- Topics: `general/user_input`, `general/assistant_response`
- Style: Clear, concise, accurate

## Advanced Usage

### Custom System Prompts

To add a new project with custom system prompt:

1. Edit `SYSTEM_PROMPTS` dictionary in `vLLMDeploy.py`:
```python
SYSTEM_PROMPTS = {
    # ... existing prompts ...
    "myproject": """Your custom system prompt here..."""
}
```

2. Deploy with your project:
```bash
python vLLMDeploy.py --projects myproject
```

### Multi-GPU Deployment

For large models, use tensor parallelism:
```bash
python vLLMDeploy.py \
  --projects general \
  --model Qwen/QwQ-72B \
  --tensor_parallel_size 4 \
  --max_model_len 8192
```

### Memory-Constrained Deployment

For limited VRAM:
```bash
python vLLMDeploy.py \
  --projects general \
  --quantization awq \
  --max_model_len 2048 \
  --gpu_memory_utilization 0.85 \
  --max_history_tokens 1500
```

## Performance Optimization

### Tips for Maximum Throughput

1. **Use CUDA Graphs**: Enabled by default (`enforce_eager=False`)
2. **Adjust Batch Size**: vLLM automatically batches concurrent requests
3. **Tune Worker Threads**: Match `--num_workers` to your CPU core count
4. **GPU Memory**: Increase `--gpu_memory_utilization` if you have headroom
5. **Context Length**: Use smaller `--max_model_len` if you don't need long context

### Monitoring Performance

The script logs statistics every 60 seconds:
```
Stats: Processed=150, Errors=0, AvgLatency=0.342s
```

## Testing

### Test with MQTT Client

Using `mosquitto_pub` to send a test message:
```bash
mosquitto_pub -h 47.89.252.2 -t "general/user_input" \
  -m '{"sessionId":"test123","message":"Hello, how are you?"}'
```

Listen for responses:
```bash
mosquitto_sub -h 47.89.252.2 -t "general/assistant_response/#" -v
```

### Python Test Client

```python
import paho.mqtt.client as mqtt
import json
import time

client = mqtt.Client(callback_api_version=mqtt.CallbackAPIVersion.VERSION2)

def on_message(client, userdata, msg):
    print(f"Response: {msg.payload.decode()}")

client.on_message = on_message
client.connect("47.89.252.2", 1883)
client.subscribe("general/assistant_response/#")
client.loop_start()

# Send message
message = {
    "sessionId": "test123",
    "message": "Explain quantum computing in simple terms"
}
client.publish("general/user_input", json.dumps(message))

time.sleep(10)
client.loop_stop()
```

## Troubleshooting

### Issue: OOM (Out of Memory)

**Solutions**:
1. Reduce `--max_model_len`
2. Reduce `--gpu_memory_utilization`
3. Use quantization: `--quantization awq`
4. Reduce `--max_history_tokens`

### Issue: Slow Response Times

**Solutions**:
1. Increase `--num_workers`
2. Use smaller `--max_tokens`
3. Ensure CUDA graphs are enabled (default)
4. Check GPU utilization with `nvidia-smi`

### Issue: MQTT Connection Fails

**Solutions**:
1. Verify broker address and port
2. Check firewall settings
3. Verify credentials if authentication is enabled
4. Test with `mosquitto_pub`/`mosquitto_sub`

### Issue: Sessions Not Persisting

**Note**: Sessions are in-memory and cleared after `session_timeout` (default 3600s) or on restart. This is by design for stateless operation.

## Production Deployment

### Using systemd (Linux)

Create `/etc/systemd/system/vllm-deploy.service`:
```ini
[Unit]
Description=vLLM Multi-Project MQTT Deployment
After=network.target

[Service]
Type=simple
User=llmuser
WorkingDirectory=/path/to/llama3
ExecStart=/path/to/python vLLMDeploy.py --projects maze driving bloodcell
Restart=on-failure
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
```

Enable and start:
```bash
sudo systemctl enable vllm-deploy
sudo systemctl start vllm-deploy
sudo systemctl status vllm-deploy
```

View logs:
```bash
sudo journalctl -u vllm-deploy -f
```

### Using Docker

Create `Dockerfile`:
```dockerfile
FROM nvidia/cuda:12.1.0-runtime-ubuntu22.04

RUN apt-get update && apt-get install -y python3 python3-pip
RUN pip3 install vllm fire paho-mqtt

COPY vLLMDeploy.py /app/
WORKDIR /app

CMD ["python3", "vLLMDeploy.py", "--projects", "general"]
```

Build and run:
```bash
docker build -t vllm-deploy .
docker run --gpus all -p 1883:1883 vllm-deploy \
  python3 vLLMDeploy.py --projects maze driving bloodcell
```

## License

[Your License Here]

## Contributing

Contributions are welcome! Please:
1. Fork the repository
2. Create a feature branch
3. Make your changes with tests
4. Submit a pull request

## Support

For issues and questions:
- GitHub Issues: [link]
- Email: [email]
- Documentation: [link]

## Acknowledgments

- Built with [vLLM](https://github.com/vllm-project/vllm) - High-performance LLM inference
- Uses [Paho MQTT](https://eclipse.dev/paho/) for messaging
- Inspired by production LLM deployment needs
