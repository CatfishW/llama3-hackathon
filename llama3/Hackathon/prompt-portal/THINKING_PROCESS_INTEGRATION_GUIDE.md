# Quick Integration Guide - Thinking Process Feature

## For LLM Backend Developers

### How to Enable Thinking Process Display

The frontend now automatically detects and displays thinking processes. Your LLM responses just need to include thinking content in one of these formats:

### Format 1: XML Tags (Recommended)
Wrap your thinking in `<thinking>` tags before your response:

```
<thinking>
Let me analyze this problem:
1. First, I need to understand what the user is asking
2. Then I'll break down the key components
3. Finally, I'll formulate a comprehensive response

The user is asking about...
This requires understanding...
</thinking>

Here is my response to your question:

[Your actual response content here]
```

### Format 2: Markdown Headers
Use markdown headers to separate thinking:

```
## 思考过程
让我分析这个问题：
1. 首先，我需要理解用户的问题
2. 然后分解关键组件
3. 最后制定全面的回答

## 回复
以下是对您问题的回答：

[Your actual response content here]
```

Or in English:

```
## Thinking
Let me analyze this problem...

## Response
Here is my answer...
```

## How It Works

1. **No Backend Changes Needed**: The feature works entirely on the frontend
2. **Automatic Detection**: The `extractThinkingProcess()` function detects and extracts thinking
3. **Clean Display**: Thinking is hidden by default, user can expand to see it
4. **Context Available**: Thinking is also shown above input for user context

## Testing Your Integration

### Test Case 1: Basic Thinking
Send a response like:
```
<thinking>
This is a math problem.
I need to solve: 2x + 5 = 13
Let me work through it step by step.
</thinking>

The solution is x = 4.
```

**Expected Result**: 
- Message shows "The solution is x = 4."
- Thinking process appears collapsed above the message
- User can click to expand and see the thinking

### Test Case 2: Long Thinking
```
<thinking>
This is a complex problem that requires multiple steps of analysis.
Step 1: Understand the requirements
- The user wants to optimize database queries
- Performance is critical
- They're using PostgreSQL

Step 2: Analyze current issues
- N+1 query problem
- Missing indexes
- Inefficient joins

Step 3: Generate solutions
- Add proper indexes
- Use batch loading
- Optimize the query structure
</thinking>

Based on my analysis, here are three optimization strategies...
```

**Expected Result**:
- Expanded thinking box shows all analysis
- Scrollable if longer than 300px
- Clean main response visible

### Test Case 3: Multiple Sections
```
<thinking>
First, let me consider the user's request...
They want to learn Python basics.

The key topics should be:
1. Variables
2. Data types
3. Control flow
</thinking>

Here's a Python learning guide:

## Variables
In Python, variables are created by assignment...

## Data Types
Python has several basic data types...
```

**Expected Result**:
- Only content before markdown headers is treated as thinking
- If thinking contains markdown, it's preserved in the display

## API Contract

**No changes to API response format required!**

The feature works with existing message structure:
```typescript
{
  id: 1,
  session_id: 1,
  role: "assistant",
  content: "<thinking>...</thinking>\n\nActual response...",
  created_at: "2025-11-11T10:00:00Z"
}
```

## Advanced: Structured Thinking

For more complex models, you can format thinking with structure:

```
<thinking>
## Analysis
The user's request involves three components:
1. Data structure understanding
2. Algorithm implementation
3. Performance optimization

## Decision Making
I'll focus on clarity and correctness first, then optimization.

## Solution Outline
- Explain data structures
- Show algorithm code
- Discuss time complexity
</thinking>

## Solution

Here's how to approach this:
...
```

## Regex Patterns Used for Detection

The frontend uses these patterns to detect thinking:

```javascript
// Pattern 1: XML tags
<thinking>([\s\S]*?)<\/thinking>

// Pattern 2: Markdown headers
^#{1,3}\s*(?:Thinking|思考过程)[\s\S]*?(?=^#{1,3}|$)
```

