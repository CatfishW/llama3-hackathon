# Multi-Model Support - Quick Reference

## 🚀 Quick Start

### For Users
1. Go to **Settings** page
2. Find **"AI Model Selection"** section
3. Click on any model card to select it
4. Your selection is automatically saved!

### For Developers
```python
# Get user's model and create client
from backend.app.services.llm_client import get_llm_client_for_user

llm_client = get_llm_client_for_user(user.selected_model)
response = llm_client.generate(messages=[...])
```

## 📋 Available Models

| Model | Provider | Features | Use Case |
|-------|----------|----------|----------|
| **TangLLM** | Local (Qwen-VL-32B) | Vision, Functions, 32K tokens | Vision tasks, Local hosting |
| **MiniMax M2** | OpenRouter | Free tier, Fast, Functions | General purpose, Free |
| **Qwen3 Coder** | OpenRouter | Code gen, Free, Fast | Code tasks, Development |
| **Kat Coder Pro** | OpenRouter | Advanced coding, Free | Complex coding, Pro tasks |

## 🔧 API Endpoints

```bash
# List available models
GET /api/models/available

# Get user's selected model
GET /api/models/selected

# Select a model
PUT /api/models/select
Body: {"model_name": "Model Name"}
```

## 💻 Frontend Usage

```typescript
import { modelsAPI } from './api'

// Get available models
const models = await modelsAPI.getAvailable()

// Get selected model
const selected = await modelsAPI.getSelected()

// Select a model
await modelsAPI.selectModel('TangLLM')
```

## 🎨 UI Location

**Settings Page → AI Model Selection**
- Visual model cards with features
- Click to select
- Checkmark shows selected model
- Feature badges display capabilities

## 🔒 Security

- ✅ API keys never exposed to frontend
- ✅ User authentication required
- ✅ Per-user model preferences
- ✅ Secure database storage

## 📊 Database

```sql
-- User model preference
users.selected_model VARCHAR(255) DEFAULT 'TangLLM'
```

## 🔄 Architecture Flow

```
User Selects Model (Frontend)
    ↓
PUT /api/models/select
    ↓
Update users.selected_model (Database)
    ↓
User Makes Chat Request
    ↓
Backend reads users.selected_model
    ↓
Creates LLM Client with model's API endpoint & key
    ↓
Sends request to selected model's API
    ↓
Returns response to user
```

## 🎯 Key Files

### Backend
- `backend/app/models_config.py` - Model configuration manager
- `backend/app/routers/models.py` - Models API endpoints
- `backend/app/models.json` - Model configurations
- `backend/app/services/llm_client.py` - Dynamic client creation

### Frontend
- `frontend/src/pages/Settings.tsx` - Model selection UI
- `frontend/src/api.ts` - Models API client

## ⚙️ Adding New Models

Edit `backend/app/models.json`:

```json
{
  "name": "Your Model",
  "provider": "openai",
  "model": "model-identifier",
  "apiBase": "https://api.provider.com/v1",
  "apiKey": "your-api-key",
  "description": "Model description",
  "features": ["Feature 1", "Feature 2"],
  "maxTokens": 8192,
  "supportsFunctions": true,
  "supportsVision": false
}
```

Then restart the backend!

## 🐛 Common Issues

### Model not appearing in UI
- Check `models.json` syntax
- Restart backend
- Check browser console for errors

### Selection not saving
- Verify database migration ran
- Check backend logs
- Ensure user is authenticated

### API errors
- Verify API keys in `models.json`
- Test model endpoint availability
- Check rate limits

## 📱 Mobile Support

✅ Fully responsive design
- Touch-friendly model cards
- Adaptive grid layout
- Mobile-optimized spacing
- Smooth animations

## 🎉 Features at a Glance

✅ **4 Pre-configured Models**
✅ **Beautiful Interactive UI**
✅ **Real-time Model Switching**
✅ **Per-user Preferences**
✅ **Vision Support Detection**
✅ **Feature Badges**
✅ **Mobile Responsive**
✅ **Secure API Key Management**
✅ **Easy Model Addition**
✅ **Automatic Client Configuration**

## 📖 Full Documentation

See `MULTI_MODEL_IMPLEMENTATION_GUIDE.md` for complete details!
