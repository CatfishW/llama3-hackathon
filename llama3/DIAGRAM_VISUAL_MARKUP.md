# Diagram Markup Guide - Specific Visual Changes

## Your Current Diagram Elements

Looking at your SPARC Environment LAM Pipeline diagram, here's exactly what to add/modify:

---

## 🎯 Specific Changes by Element

### ELEMENT 1: The LLM Circle

**CURRENT**: Large empty circle labeled "Llama3/Gemma"

**ENHANCEMENT**: Show internal stages

```
Change From:
╭─────────────────────╮
│                     │
│    Llama3/Gemma     │
│    (LLM)            │
│                     │
╰─────────────────────╯

Change To:
╭─────────────────────╮
│  LLM (Llama3/Gemma) │
├─────────────────────┤
│                     │
│  [1] UNDERSTAND     │◄─── Step 1
│  Parse Intent       │
│  ↓                  │
│  [2] REASON         │◄─── Step 2
│  Analyze Context    │
│  ↓                  │
│  [3] GENERATE       │◄─── Step 3
│  Choose Functions   │
│                     │
╰─────────────────────╯
```

**Visual Style**: 
- Add horizontal lines to separate stages
- Use numbers [1] [2] [3] with boxes
- Add small down arrows between stages
- Keep the circle but make it taller

---

### ELEMENT 2: Pre-defined Functions Box

**CURRENT**: 
```
ScanEnvironment (yellow)
ProvideInformation (cyan)
FollowPlayer (red)
[More functions] (green)
```

**ENHANCEMENT**: Add categories and descriptions

```
PRE-DEFINED FUNCTIONS
┌────────────────────────────────────┐
│ 📊 INFORMATION (Blue Background)   │
│ • ScanEnvironment()                │
│   └─ Returns: objects, threats     │
│ • ProvideInformation()             │
│   └─ Returns: description, teaching│
│                                    │
│ ⚔️ ACTION (Red Background)         │
│ • FollowPlayer()                   │
│   └─ Updates: position             │
│ • AttackThreat()                   │
│   └─ Params: target_id             │
│                                    │
│ ⚙️ STATE (Green Background)        │
│ • GenerateResponse()               │
│   └─ Returns: text                 │
│ • UpdateObjective()                │
│   └─ Params: goal                  │
└────────────────────────────────────┘
```

**Visual Style**:
- Use emoji icons (📊 ⚔️ ⚙️)
- Add colored background bars/sections
- Include function signature format
- Show what each returns/takes as params
- Add small icons next to function names

---

### ELEMENT 3: Add Feedback Arrow (NEW)

**CURRENT**: No feedback from environment to LLM

**ENHANCEMENT**: Add dotted/dashed arrow

```
Add between Environment and LLM:

Environment
    ▲
    │
    │ ··· ··· ··· ··· (DOTTED LINE - NEW)
    │
    └─→ LLM

Label the arrow: "Feedback Loop"
                 "Context Update"
                 
Style: Dotted/dashed line (different from solid)
       Different arrow style (open/empty triangle)
       Possibly lighter color or gray
```

---

### ELEMENT 4: Expand Execution Pipeline

**CURRENT**:
```
JSON File → Deserialize → Function Selector → Execute
```

**ENHANCEMENT**: Show stages in detail

```
┌─────────────────────────────────────────────┐
│ EXECUTION PIPELINE                          │
├─────────────────────────────────────────────┤
│                                             │
│  JSON Input (Function Calls)               │
│  {function, parameters}                     │
│      │                                      │
│      ▼                                      │
│  ✓ DESERIALIZE                             │
│    Parse JSON format                        │
│      │                                      │
│      ▼                                      │
│  ✓ VALIDATE                                │
│    Check parameters & syntax                │
│      │                                      │
│      ▼                                      │
│  ✓ AUTHORIZE                               │
│    Check permissions                        │
│      │                                      │
│      ▼                                      │
│  ⚙️ EXECUTE                                 │
│    Run function                             │
│      │                                      │
│      ▼                                      │
│  ✓ SUCCESS? ──YES──→ Return Results        │
│      │                                      │
│      NO                                     │
│      ▼                                      │
│  🔄 ERROR HANDLER                          │
│    Retry/Recover                            │
│                                             │
└─────────────────────────────────────────────┘
```

