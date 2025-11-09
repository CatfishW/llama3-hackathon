# 502 Bad Gateway Fix - Quick Start

## 🚨 Problem
After running for a long time, your web application shows:
```
POST https://lammp.agaii.org/api/chatbot/messages 502 (Bad Gateway)
```

## ⚡ Quick Fix (5 minutes)

### On Windows (Recommended):
```powershell
cd Z:\llama3_20250528\llama3\Hackathon\prompt-portal
.\fix-502-error.ps1
```

### On Server (Direct):
```bash
ssh root@lammp.agaii.org
# Upload fix-502-error.sh, then:
chmod +x fix-502-error.sh
sudo ./fix-502-error.sh
```

## 📚 Documentation Files

| File | Purpose |
|------|---------|
| **QUICK_FIX_502.md** | ⭐ START HERE - Quick reference guide |
| **FIX_502_IMPLEMENTATION_SUMMARY.md** | Complete implementation summary |
| **FIX_502_ERROR_LONG_RUNTIME.md** | Detailed technical documentation |
| **fix-502-error.ps1** | Windows deployment script |
| **fix-502-error.sh** | Linux deployment script |
| **prompt-portal-backend.service** | Systemd service configuration |
| **monitor-backend.sh** | Health monitoring script |

## 🔧 What Gets Fixed

- ✅ Backend crashes → Auto-restart within 10 seconds
- ✅ MQTT connection issues → Automatic reconnection
- ✅ Nginx timeouts → Increased to 120 seconds
- ✅ No monitoring → Health checks every 30 seconds
- ✅ Poor error messages → Clear, actionable errors

## ✅ After Deployment

### Verify Everything Works:
```bash
# Check health
curl https://lammp.agaii.org/api/health

# Expected response:
# {"status":"healthy","mqtt":{"connected":true,...}}
```

### Monitor Logs:
```bash
# On server
sudo journalctl -u prompt-portal-backend -f
```

## 🆘 If Something Goes Wrong

### Quick Checks:
```bash
# 1. Is backend running?
sudo systemctl status prompt-portal-backend

# 2. Is MQTT connected?
curl http://localhost:8000/api/health/mqtt | jq

# 3. Check recent errors
sudo journalctl -u prompt-portal-backend -n 50
```

### Quick Fix:
```bash
# Restart everything
sudo systemctl restart mosquitto
sudo systemctl restart prompt-portal-backend
sudo systemctl restart nginx
```

## 📊 Testing

### Send a test message:
1. Open https://lammp.agaii.org
2. Login and send a chat message
3. Should respond in 10-30 seconds (no 502 error)

## 📖 Need More Help?

1. **Quick issues:** See `QUICK_FIX_502.md`
2. **Technical details:** See `FIX_502_ERROR_LONG_RUNTIME.md`
3. **Implementation:** See `FIX_502_IMPLEMENTATION_SUMMARY.md`

## 🎯 Success Indicators

After deployment you should see:

✅ Backend running: `sudo systemctl status prompt-portal-backend`  
✅ Health check passes: `curl https://lammp.agaii.org/api/health`  
✅ No 502 errors in browser  
✅ Messages work consistently  

---

**Next Steps:**
1. Run `.\fix-502-error.ps1` (Windows) or `./fix-502-error.sh` (Linux)
2. Wait 3-5 minutes for deployment
3. Test by sending a message
4. Monitor for 24 hours

**Questions?** Check `QUICK_FIX_502.md` for troubleshooting.
