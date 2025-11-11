# Multi-Model Selection UI - Visual Guide

## 🎨 Settings Page - AI Model Selection Section

```
╔════════════════════════════════════════════════════════════════╗
║                         SETTINGS                               ║
║                 Manage your account preferences                ║
╚════════════════════════════════════════════════════════════════╝

┌────────────────────────────────────────────────────────────────┐
│  🤖 AI Model Selection                                         │
│  Choose the AI model that powers your conversations            │
├────────────────────────────────────────────────────────────────┤
│                                                                │
│  ┌──────────────────┐  ┌──────────────────┐                  │
│  │   TangLLM     ✓  │  │   MiniMax M2     │                  │
│  │ ──────────────── │  │ ──────────────── │                  │
│  │ 🖥️ openai        │  │ 🖥️ openai        │                  │
│  │                  │  │                  │                  │
│  │ Local Qwen      │  │ MiniMax M2 -     │                  │
│  │ Vision-Language  │  │ Free tier via    │                  │
│  │ Model - 32B      │  │ OpenRouter       │                  │
│  │                  │  │                  │                  │
│  │ 🏷️ Fast Response │  │ 🏷️ Free Tier    │                  │
│  │ 🏷️ Vision Support│  │ 🏷️ Fast Response│                  │
│  │ 🏷️ Function Call │  │ 🏷️ Cloud-based  │                  │
│  └──────────────────┘  └──────────────────┘                  │
│                                                                │
│  ┌──────────────────┐  ┌──────────────────┐                  │
│  │  Qwen3 Coder     │  │ Kat Coder Pro    │                  │
│  │ ──────────────── │  │ ──────────────── │                  │
│  │ 🖥️ openai        │  │ 🖥️ openai        │                  │
│  │                  │  │                  │                  │
│  │ Qwen3 Coder -   │  │ Kat Coder Pro -  │                  │
│  │ Specialized for  │  │ Advanced coding  │                  │
│  │ code generation  │  │ assistant        │                  │
│  │                  │  │                  │                  │
│  │ 🏷️ Code Gen      │  │ 🏷️ Advanced Code│                  │
│  │ 🏷️ Free Tier     │  │ 🏷️ Free Tier    │                  │
│  └──────────────────┘  └──────────────────┘                  │
│                                                                │
└────────────────────────────────────────────────────────────────┘
```

## 💡 UI Features Explained

### Model Card States

#### 🟢 Selected Model (TangLLM shown above)
```
┌──────────────────────────────────────────┐
│                              ┌───┐       │
│   TangLLM                    │ ✓ │       │ ← Checkmark badge
│   ────────────────           └───┘       │
│   🖥️ openai  •  👁️ Vision                │ ← Provider + Vision indicator
│                                          │
│   Local Qwen Vision-Language             │ ← Description
│   Model - 32B parameters with            │
│   vision capabilities                    │
│                                          │
│   🏷️ Fast Response  🏷️ Vision Support   │ ← Feature badges
│   🏷️ Function Calling  🏷️ Local Hosting │
│                                          │
│   [GRADIENT BACKGROUND + GLOW EFFECT]    │ ← Visual highlight
└──────────────────────────────────────────┘
```

#### ⚪ Unselected Model (Hover State)
```
┌──────────────────────────────────────────┐
│   MiniMax M2                             │
│   ────────────────                       │
│   🖥️ openai                               │ ← No checkmark
│                                          │
│   MiniMax M2 - Free tier via             │
│   OpenRouter with strong                 │
│   performance                            │
│                                          │
│   🏷️ Free Tier  🏷️ Fast Response        │
│   🏷️ Function Calling  🏷️ Cloud-based   │
│                                          │
│   [SUBTLE HOVER LIFT ANIMATION]          │ ← Hover effect
└──────────────────────────────────────────┘
```

## 🎨 Color Scheme

### Selected Model
- **Background**: `linear-gradient(135deg, rgba(78, 205, 196, 0.2), rgba(68, 160, 141, 0.2))`
- **Border**: `2px solid #4ecdc4` (Teal)
- **Checkmark**: White on `#4ecdc4` circular background

### Unselected Model
- **Background**: `rgba(255, 255, 255, 0.05)` (Subtle glass effect)
- **Border**: `2px solid rgba(255, 255, 255, 0.1)` (Light gray)
- **Hover Background**: `rgba(255, 255, 255, 0.08)`
- **Hover Border**: `rgba(78, 205, 196, 0.5)` (Teal hint)

### Feature Badges
- **Background**: `rgba(78, 205, 196, 0.2)` (Teal translucent)
- **Text**: `#4ecdc4` (Teal)
- **Font**: Small, bold, rounded corners

