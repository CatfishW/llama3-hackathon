# Model Management UI Guide

## 🎨 User Interface Overview

### Main Settings Page - Model Section

```
┌─────────────────────────────────────────────────────────────────┐
│  ⚡ AI Model Selection                                          │
│  Choose the AI model that powers your conversations             │
│                                                                  │
│  [➕ Add Custom Model]                                          │
│                                                                  │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐            │
│  │ TangLLM  ✓  │  │ MiniMax M2  │  │ Qwen3 Coder │            │
│  │━━━━━━━━━━━━ │  │             │  │             │            │
│  │ 🤖 Local    │  │ 🤖 OpenRouter│ │ 🤖 OpenRouter│           │
│  │             │  │             │  │             │            │
│  │ Qwen2-VL    │  │ minimax-01  │  │ qwen-2.5-   │            │
│  │ 32B         │  │             │  │ coder-32b   │            │
│  │             │  │             │  │             │            │
│  │ ✨ Features │  │ ✨ Features  │  │ ✨ Features │            │
│  │ • Vision    │  │ • Fast      │  │ • Code gen  │            │
│  │ • Fast      │  │ • Reasoning │  │ • Fast      │            │
│  │ • High qual │  │             │  │             │            │
│  │             │  │             │  │             │            │
│  │ [✏️ Edit]   │  │ [✏️ Edit]    │  │ [✏️ Edit]   │            │
│  │ [🗑️ Delete] │  │ [🗑️ Delete]  │  │ [🗑️ Delete] │            │
│  └─────────────┘  └─────────────┘  └─────────────┘            │
└─────────────────────────────────────────────────────────────────┘
```

### Model Card States

#### Default State
```
┌─────────────────────┐
│ Model Name          │
│ ─────────────────── │
│ 🤖 Provider         │
│                     │
│ model-id-here       │
│                     │
│ ✨ Features         │
│ • Feature 1         │
│ • Feature 2         │
│                     │
│ [hidden buttons]    │
└─────────────────────┘
```

#### Hover State
```
┌─────────────────────┐
│ Model Name          │  ← Slightly lifted (shadow)
│ ─────────────────── │
│ 🤖 Provider         │
│                     │
│ model-id-here       │
│                     │
│ ✨ Features         │
│ • Feature 1         │
│ • Feature 2         │
│                     │
│ [✏️ Edit] [🗑️ Delete]│  ← Buttons visible
└─────────────────────┘
```

#### Selected State
```
┌═════════════════════┐  ← Green border (2px solid)
│ Model Name       ✓  │  ← Green checkmark
│ ━━━━━━━━━━━━━━━━━━━ │  ← Green underline
│ 🤖 Provider         │
│                     │
│ model-id-here       │
│                     │  ← Green gradient background
│ ✨ Features         │
│ • Feature 1         │
│ • Feature 2         │
│                     │
│ [✏️ Edit] [🗑️ Delete]│
└═════════════════════┘
```

### Add/Edit Model Dialog

```
╔═══════════════════════════════════════════════════════════╗
║                   🆕 Add Custom Model                     ║
║ (or ✏️ Edit Model)                                        ║
║                                                           ║
║  Model Name *                                             ║
║  ┌──────────────────────────────────────────────────┐    ║
║  │ e.g., GPT-4 Turbo                                │    ║
║  └──────────────────────────────────────────────────┘    ║
║  ℹ️  Model name cannot be changed (when editing)         ║
║                                                           ║
║  Provider *                                               ║
║  ┌──────────────────────────────────────────────────┐    ║
║  │ e.g., OpenAI, OpenRouter                         │    ║
║  └──────────────────────────────────────────────────┘    ║
║                                                           ║
║  Model ID *                                               ║
║  ┌──────────────────────────────────────────────────┐    ║
║  │ e.g., gpt-4-turbo-preview                        │    ║
║  └──────────────────────────────────────────────────┘    ║
║                                                           ║
║  API Base URL *                                           ║
║  ┌──────────────────────────────────────────────────┐    ║
║  │ e.g., https://api.openai.com/v1                  │    ║
║  └──────────────────────────────────────────────────┘    ║
║                                                           ║
║  API Key *                                                ║
║  ┌──────────────────────────────────────────────────┐    ║
║  │ ••••••••••••••••                                 │    ║
║  └──────────────────────────────────────────────────┘    ║
║                                                           ║
║  Description                                              ║
║  ┌──────────────────────────────────────────────────┐    ║
║  │ Brief description of this model                  │    ║
║  │                                                   │    ║
║  │                                                   │    ║
║  └──────────────────────────────────────────────────┘    ║
║                                                           ║
║  Features (comma-separated)                               ║
║  ┌──────────────────────────────────────────────────┐    ║
║  │ Fast responses, Code generation                  │    ║
║  └──────────────────────────────────────────────────┘    ║
║                                                           ║
║  Max Tokens        Capabilities                           ║
║  ┌──────────┐      ☑ Functions  ☑ Vision                ║
║  │ 4096     │                                            ║
║  └──────────┘                                            ║
║                                                           ║
║                           [Cancel] [💾 Add/Update Model] ║
╚═══════════════════════════════════════════════════════════╝
```

## 🎯 Interactive Elements

### Buttons

