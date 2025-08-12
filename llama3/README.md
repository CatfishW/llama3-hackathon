# Llama 3 – Local Inference, MQTT Services, WebQSP Evaluation, and Hackathon Demos

This repository combines a minimal Llama 3 inference stack with several practical examples:

- Local inference for text- and chat-completions using native Llama 3 weights
- MQTT services for building applications
  - `mqtt_deploy.py`: chat assistant over MQTT
  - `lam_mqtt_deploy.py`: Large Action Model (LAM) that returns JSON actions over MQTT
- WebQSP knowledge-graph QA evaluation utilities (`eval_KGLAM.py` and helpers)
- Hackathon demo: a 2D Maze “Red Blood Cell Adventure” game with assets and RL scaffolding

The code targets Python and PyTorch with optional CUDA acceleration.


## Contents

- Core library: `llama/` (tokenizer, model, generation)
- Examples: `example_text_completion.py`, `example_chat_completion.py`, `demo.py`
- MQTT services: `mqtt_deploy.py`, `lam_mqtt_deploy.py`
- WebQSP dataset and evaluation: `WebQSP/`, `eval_KGLAM.py`
- Hackathon demo: `Hackathon/` (game, UI, RL stubs, prompt-portal assets)
- Sample local weights folders (place your own): `Llama3.1-8B-Instruct/`, `Llama3.2-3B-Instruct/`


## Requirements

- Python 3.10+ recommended
- PyTorch (CUDA optional but recommended)
- Install base dependencies:

  ```powershell
  pip install -r requirements.txt
  ```

  The services and demos may require optional extras:

  - MQTT services: `paho-mqtt`, `transformers>=4.41`, optional `bitsandbytes` for 4/8-bit
  - Hackathon game: `pygame`
  - WebQSP extras (optional experimentation): `accelerate`, `peft`, `dgl`

  Example:

  ```powershell
  pip install paho-mqtt transformers bitsandbytes pygame
  ```

> Note for Windows PowerShell users: create and activate a venv if desired:
>
> ```powershell
> python -m venv .venv
> .\.venv\Scripts\Activate.ps1
> ```


## Model Weights

This repo expects the native “original” format (not Transformers safetensors) that matches `llama/`.

- After you obtain access to Llama weights (see License & Use Policy), place files as:

  ```text
  Llama3.x-*-Instruct/
    ├─ consolidated.00.pth
    ├─ params.json
    └─ tokenizer.model
  ```

- Alternatively, download from Hugging Face “original” folder for a given model and keep the directory layout.


## Quick Start: Chat and Text Completion (Local)

- Chat completion (set paths to your local model folder):

  ```powershell
  torchrun --nproc_per_node 1 example_chat_completion.py `
    --ckpt_dir Llama3.2-3B-Instruct `
    --tokenizer_path Llama3.2-3B-Instruct/tokenizer.model `
    --max_seq_len 512 --max_batch_size 4
  ```

- Text completion:

  ```powershell
  torchrun --nproc_per_node 1 example_text_completion.py `
    --ckpt_dir Llama3.2-3B-Instruct `
    --tokenizer_path Llama3.2-3B-Instruct/tokenizer.model `
    --max_seq_len 128 --max_batch_size 4 --max_gen_len 64
  ```

- Interactive demo (streams responses, trims history):

  ```powershell
  python .\demo.py --ckpt_dir Llama3.2-3B-Instruct --tokenizer_path Llama3.2-3B-Instruct/tokenizer.model
  ```

Notes
- The model-parallel world size must equal the number of shard files in your checkpoint directory (e.g., MP=1 for a single `consolidated.00.pth`).
- The native runtime supports up to 8192 context tokens; set `--max_seq_len` ≤ 8192 and adjust `--max_batch_size` to fit your GPU memory.


## MQTT Services

Both services expose topics on an MQTT broker (defaults are in the scripts). Set credentials via CLI flags if required.

### 1) Chat Assistant Service (`mqtt_deploy.py`)

- Subscribes: `llama/user_input/<sessionId>`
- Publishes:  `llama/assistant_response/<sessionId>`
- Session creation: publish any message to `llama/session`; the service replies with a new session id on `llama/session/response`.