**Visual Style**:
- Use checkmarks (✓) for validation steps
- Use vertical flow (top to bottom)
- Add decision diamond for SUCCESS? question
- Use icons (⚙️ 🔄) for action steps
- Add indentation for clarity
- Make it look like a flowchart

---

### ELEMENT 5: Add Metrics Box (NEW)

**LOCATION**: Bottom-right corner

**ENHANCEMENT**: Add performance display

```
┌──────────────────────────┐
│  SYSTEM METRICS          │
├──────────────────────────┤
│ 🕐 Latency: ~1200ms      │
│ ✅ Success Rate: 98%     │
│ 🎯 Accuracy: 99%        │
│ 👥 Active NPCs: 5/100    │
│ ⭐ Satisfaction: 4.8/5   │
└──────────────────────────┘
```

**Visual Style**:
- Use emoji indicators
- Show as small box in corner
- Light background color
- Use real numbers from your system
- Add progress bars (optional)

---

### ELEMENT 6: Annotate All Arrows (NEW)

**CURRENT**: Most arrows have no labels

**ENHANCEMENT**: Add meaningful labels

```
Arrow from User Prompt to NPC:
Label: "User Intent"

Arrow from System Prompt to LLM:
Label: "Strategy Context"

Arrow from User Prompt (also goes around) to Pre-functions:
Label: "Provide Context"

Arrow from LLM to JSON:
Label: "Function Calls (JSON)"

Arrow from JSON to Deserialize:
Label: "Parse & Validate"

Arrow from Deserialize to Function Selector:
Label: "Match Functions"

Arrow from Function Selector to Execute:
Label: "Dispatch"

Arrow from Execute back to Environment:
Label: "Update State"

Arrow (DOTTED) from Environment back to LLM:
Label: "Feedback Loop"
```

**Visual Style**:
- Place labels above/beside arrows
- Use small text (10-12pt)
- Keep labels short (1-3 words)
- Use consistent font and color
- For important arrows, use darker color

---

### ELEMENT 7: Enhance System Prompt Box

**CURRENT**: Just an icon labeled "System Prompt"

**ENHANCEMENT**: Show sample content

```
SYSTEM PROMPT
┌─────────────────────────────────┐
│ "You are Cap, an NPC helping    │
│  players learn biology through  │
│  interactive game exploration.  │
│                                 │
│ AVAILABLE ACTIONS:              │
│ • Scan environment              │
│ • Provide information           │
│ • Follow player                 │
│ • Attack threats                │
│                                 │
│ RULES:                          │
│ • Be helpful but not controlling│
│ • Teach through questioning     │
│ • Reward curiosity"             │
└─────────────────────────────────┘
```

**Visual Style**:
- Show it as a text box with quote marks
- Use monospace font for code-like appearance
- Add section headers (AVAILABLE ACTIONS, RULES)
- Make it look like actual system prompt text
- Use slightly different background color

---

### ELEMENT 8: Color Code by Function Type (NEW)

**CURRENT**: Each function has a different color

**ENHANCEMENT**: Organize by category and add legend

```
Add Legend Box (top-right):
┌─ Function Categories ──┐
│ 📊 Information (Blue)   │
│ ⚔️  Action (Red)        │
│ ⚙️  State (Green)       │
│ 🎓 Learning (Orange)    │
└────────────────────────┘

Apply to functions:
BLUE background   → ScanEnvironment, ProvideInformation
RED background    → FollowPlayer, AttackThreat
GREEN background  → SaveState, UpdateObjective, GenerateResponse
```

**Visual Style**:
- Add legend in corner
- Use semi-transparent backgrounds for function boxes
- Keep text readable over colored backgrounds
- Use consistent colors throughout diagram
- Match legend colors to function box colors

---

### ELEMENT 9: Add Decision Logic (NEW)

**LOCATION**: Inside or near LLM box

**ENHANCEMENT**: Show how LLM decides

```
DECISION LOGIC EXAMPLE
┌──────────────────────────────────┐
│ User Query: "Investigate area"   │
│     ↓                            │
│ Match to category?               │
│ ├─ INVESTIGATION ✓              │
│ │  Use: ScanEnvironment()       │
│ │        ProvideInformation()   │
│ ├─ In danger?  ✓                │
│ │  Use: FollowPlayer(defend)    │
│ └─ Generate: Natural response   │
│                                  │
│ RESULT: 3 functions selected     │
└──────────────────────────────────┘
```

