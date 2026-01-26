#!/bin/bash

echo "===================================="
echo "vLLM Auto-Restart Script"
echo "===================================="
echo "This script will keep vLLM serving Qwen3-VL-8B-Instruct alive."
echo "If it exits or crashes, it will automatically restart after 3 seconds."
echo "Press Ctrl+C to stop this script."
echo ""

# Optional: Activate conda environment if not already active
# eval "$(conda shell.bash hook)"
conda activate vllm # source ~/vllm/bin/activate
# source ~/vllm/bin/activate
# Configuration
# MODEL="Qwen/Qwen3-VL-8B-Instruct-FP8"
CUDA_VISIBLE_DEVICES="1"
MODEL="cyankiwi/Qwen3-VL-30B-A3B-Instruct-AWQ-8bit"
PORT="8888"
MAX_MODEL_LEN="38280"
GPU_MEMORY_UTILIZATION="0.8"

while true; do
    echo "[$(date)] Starting vLLM serve..."
    echo "Command: vllm serve \"$MODEL\" --port $PORT --max-model-len $MAX_MODEL_LEN --gpu-memory-utilization $GPU_MEMORY_UTILIZATION --trust-remote-code"
    echo ""

    CUDA_VISIBLE_DEVICES="1" vllm serve "$MODEL" --port $PORT --max-model-len $MAX_MODEL_LEN --gpu-memory-utilization $GPU_MEMORY_UTILIZATION --trust-remote-code 
    # --enable-auto-tool-choice --tool-call-parser hermes

    EXIT_CODE=$?
    echo ""
    echo "[$(date)] vLLM exited with code: $EXIT_CODE"
    echo ""

    if [ $EXIT_CODE -eq 0 ]; then
        echo "Server stopped normally."
    else
        echo "Server crashed or encountered an error!"
    fi

    echo "Restarting in 3 seconds... Press Ctrl+C to cancel."
    sleep 3
done