## 📱 Mobile View

```
┌────────────────────────┐
│  🤖 AI Model Selection │
│  Choose your AI model  │
├────────────────────────┤
│                        │
│  ┌──────────────────┐ │
│  │   TangLLM     ✓  │ │
│  │ ──────────────── │ │
│  │ 🖥️ openai  •  👁️  │ │
│  │                  │ │
│  │ Local Qwen VL    │ │
│  │ Model - 32B      │ │
│  │                  │ │
│  │ 🏷️ Fast 🏷️ Vision│ │
│  └──────────────────┘ │
│                        │
│  ┌──────────────────┐ │
│  │   MiniMax M2     │ │
│  │ ──────────────── │ │
│  │ 🖥️ openai         │ │
│  │                  │ │
│  │ Free tier via    │ │
│  │ OpenRouter       │ │
│  │                  │ │
│  │ 🏷️ Free 🏷️ Fast  │ │
│  └──────────────────┘ │
│                        │
│         (...)          │
│                        │
└────────────────────────┘
```

## 🎭 Interaction Flow

### 1. User Clicks Model Card
```
User Click
    ↓
Card Sends API Request
    ↓
PUT /api/models/select
    {"model_name": "MiniMax M2"}
    ↓
Backend Updates Database
    ↓
Success Response
    ↓
✅ Success message appears:
"Successfully switched to MiniMax M2!"
    ↓
Previous selection loses checkmark
New selection gets checkmark + glow
    ↓
Auto-dismiss success message (3s)
```

### 2. Visual Feedback States
```
Normal State → Hover → Click → Loading → Success
   ⚪         →   🟡   →   ⏳   →    ⏰    →   ✅
```

## 🖼️ Key Visual Elements

### Icons Used
- 🤖 **fa-robot** - Section header
- 🖥️ **fa-server** - Provider indicator  
- 👁️ **fa-eye** - Vision support indicator
- ✓ **fa-check** - Selected checkmark
- 🔄 **fa-spinner** - Loading state

### Animations
1. **Hover Effect**: `translateY(-2px)` - Subtle lift
2. **Select Animation**: Border color transition (0.3s ease)
3. **Checkmark**: Fade in with scale (0.3s ease)
4. **Success Toast**: Slide in from top

## 🎯 Accessibility

- ✅ **Keyboard Navigation**: Tab through cards
- ✅ **Focus Indicators**: Visible focus ring
- ✅ **Screen Reader**: Descriptive ARIA labels
- ✅ **Color Contrast**: WCAG AA compliant
- ✅ **Touch Targets**: 44px minimum (mobile)

## 💻 Developer Preview

### Component Structure
```tsx
<div className="model-selection-section">
  <h3>🤖 AI Model Selection</h3>
  <p>Choose the AI model...</p>
  
  <div className="models-grid">
    {availableModels.map(model => (
      <div 
        className={`model-card ${isSelected ? 'selected' : ''}`}
        onClick={() => selectModel(model.name)}
      >
        {isSelected && <CheckmarkBadge />}
        <ModelHeader name={model.name} provider={model.provider} />
        <ModelDescription text={model.description} />
        <FeatureBadges features={model.features} />
      </div>
    ))}
  </div>
</div>
```

## 🌟 Special Effects

### Glassmorphism
- Backdrop blur: `blur(10px)`
- Semi-transparent background
- Subtle borders
- Layered depth

### Gradient Glow (Selected)
- Two-color gradient
- Animated glow on selection
- Box shadow with model color

### Smooth Transitions
- All properties: `0.3s ease`
- Border, background, transform
- Checkmark fade/scale

## 🎬 Animation Timeline

```
Selection Click (t=0ms)
    ↓
Send API Request (t=0ms)
    ↓
Show loading cursor (t=0ms)
    ↓
API Response (t=100-300ms)
    ↓
Update UI State (t=300ms)
    ↓
Checkmark Fade In (t=300-600ms)
    ↓
Border Color Change (t=300-600ms)
    ↓
Background Gradient (t=300-600ms)
    ↓
Success Toast Show (t=600ms)
    ↓
Success Toast Hide (t=3600ms)
```

---

## 🎨 Design Philosophy

**Clean • Modern • Intuitive • Beautiful**

The model selection UI follows these principles:
1. **Visual Hierarchy** - Selected model stands out
2. **Information Density** - All key info at a glance
3. **Interaction Feedback** - Immediate visual response
4. **Progressive Enhancement** - Works on all devices
5. **Aesthetic Consistency** - Matches app design language

Enjoy your beautiful multi-model interface! 🚀✨