**Visual Style**:
- Use checkmarks (✓) for matches
- Show hierarchy with indentation
- Use arrows to show flow
- Make it look like decision tree
- Add to diagram or as separate callout

---

### ELEMENT 10: Show Error Paths (NEW)

**LOCATION**: In execution pipeline

**ENHANCEMENT**: Show what happens on failure

```
EXECUTION WITH ERROR HANDLING
              Execute
                 │
                 ├─ Success ──→ Update Environment
                 │
                 └─ Error ──→ Error Handler
                              ├─ Log Error
                              ├─ Retry?  YES ──→ Execute Again
                              │           NO
                              └─ Fallback Function
                              
Visual: Use different arrow styles
- Solid green for success path
- Dashed red for error path
```

**Visual Style**:
- Use different arrow colors/styles
- Add decision points (diamonds) for conditionals
- Show error handling flow
- Make error paths visually distinct

---

## 🎨 Color Scheme Recommendation

```
USE THESE COLORS:
Primary: #2E86AB (Professional Blue) - Main LLM
Secondary: #A23B72 (Purple) - System Prompt
Success: #06A77D (Green) - Successful execution
Warning: #F18F01 (Orange) - Learning/updates
Error: #C1121F (Red) - Action/threats
Info: #4A90E2 (Light Blue) - Information functions
State: #7CB342 (Lime) - State functions
Accent: #FFD700 (Gold) - Important elements
Text: #333333 (Dark Gray) - Text on light backgrounds
```

---

## 📐 Sizing Suggestions

```
LLM Box:        300px × 250px (tallest element)
Function Box:   350px × 300px (wide, organized)
System Prompt:  300px × 200px
Metrics Box:    200px × 150px
JSON Box:       200px × 100px
Function Selector: 200px × 100px

Arrows: 2-3px stroke width (3px for important ones)
Text:   12pt for labels, 10pt for details
```

---

## 🖱️ Interactive Features (if digital)

```
HOVER STATES:
- Hover over LLM → Show "3 stages" tooltip
- Hover over function → Show parameters & return values
- Hover over arrow → Highlight the connected elements

CLICK STATES:
- Click on function category → Expand to show details
- Click on LLM → Show example reasoning process
- Click on arrow → Show example data flowing
```

---

## 📊 Step-by-Step Implementation

**Step 1** (5 min): Add arrow labels
**Step 2** (10 min): Expand LLM box with 3 stages
**Step 3** (10 min): Reorganize functions with categories
**Step 4** (5 min): Add color coding legend
**Step 5** (5 min): Add feedback dotted arrow
**Step 6** (10 min): Add execution pipeline detail
**Step 7** (5 min): Add metrics box
**Step 8** (5 min): Final polish and alignment

**Total time**: ~55 minutes for full enhancement

---

## ✅ Enhancement Checklist

- [ ] Add numbered stages inside LLM (1-3)
- [ ] Label all arrows with meaningful text
- [ ] Add function category colors and legend
- [ ] Add dotted feedback arrow from Environment → LLM
- [ ] Expand execution pipeline with validation steps
- [ ] Add metrics box in corner
- [ ] Add system prompt content box
- [ ] Show error handling path
- [ ] Add decision logic callout
- [ ] Verify all text is readable
- [ ] Ensure color consistency
- [ ] Add any missing explanatory text

---

## 🎯 Final Result

Your enhanced diagram will clearly show:

1. ✅ **Input Layer** - Where user input enters
2. ✅ **Processing Layer** - How LLM thinks (3 stages)
3. ✅ **Function Layer** - What actions are available (organized & colored)
4. ✅ **Execution Layer** - How functions are validated & run
5. ✅ **Output Layer** - Results back to environment
6. ✅ **Feedback Layer** - How system learns continuously
7. ✅ **Metrics Layer** - Performance indicators
8. ✅ **Error Layer** - Failure handling

**Result**: Professional, detailed, presentation-ready diagram! 🎉

---

## 💡 Pro Tips

1. **Layering**: Use transparency to show depth
2. **Alignment**: Align elements in grid for neat appearance
3. **White Space**: Leave breathing room between elements
4. **Hierarchy**: Make important elements larger
5. **Consistency**: Use same line styles, fonts, colors
6. **Clarity**: Ensure all text is readable at presentation size
7. **Flow**: Make data flow obvious with arrows and labels
8. **Balance**: Distribute elements evenly across diagram

---

**Your enhanced diagram will transform from a good overview to a comprehensive technical reference!**

