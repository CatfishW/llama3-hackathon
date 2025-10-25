# Qwen3 30B Optimization Guide for RTX 4090

## Problem
RTX 4090 has 24GB VRAM, but Qwen3 30B requires ~60GB in FP16, causing Out-of-Memory errors.

## Memory Comparison
| Method | Memory Required | Speed | Quality |
|--------|-----------------|-------|---------|
| FP16 (no quant) | ~60GB | Fastest | Best |
| FP8 Quantization | ~30GB | Very Fast | Excellent |
| 8-bit (GPTQ/AWQ) | ~30GB | Fast | Excellent |
| 4-bit Quantization | ~15GB | Fast | Good |
| 2048 context (FP16) | ~45GB | Fastest | Best |
| 2048 context (FP8) | ~22GB | Very Fast | Excellent ✅ |

## Recommended Solutions (Best to Worst)

### 🥇 Solution 1: FP8 Quantization (BEST)
Uses native GPU FP8 support on Ada architecture.

```bash
python vLLMDeploy.py \
  --projects general \
  --model qwen3-30b-a3b-instruct-2507 \
  --quantization fp8 \
  --max_model_len 2048 \
  --gpu_memory_utilization 0.75 \
  --visible_devices "0"
```

**Expected memory usage:** ~18GB  
**Speed:** Very fast (minimal overhead)  
**Quality:** Minimal quality loss (FP8 is quite accurate)

---

### 🥈 Solution 2: Reduce Context Length (SIMPLE)
Keep FP16 but reduce context window from 4096 to 2048 tokens.

```bash
python vLLMDeploy.py \
  --projects general \
  --model qwen3-30b-a3b-instruct-2507 \
  --max_model_len 2048 \
  --gpu_memory_utilization 0.70 \
  --visible_devices "0"
```

**Expected memory usage:** ~23GB  
**Speed:** Fastest  
**Quality:** Full FP16 quality  
**Trade-off:** Shorter conversation context (8K tokens if 2 exchanges)

---

### 🥉 Solution 3: 4-bit Quantization (Most Aggressive)
Maximum memory savings but slight quality loss.

```bash
python vLLMDeploy.py \
  --projects general \
  --model qwen3-30b-a3b-instruct-2507 \
  --quantization bitsandbytes \
  --max_model_len 2048 \
  --gpu_memory_utilization 0.60 \
  --visible_devices "0"
```

**Expected memory usage:** ~12-14GB  
**Speed:** Fast  
**Quality:** Good (noticeable but acceptable loss)  
**Benefit:** Lowest memory usage, room for batching

---

## Quick Debug Checklist

### Check Current Memory Usage
```bash
# Windows - watch GPU memory
nvidia-smi -l 1
```

### Verify CUDA Installation
```bash
python -c "import torch; print(torch.cuda.is_available()); print(torch.cuda.get_device_name(0))"
```

### Test Individual Solutions
```bash
# Test 1: FP8 (safest for 4090)
python vLLMDeploy.py --projects general --model qwen3-30b-a3b-instruct-2507 --quantization fp8 --max_model_len 2048

# Test 2: Context reduction only
python vLLMDeploy.py --projects general --model qwen3-30b-a3b-instruct-2507 --max_model_len 2048 --gpu_memory_utilization 0.70

# Test 3: 4-bit quantization
python vLLMDeploy.py --projects general --model qwen3-30b-a3b-instruct-2507 --quantization bitsandbytes --max_model_len 2048
```

---

## Parameter Tuning Reference

### gpu_memory_utilization
- **0.90**: Maximum utilization (default) - often causes OOM
- **0.75**: Balanced - recommended for 4090
- **0.60**: Conservative - safe for large models
- **0.50**: Very safe - avoids fragmentation

### max_model_len
- **4096**: Full context (requires more memory)
- **2048**: Half context (recommended for 30B)
- **1024**: Quarter context (for severe memory constraints)

### quantization options
- **fp8**: Best for Ada/4090, minimal loss
- **awq/gptq**: Pre-quantized models only
- **bitsandbytes**: 4-bit, most savings

---

## Diagnosis: Why Out of Memory?

1. **Model too large in FP16**: 30B × 2 bytes (FP16) = 60GB
2. **GPU memory fragmentation**: vLLM memory allocation
3. **Context window too large**: Each token needs buffer space
4. **High gpu_memory_utilization**: Leaves no headroom for inference

---

## Expected Performance

| Config | Memory | Speed | Max Batch |
|--------|--------|-------|-----------|
| FP8 + 2K context | 18GB | 45 tok/s | 4 |
| FP16 + 2K context | 23GB | 50 tok/s | 2 |
| 4-bit + 2K context | 12GB | 40 tok/s | 8 |

---

## Recommended Configuration for Production

```bash
python vLLMDeploy.py \
  --projects maze driving bloodcell \
  --model qwen3-30b-a3b-instruct-2507 \
  --quantization fp8 \
  --max_model_len 2048 \
  --gpu_memory_utilization 0.75 \
  --temperature 0.6 \
  --top_p 0.9 \
  --max_tokens 512 \
  --num_workers 12 \
  --visible_devices "0" \
  --mqtt_broker 47.89.252.2
```

This should:
- Use ~18GB GPU memory (safe on 4090)
- Allow batching of 4-8 concurrent requests
- Maintain good response quality with FP8
- Support multiple projects simultaneously

---

## Troubleshooting

### Still getting OOM?
1. Reduce `max_model_len` to 1024
2. Lower `gpu_memory_utilization` to 0.60
3. Add `--quantization bitsandbytes` for 4-bit

### Slow inference?
1. Increase `max_model_len` back to 2048
2. Increase `gpu_memory_utilization` to 0.80
3. Reduce `num_workers` to reduce context switch overhead

### Poor response quality?
1. Try FP8 instead of 4-bit
2. Increase `temperature` slightly (0.7-0.8)
3. Use full FP16 (reduce `max_model_len` instead)