**Primary Button (Add/Save)**
```
Normal:  ╔════════════════════╗
         ║ 💾 Save Model     ║  Blue gradient
         ╚════════════════════╝

Hover:   ╔════════════════════╗
         ║ 💾 Save Model     ║  Brighter, lifted
         ╚════════════════════╝

Disabled:╔════════════════════╗
         ║ 💾 Save Model     ║  50% opacity, no pointer
         ╚════════════════════╝
```

**Edit Button**
```
Normal:  [✏️ Edit]   Green transparent bg
Hover:   [✏️ Edit]   Green solid bg, lifted
```

**Delete Button**
```
Normal:  [🗑️ Delete]  Red transparent bg
Hover:   [🗑️ Delete]  Red solid bg, lifted
```

### Model Card Interactions

1. **Click anywhere on card** → Select model
2. **Hover over card** → Show edit/delete buttons
3. **Click edit button** → Open dialog with model data
4. **Click delete button** → Delete model (with confirmation)

## 🎨 Color Scheme

### Model Cards
- **Background (default)**: `rgba(255, 255, 255, 0.05)` - Subtle transparent white
- **Background (selected)**: `linear-gradient(135deg, rgba(78, 205, 196, 0.2), rgba(68, 160, 141, 0.2))` - Green gradient
- **Border (default)**: `rgba(255, 255, 255, 0.1)` - Light transparent
- **Border (selected)**: `#4ecdc4` - Bright teal/green
- **Border (hover)**: `rgba(255, 255, 255, 0.2)` - Brighter

### Buttons
- **Primary**: `linear-gradient(135deg, #667eea 0%, #764ba2 100%)` - Blue to purple
- **Edit**: `rgba(78, 205, 196, 0.1)` base, `#4ecdc4` accent - Teal
- **Delete**: `rgba(255, 107, 107, 0.1)` base, `#ff6b6b` accent - Red

### Text
- **Headers**: White, `1.5rem`
- **Body**: White, `0.95rem`
- **Muted**: `rgba(255, 255, 255, 0.7)`
- **Very muted**: `rgba(255, 255, 255, 0.6)`

## 📱 Responsive Behavior

### Desktop (> 720px)
```
┌──────────────────────────────────────────────────────┐
│  [Model 1]  [Model 2]  [Model 3]  [Model 4]         │
│  [Model 5]  [Model 6]                                │
└──────────────────────────────────────────────────────┘
```
- Grid: `repeat(auto-fit, minmax(300px, 1fr))`
- 3-4 cards per row depending on width

### Mobile (≤ 720px)
```
┌──────────────┐
│  [Model 1]   │
│  [Model 2]   │
│  [Model 3]   │
│  [Model 4]   │
└──────────────┘
```
- Grid: `1fr` (single column)
- Full width cards

### Dialog (Mobile)
- Dialog uses 90vh max-height
- Scrollable content area
- Full width with padding

## ⚡ Animations

### Transitions (all 0.3s ease)
- Background color changes
- Border color changes
- Transform (translateY for lift effect)
- Box shadow changes
- Button hover states

### Loading States
```
⏳ Loading models...
   🔄 (spinning icon)
```

### Selection Feedback
```
Before: [Click]
        ↓
After:  ✓ Model Selected! (green checkmark appears)
        Green border animates in
        Background gradient fades in
```

## 🔧 Form Validation

### Required Fields (marked with *)
- Model Name
- Provider
- Model ID
- API Base URL
- API Key

### Validation States
```
Empty:    [         ]  Normal border
Filled:   [████████]  Normal border
Invalid:  [××××××××]  Red border (if pattern checking added)
Valid:    [✓✓✓✓✓✓✓✓]  Green border (if pattern checking added)
```

### Save Button States
```
All required filled:     [💾 Save Model] → Enabled (full opacity)
Missing required:        [💾 Save Model] → Disabled (50% opacity)
```

## 🌟 User Experience Flow

### Adding a Custom Model
1. User clicks "Add Custom Model" button
2. Dialog slides in with backdrop blur
3. User fills form (required fields marked with *)
4. Save button becomes enabled when all required fields filled
5. Click "Save" → API call → Success toast → Dialog closes → Model appears in grid

### Editing a Model
1. User hovers over model card → Edit/Delete buttons appear
2. Click "Edit" button
3. Dialog opens with all fields pre-filled (except API key shows as password)
4. User modifies fields (model name is disabled)
5. Click "Update" → API call → Success toast → Dialog closes → Card updates

### Deleting a Model
1. User hovers over model card → Edit/Delete buttons appear
2. Click "Delete" button
3. Confirmation prompt (optional, can be added)
4. API call → Success toast → Model removed from grid

### Selecting a Model
1. User clicks anywhere on model card
2. Previous selection loses highlight
3. New selection gets green border + checkmark
4. API call saves preference
5. All future chats use this model

## 🎭 Visual Feedback

### Success Messages
```
┌─────────────────────────────────┐
│ ✅ Model saved successfully!    │
└─────────────────────────────────┘
```

### Error Messages
```
┌─────────────────────────────────┐
│ ❌ Failed to save model         │
└─────────────────────────────────┘
```

### Loading States
- Spinner icons with rotation animation
- "Saving..." / "Loading..." text
- Disabled buttons during operations

---

**Design Philosophy:** Clean, modern, glassmorphism aesthetic with smooth interactions
