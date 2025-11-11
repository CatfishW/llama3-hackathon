# Thinking Process Feature - Visual Guide

## UI Layout

### In Message Bubbles
```
┌─────────────────────────────────────────┐
│ ▶ 💭 Thinking Process                   │  ← Collapsible header (click to expand)
└─────────────────────────────────────────┘
┌─────────────────────────────────────────┐
│                                         │
│  The LLM's actual response would be    │  ← Main message bubble
│  displayed here, clean and readable.   │
│  The thinking content is hidden above. │
│                                         │
└─────────────────────────────────────────┘
```

### Expanded Thinking Process
```
┌─────────────────────────────────────────┐
│ ▼ 💭 Thinking Process                   │  ← Click to collapse
├─────────────────────────────────────────┤
│ Let me analyze this problem step by     │
│ step...                                 │
│                                         │
│ 1. First, I need to understand what    │
│    the user is asking                   │
│ 2. Then identify the key concepts       │
│ 3. Finally, formulate a response        │
│                                         │
│ [Scrollable if content exceeds height]  │
└─────────────────────────────────────────┘
```

### Above Input Box
```
Current Chat Area:

┌────────────────────────────────────────────────────────┐
│ Message Area - Previous messages and responses         │
│                                                        │
│ [Assistant Message]                                    │
│                                                        │
└────────────────────────────────────────────────────────┘

┌────────────────────────────────────────────────────────┐
│ ▶ 💭 Thinking Process (Latest assistant thinking)      │  ← NEW: Thinking from last response
├────────────────────────────────────────────────────────┤
│                                                        │
│ Input Textarea:                                        │
│ [Type your message here...                             │
│  Shift+Enter for newline]                             │
│                                                        │
│ [Upload Doc] [Upload Image]                           │
│                                                        │
│                              [Send] [Edit]            │
└────────────────────────────────────────────────────────┘
```

## Color Scheme

### Thinking Process Component
- **Border**: Purple (`rgba(168, 85, 247, 0.3)`)
- **Background (collapsed)**: Light purple (`rgba(168, 85, 247, 0.08)`)
- **Background (expanded)**: Even lighter purple (`rgba(168, 85, 247, 0.04)`)
- **Text**: Purple accent (`rgba(168, 85, 247, 0.9)`)
- **Hover**: Brighter purple (`rgba(196, 181, 253, 0.95)`)

### Example Color Display
```
    Normal State        →        Hover State         →      Expanded State
┌─ Purple Border ─┐     ┌─ Purple Border ─┐     ┌─ Purple Border ─┐
│ ▶ 💭 Thinking... │  → │ ▶ 💭 Thinking... │  → │ ▼ 💭 Thinking... │
│ Light Purple BG │     │ Bright Purple    │     │ Very Light BG   │
└──────────────────┘     └──────────────────┘     │                 │
                                                  │ [Expanded cont] │
                                                  └─────────────────┘
```

## Interaction Flow

```
1. LLM generates response
   ↓
2. Response includes thinking tags: <thinking>...</thinking>
   ↓
3. extractThinkingProcess() runs
   ├─ Extracts thinking content
   └─ Returns clean response
   ↓
4. MessageBubble renders
   ├─ Shows ThinkingProcess (collapsed) if thinking exists
   └─ Shows clean response in bubble
   ↓
5. Input area also displays latest thinking
   (So user sees assistant's reasoning)
   ↓
6. User can click to expand/collapse thinking
   └─ View full reasoning process
   ↓
7. User can craft response based on understanding
   the assistant's reasoning
```

## Responsive Behavior

### Desktop (width > 768px)
- Thinking process: 70% width (matches message bubbles)
- Max height: 300px with scrollbar
- Full padding: 24px
- Font size: 0.8rem

### Mobile (width < 768px)
- Thinking process: 90% width
- Max height: 300px with scrollbar  
- Reduced padding: 12px
- Font size: 0.8rem (same as desktop for readability)
- Stack layout for all elements

## Text Rendering

Thinking content is displayed in monospace font for technical clarity:
```
Font: Consolas, Monaco, "Courier New", monospace
Size: 0.8rem
Line height: 1.6
Color: rgba(226, 232, 240, 0.85) (light gray)
```

Example output:
```
Let me break this down:

Step 1: Parse the input
- Check if string is empty
- Validate format

Step 2: Process data
- Apply transformation
- Store results

Step 3: Return output
```

## Accessibility Features

1. **Clear Visual Hierarchy**
   - Arrow indicator (▶/▼) shows expand/collapse state
   - Header is clickable and button-like

2. **Color Contrast**
   - Purple accent contrasts well with dark background
   - Text is clearly readable

3. **Mobile-Friendly**
   - Touch targets are 40px+ for mobile
   - Responsive text sizing
   - Proper spacing between elements

4. **Keyboard Navigation**
   - Button is focusable
   - Can be activated with Enter/Space

## Example Usage Scenarios

### Scenario 1: Math Problem
```
User asks: "Solve 2x + 5 = 13"

Thinking Process (collapsed):
▶ 💭 Thinking Process

Response:
To solve this equation:
1. Subtract 5 from both sides: 2x = 8
2. Divide by 2: x = 4

---

User expands thinking to see:
▼ 💭 Thinking Process
Okay, I need to solve for x.
This is a linear equation.
Step 1: 2x + 5 = 13
        2x = 13 - 5
        2x = 8
Step 2: x = 8/2
        x = 4
Verification: 2(4) + 5 = 8 + 5 = 13 ✓
```

### Scenario 2: Code Review
```
User asks: "Review this Python code"

Thinking Process (collapsed):
▶ 💭 Thinking Process

Response:
The code looks good overall. Here are a few suggestions:
1. Add type hints
2. Use more descriptive variable names
...

---

User expands thinking to see:
▼ 💭 Thinking Process
Let me analyze this code:
- It's a function that processes data
- The logic seems correct
- But I notice some areas that could be improved:
  * No type hints (PEP 484)
  * Variable names could be clearer
  * Some comments would help
- Overall, this is decent code that could be enhanced
```

### Scenario 3: Creative Writing
```
User asks: "Write a short story opening"

Thinking Process (collapsed):
▶ 💭 Thinking Process

Response:
The old lighthouse stood alone on the rocky peninsula, 
its paint weathered to a soft gray...

---

User expands thinking to see:
▼ 💭 Thinking Process
The user wants a story opening. I should:
1. Create atmosphere
2. Use descriptive language
3. Hook the reader immediately
4. Set the scene

A lighthouse is a good isolated setting...
I'll use vivid imagery of decay and solitude...
```

## Browser DevTools

When inspecting the component in browser DevTools:

```
<ThinkingProcess thinking="content...">
  <div style="...">
    <button style="..." onClick={...}>
      ▶ 💭 Thinking Process
    </button>
    {isExpanded && <div>... thinking content ...</div>}
  </div>
</ThinkingProcess>
```

## Performance Notes

- Thinking extraction runs once per message render
- No external dependencies required
- Efficient regex matching
- Scrollable container prevents layout shifts
- Memory efficient: Only stores extracted thinking

## Known Limitations

1. Only extracts first thinking block if multiple exist
2. Requires specific tag format: `<thinking>...</thinking>`
3. Markdown format detection uses regex (simple patterns only)
4. Max displayed height: 300px (scrollable)

## Future UI Improvements

- [ ] Copy button for thinking content
- [ ] Print-friendly thinking process view
- [ ] Dark/light theme toggle for thinking box
- [ ] Keyboard shortcut (Alt+T) to expand thinking
- [ ] Thinking process statistics (time, tokens used)
- [ ] Export conversation with thinking visible
