# Qwen3 Deep Thinking Mode Control Guide

## Overview

This guide explains how to control deep thinking mode in your Qwen3-30B model when using the `llamacpp_mqtt_deploy.py` script.

## Background

Based on Aliyun's official documentation on Qwen3 deep thinking models:

- **Qwen3 Open-Source Models** (like Qwen3-30B) have **hybrid thinking mode enabled by default**
- They can output reasoning/thinking before the final answer
- You can disable thinking mode using the `/no_think` prompt directive

## Key Parameter: `skip_thinking`

### Default Behavior (skip_thinking=True)

```bash
python llamacpp_mqtt_deploy.py --projects general
```

**What happens:**
- Adds `/no_think` directive to the prompt
- Model skips deep thinking and goes directly to the answer
- Faster response times
- Lower token consumption
- Better for real-time applications

**Prompt transformation:**
```
Original: "What is 2+2?"
After:    "What is 2+2?\n/no_think"
```

**Example output:**
```
The answer is 4.
```

### Enable Thinking (skip_thinking=False)

```bash
python llamacpp_mqtt_deploy.py --projects general --skip_thinking False
```

**What happens:**
- No `/no_think` directive added
- Model performs full deep reasoning before answering
- Longer response times
- Higher token consumption (thinking tokens count as output)
- Better reasoning for complex problems

**Example output:**
```
Let me think about this step by step...

Okay, so we need to add two numbers: 2 and 2.
2 + 2 equals 4.

The answer is 4.
```

## Implementation Details

### 1. Prompt Directive Method
The script adds `/no_think` to the prompt when `skip_thinking=True`:

```python
if self.config.skip_thinking:
    payload["prompt"] = f"{prompt}\n/no_think"
```

### 2. Stop Token Control
Stop tokens prevent thinking output from being generated:

```python
if self.config.skip_thinking:
    payload["stop"] = ["</think>", "<think>", "**Final Answer**"]
else:
    payload["stop"] = []
```

### 3. Output Cleaning
The `_clean_qwq_output()` method removes any remaining thinking markers:

- Handles `**Final Answer**` markers
- Removes `<think>...</think>` blocks
- Filters out thinking-related phrases (English and Chinese)

## Usage Examples

### Example 1: Production (No Thinking)
```bash
python llamacpp_mqtt_deploy.py \
  --projects "maze driving bloodcell" \
  --server_url http://localhost:8080 \
  --mqtt_username TangClinic \
  --mqtt_password Tang123
```

Fast responses, lower latency, ideal for game agents.

### Example 2: Research/Analysis (With Thinking)
```bash
python llamacpp_mqtt_deploy.py \
  --projects general \
  --server_url http://localhost:8080 \
  --skip_thinking False \
  --max_tokens 2048
```

Full reasoning visible, better for complex questions.

### Example 3: Custom Multi-Project Setup
```bash
python llamacpp_mqtt_deploy.py \
  --projects "maze:no_think driving:think general:no_think" \
  --server_url http://localhost:8080 \
  --mqtt_username TangClinic \
  --mqtt_password Tang123
```

**Note:** Currently, the global `--skip_thinking` flag applies to all projects. For per-project control, you would need custom system prompts with `/think` or `/no_think` directives embedded.

## Aliyun Reference

From https://help.aliyun.com/zh/model-studio/deep-thinking:

> 混合思考模型通过 `enable_thinking` 参数控制是否开启思考模式：
> - `true`：开启思考模式
> - `false`：关闭思考模式
>
> 此外，Qwen3 开源版的混合思考模型与 qwen-plus-2025-04-28、qwen-turbo-2025-04-28 模型提供了通过提示词动态控制思考模式的方法。`enable_thinking` 为 `true` 时，在提示词中加上 `/no_think`，模型会关闭思考模式。

**Translation:**
> Hybrid thinking models control thinking mode via the `enable_thinking` parameter:
> - `true`: Enable thinking mode
> - `false`: Disable thinking mode
>
> Additionally, Qwen3 open-source hybrid thinking models provide a way to dynamically control thinking mode via prompts. When `enable_thinking` is `true`, adding `/no_think` to the prompt will disable thinking mode.

## Performance Comparison

| Aspect | skip_thinking=True | skip_thinking=False |
|--------|-------------------|-------------------|
| **Response Time** | Fast (immediate) | Slow (30-60s) |
| **Token Usage** | ~30-50% lower | ~50-100% higher |
| **Quality** | Good | Excellent |
| **Use Case** | Real-time games | Research, analysis |
| **Output Format** | Direct answer | Reasoning + answer |

## Debugging

Check the debug log for thinking mode status:

```bash
tail -f debug_info.log | grep "Thinking Mode"
```

You'll see:
```
Thinking Mode: DISABLED  (when skip_thinking=True)
Thinking Mode: ENABLED   (when skip_thinking=False)
```

## Common Issues

### Issue 1: Model still shows thinking output
**Solution:** Ensure stop tokens are set correctly. Update your server command:
```bash
llama-server -m ./qwen3-30b.gguf --stop "</think>" --stop "<think>" -ngl 99 --port 8080
```

### Issue 2: /no_think directive not recognized
**Solution:** This directive is specific to Qwen3 models. Verify your model supports it:
- ✅ Qwen3-30B (Hybrid thinking)
- ✅ Qwen3-32B
- ❌ QwQ (Thinking-only, can't disable)
- ❌ Standard Qwen models (no thinking capability)

### Issue 3: Responses are truncated
**Solution:** The `/no_think` directive sometimes causes early stopping. Workaround:
```bash
python llamacpp_mqtt_deploy.py \
  --projects general \
  --skip_thinking False \
  --max_tokens 1024
```

Then manually filter thinking output.

## API Parameters Reference

When `skip_thinking=True`, the payload sent to llama.cpp includes:

```json
{
  "prompt": "Your question here?\n/no_think",
  "temperature": 0.6,
  "top_p": 0.9,
  "n_predict": 512,
  "stop": ["</think>", "<think>", "**Final Answer**"],
  "stream": false
}
```

When `skip_thinking=False`:

```json
{
  "prompt": "Your question here?",
  "temperature": 0.6,
  "top_p": 0.9,
  "n_predict": 512,
  "stop": [],
  "stream": false
}
```

## Recommended Settings by Use Case

### 🎮 Game Agents (Maze, Driving, BloodCell)
```bash
--skip_thinking True
--temperature 0.6
--max_tokens 256
```

### 🧠 Reasoning Tasks
```bash
--skip_thinking False
--temperature 0.7
--max_tokens 1024
```

### 📚 General Chat
```bash
--skip_thinking True
--temperature 0.6
--max_tokens 512
```

### 🔬 Research Analysis
```bash
--skip_thinking False
--temperature 0.5
--max_tokens 2048
```

## Summary

- **`--skip_thinking True` (default)**: Faster, cheaper, good for interactive applications
- **`--skip_thinking False`**: Slower, more expensive, better reasoning for complex tasks
- Both modes use the official Qwen3 directive `/no_think` as documented by Aliyun
- The script provides automatic cleanup of any thinking markers in the output