## Best Practices

1. **Keep Thinking Concise**: While there's no limit, thinking should be focused
2. **Use Clear Structure**: Number steps, use bullets, be logical
3. **Separate Clearly**: Always end thinking tags before response begins
4. **Language Consistency**: Match language of thinking and response
5. **Technical Clarity**: Use monospace-friendly formatting

## Example: Full Integration

Here's a complete example of a well-formatted response:

```
<thinking>
The user is asking how to implement a binary search tree in Python.

Key requirements:
1. Implement insertion
2. Implement search
3. Handle balance

I'll provide:
- Clear class structure
- Step-by-step code with comments
- Example usage
- Time complexity analysis
</thinking>

# Binary Search Tree Implementation

Here's a complete BST implementation in Python:

```python
class Node:
    def __init__(self, value):
        self.value = value
        self.left = None
        self.right = None

class BST:
    def __init__(self):
        self.root = None
    
    def insert(self, value):
        if self.root is None:
            self.root = Node(value)
        else:
            self._insert_recursive(self.root, value)
    
    def _insert_recursive(self, node, value):
        if value < node.value:
            if node.left is None:
                node.left = Node(value)
            else:
                self._insert_recursive(node.left, value)
        else:
            if node.right is None:
                node.right = Node(value)
            else:
                self._insert_recursive(node.right, value)
```

**Time Complexity**: O(log n) average, O(n) worst case
```

## Troubleshooting

### Issue: Thinking not showing up
**Solution**: Ensure thinking is wrapped in `<thinking>` tags with correct syntax
```
❌ Wrong: <thinking>... Response...
✅ Right: <thinking>...</thinking>\n\nResponse...
```

### Issue: Thinking and response mixed
**Solution**: Make sure to close `</thinking>` tag before response starts
```
❌ Wrong:
<thinking>
Content
Response in here too
</thinking>

✅ Right:
<thinking>
Content
</thinking>

Response here
```

### Issue: Response appears in thinking
**Solution**: Verify tag placement - response should be after closing tag
```
❌ Wrong:
<thinking>
Thinking here
Response starts here too
</thinking>

✅ Right:
<thinking>
Thinking here
</thinking>

Response starts here
```

## Performance Considerations

- **Extraction Time**: Negligible (regex on single response)
- **Display Overhead**: Minimal (only renders if thinking exists)
- **Memory**: Efficient (no extra state management needed)
- **Scroll Performance**: Smooth (CSS-based scrolling)

## Monitoring & Analytics

To track thinking process usage:

```javascript
// Optional: Track when thinking is expanded
function onThinkingExpanded(messageId, thinkingLength) {
  console.log(`Message ${messageId}: thinking expanded (${thinkingLength} chars)`)
}
```

## Future Enhancements

Planned features that will integrate with thinking:

1. **Thinking Statistics**
   - Average thinking length per message type
   - Time to generate thinking vs response

2. **Thinking Quality Metrics**
   - User satisfaction with thinking visibility
   - Most useful thinking patterns

3. **Selective Thinking**
   - User can request longer/shorter thinking
   - Toggle thinking requirement per session

4. **Export Capabilities**
   - Export conversation with thinking visible
   - PDF export with thinking in appendix

## Questions & Support

For issues or questions about the thinking process feature:

1. Check `THINKING_PROCESS_FEATURE.md` for detailed documentation
2. See `THINKING_PROCESS_VISUAL_GUIDE.md` for UI examples
3. Review example formats in this guide
4. Check browser console for extraction errors

## Summary

✅ **For Backend Teams**:
- No API changes needed
- Just include thinking in XML tags
- Frontend handles the rest automatically

✅ **For Frontend Users**:
- Thinking appears as collapsible box
- Click to expand and see reasoning
- Context reference above input

✅ **For End Users**:
- See the model's reasoning process
- Understand decision-making
- Better context for follow-up questions