Start with a local Llama 3 model:

```powershell
torchrun --nproc_per_node 1 .\mqtt_deploy.py `
  --model_type llama `
  --ckpt_dir Llama3.2-3B-Instruct `
  --tokenizer_path Llama3.2-3B-Instruct/tokenizer.model `
  --max_batch_size 4 `
  --mqtt_username <USER> `
  --mqtt_password <PASS>
```

Start with a Transformers model (QwQ, full precision):

```powershell
python .\mqtt_deploy.py --model_type qwq --model_name Qwen/QwQ-32B --mqtt_username <USER> --mqtt_password <PASS>
```

Quantized variants (optional):

```powershell
python .\mqtt_deploy.py --model_type qwq --model_name Qwen/QwQ-32B --quantization 4bit
python .\mqtt_deploy.py --model_type qwq --model_name Qwen/QwQ-32B --quantization 8bit
```

### 2) Large Action Model Service (`lam_mqtt_deploy.py`)

This service returns structured JSON actions for NPC control:

- Subscribes: `lam/user_input/<sessionId>` and `lam/session`
- Publishes:  `lam/assistant_response/<sessionId>` and `lam/session/response`

Start with local Llama:

```powershell
torchrun --nproc_per_node 1 .\lam_mqtt_deploy.py `
  --model_type llama `
  --ckpt_dir Llama3.2-3B-Instruct `
  --tokenizer_path Llama3.2-3B-Instruct/tokenizer.model `
  --max_batch_size 4 `
  --mqtt_username <USER> `
  --mqtt_password <PASS>
```

Start with Transformers (QwQ):

```powershell
python .\lam_mqtt_deploy.py --model_type qwq --model_name Qwen/QwQ-32B --mqtt_username <USER> --mqtt_password <PASS>
```

Implementation details
- Priority queue + worker pool for throughput
- Per-session dialog memory with trimming to respect `max_seq_len`
- Optional bitsandbytes 4/8-bit quantization when using Transformers models


## WebQSP Evaluation Toolkit

Evaluate entity/value extraction and lightweight linking on the WebQSP test set.

- Test set: `WebQSP/data/WebQSP.test.json`
- Llama-based runner: `eval_KGLAM.py` (async batched generation, streaming accuracy/time logs)
- Official evaluation script: `WebQSP/eval/eval.py`

Run inference and evaluation:

```powershell
torchrun --nproc_per_node 1 .\eval_KGLAM.py `
  --ckpt_dir Llama3.2-3B-Instruct `
  --tokenizer_path Llama3.2-3B-Instruct/tokenizer.model `
  --test_path WebQSP/data/WebQSP.test.json `
  --pred_path preds.json `
  --max_batch_size 4
```

You can override `--eval_script_path` to point to a specific `eval.py`; otherwise, the script tries to locate it near the test set.


## Hackathon: 2D Maze “Red Blood Cell Adventure”

Arcade-style maze game with assets and RL scaffolding.

- Path: `Hackathon/`
- Requirements: `pygame`
- Run the game:

  ```powershell
  pip install pygame
  python .\Hackathon\main.py
  ```

Assets live under `Hackathon/assets/`. The game includes path visualization and can be extended to integrate LAM hints.


## Troubleshooting

- CUDA OOM: lower `--max_batch_size` and/or `--max_seq_len`. Ensure bf16/half is used automatically if supported.
- Checkpoint sharding: `torchrun --nproc_per_node` must equal the number of `.pth` shards in your checkpoint folder.
- Windows tips: if `torchrun` is not on PATH, reinstall PyTorch or call `python -m torch.distributed.run ...`.
- MQTT connectivity: confirm broker/port/credentials and that your client subscribes to the correct session-suffixed topics.


## License and Use Policy

- See `LICENSE` and `USE_POLICY.md` for model and code usage terms.
- By using Llama weights, you agree to the corresponding license and acceptable use policies from the model provider.


## Acknowledgements

This code includes a minimal Llama 3 reference implementation and additional integrations for demos and evaluation.
