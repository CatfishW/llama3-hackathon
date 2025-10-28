# TAB Completion Deployment Guide

This guide helps you deploy the TAB completion feature with the Prompt Portal.

## Prerequisites

1. **llama.cpp server** running on port 8080
2. **MQTT broker** accessible at 47.89.252.2:1883
3. **Node.js** and npm available for frontend build
4. **Python** with required dependencies

## Deployment Steps

### 1. Start the llama.cpp Server

```bash
llama-server -m qwen3-30b-a3b-instruct-2507-Q4_K_M.gguft --host 0.0.0.0 --port 8080 -c 28192 -ngl 35 -t 8 --parallel 8
```

### 2. Start the MQTT LLM Service with Completion Support

```bash
python llamacpp_mqtt_deploy.py --projects "maze,prompt_portal,completion_service" --server_url http://localhost:8080 --mqtt_username TangClinic --mqtt_password Tang123
```

### 3. Fix Frontend Build Issues (if needed)

If you encounter build issues with the new MQTT dependencies:

**For Linux/Mac:**
```bash
chmod +x fix-frontend-build.sh
./fix-frontend-build.sh
```

**For Windows:**
```cmd
fix-frontend-build.bat
```

**Manual fix:**
```bash
cd Hackathon/prompt-portal/frontend
npm install mqtt@^5.3.4
npm install @types/mqtt@^2.5.5 --save-dev
npm install terser@^5.19.0 --save-dev
npm run build
```

### 4. Test the Completion Service

```bash
python test_completion.py
```

## Troubleshooting

### Frontend Build Issues

**Common issues and solutions:**

1. **"Module not found: mqtt"**
   ```bash
   npm install mqtt@^5.3.4
   ```

2. **"Cannot find module '@types/mqtt'"**
   ```bash
   npm install @types/mqtt@^2.5.5 --save-dev
   ```

3. **"terser not found"**
   ```bash
   npm install terser@^5.19.0 --save-dev
   ```

4. **TypeScript compilation errors**
   ```bash
   npm run build -- --force
   ```

### MQTT Connection Issues

1. **Check MQTT broker connectivity:**
   ```bash
   telnet 47.89.252.2 1883
   ```

2. **Verify credentials:**
   - Username: `TangClinic`
   - Password: `Tang123`

3. **Check firewall settings** for port 1883

### LLM Service Issues

1. **Check llama.cpp server:**
   ```bash
   curl http://localhost:8080/health
   ```

2. **Verify model is loaded:**
   ```bash
   curl http://localhost:8080/v1/models
   ```

3. **Check service logs** for error messages

## Production Deployment

### Environment Variables

Set these environment variables for production:

```bash
export MQTT_BROKER="47.89.252.2"
export MQTT_PORT="1883"
export MQTT_USERNAME="TangClinic"
export MQTT_PASSWORD="Tang123"
export LLM_SERVER_URL="http://localhost:8080"
```

### Nginx Configuration

Ensure your Nginx configuration allows WebSocket connections for MQTT:

```nginx
location / {
    proxy_pass http://localhost:3000;
    proxy_http_version 1.1;
    proxy_set_header Upgrade $http_upgrade;
    proxy_set_header Connection 'upgrade';
    proxy_set_header Host $host;
    proxy_cache_bypass $http_upgrade;
}
```

### SSL/TLS for MQTT

For production, consider using MQTT over SSL:

```bash
python llamacpp_mqtt_deploy.py \
  --projects "maze,prompt_portal,completion_service" \
  --mqtt_broker 47.89.252.2 \
  --mqtt_port 8883 \
  --mqtt_username TangClinic \
  --mqtt_password Tang123
```

## Monitoring

### Health Checks

1. **LLM Service Health:**
   ```bash
   curl http://localhost:8080/health
   ```

2. **MQTT Broker Health:**
   ```bash
   mosquitto_pub -h 47.89.252.2 -p 1883 -u TangClinic -P Tang123 -t test -m "health check"
   ```

3. **Frontend Build Status:**
   ```bash
   cd Hackathon/prompt-portal/frontend && npm run build
   ```

### Logs

Monitor these logs for issues:

- **LLM Service:** Console output from llamacpp_mqtt_deploy.py
- **Frontend:** Browser console for MQTT connection errors
- **MQTT Broker:** Broker logs (if accessible)

## Performance Tuning

### LLM Service

```bash
python llamacpp_mqtt_deploy.py \
  --projects "maze,prompt_portal,completion_service" \
  --num_workers 12 \
  --temperature 0.3 \
  --max_tokens 50 \
  --server_timeout 30
```

### Frontend

Optimize completion requests:

```typescript
// In CompletionProvider
<CompletionProvider
  broker="47.89.252.2"
  port={1883}
  username="TangClinic"
  password="Tang123"
  timeout={5000} // 5 second timeout
>
  <App />
</CompletionProvider>
```

## Security Considerations

1. **MQTT Authentication:** Always use username/password
2. **Rate Limiting:** Built-in rate limiting (30 req/min per client)
3. **Input Validation:** All inputs are validated
4. **No Sensitive Data:** Completion requests don't contain sensitive information

## Rollback Plan

If issues occur, you can disable TAB completion:

1. **Remove CompletionProvider** from App.tsx
2. **Replace TabCompletionInput** with regular input elements
3. **Stop completion_service** project from llamacpp_mqtt_deploy.py

## Support

For issues with TAB completion:

1. Check the browser console for MQTT connection errors
2. Verify the completion service is running: `python test_completion.py`
3. Check llama.cpp server status
4. Review MQTT broker connectivity

## Success Indicators

✅ **TAB completion is working when:**
- Pressing TAB in input fields shows suggestions
- MQTT connection is established (check browser console)
- Completion service responds to test requests
- No TypeScript compilation errors
- Frontend builds successfully
