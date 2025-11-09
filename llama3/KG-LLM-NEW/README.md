# KG-LLM-NEW

Implementation of a maintainable prototype for the multi-granular knowledge-graph-enhanced LLM pipeline described in the research manuscript.

## Project Highlights

- **Multi-label question typing** via a lightweight `SentenceTransformer` encoder plus sigmoid head. Head weights are external (JSON) for easy training/refresh.
- **Shard-aware KG retrieval** with separate one-hop, two-hop, literal, and description stores loaded from JSONL dumps.
- **Lexical-first retrieval** using BM25 indices per shard to maintain latency, configurable budgets, and optional entity seeding.
- **Prompt construction** that exposes retrieval provenance and label probabilities for tracing decisions.
- **LLM backend abstraction** supporting:
  - HTTP OpenAI-compatible llama.cpp server (`llama-server` via `OpenAI` SDK).
  - MQTT broker workflow to reuse the `llamacpp_mqtt_deploy.py` infrastructure when needed.
  - KG-only fallback that synthesizes answers purely from retrieved shard evidence when no LLM backend is available.
  - Classifier-free KG+LLM mode via `--no-classifier`, which activates uniform label priors while still sending grounded prompts to the configured LLM transport.
- **Firebase ingest tooling** to pull Firestore collections with filters, dump raw JSONL, and emit shard files compatible with the retriever.
- **Freebase Easy ingestion** to transform the public dump into retriever-ready shard files.

## Layout

```
KG-LLM-NEW/
  README.md
  kg_llm_new/
    __init__.py
    cli.py
    config.py
    logging_utils.py
    prompt.py
    classification/
      __init__.py
      question_classifier.py
    kg/
      __init__.py
      loader.py
      freebase.py
      structures.py
    llm/
      __init__.py
      client.py
    retrieval/
      __init__.py
      filters.py
      retriever.py
```

## Getting Started

1. **Install dependencies** (example):
   ```powershell
  pip install sentence-transformers rank-bm25 scikit-learn firebase-admin openai paho-mqtt pyarrow pandas
   ```

2. **Prepare resources**:
   - Place classifier head weights JSON (exported from fine-tuning) somewhere accessible.
   - Populate `kg_path` directory with shards: `one_hop.jsonl`, `two_hop.jsonl`, `literal.jsonl`, `description.jsonl`.
   - **NEW**: For large datasets (22GB+), convert text files to Parquet format first (see [Parquet Integration](#parquet-support) below).

3. **Run the CLI** against HTTP llama-server:
   ```powershell
   python -m kg_llm_new.cli "Who directed Forrest Gump?" "Forrest_Gump" --classifier-head .\weights.json --kg-path .\kg_data --mode http --server-url http://localhost:8080/v1
   ```

4. **Run the CLI** via MQTT bridge:
   ```powershell
  python -m kg_llm_new.cli "When was the director of the film starring Tom Hanks born?" Tom_Hanks --classifier-head .\weights.json --kg-path .\kg_data --mode mqtt --mqtt-broker 127.0.0.1 --mqtt-username user --mqtt-password pass

5. **Run the CLI** in KG-only mode (no LLM backend required):
  ```powershell
  python -m kg_llm_new.cli "When was Tom Hanks born?" Tom_Hanks --classifier-head .\weights.json --kg-path .\kg_data --mode kg-only
  ```
  The pipeline ranks retrieved evidence and renders an explanatory answer directly from the knowledge graph.

6. **Skip the classifier (use KG + LLM only):**
  ```powershell
  python -m kg_llm_new.cli "When was Tom Hanks born?" Tom_Hanks --kg-path .\kg_data --mode http --server-url http://localhost:8080/v1 --no-classifier
  ```
  This keeps the LLM backend active while using uniform label priors to maximize KG retrieval without loading the SentenceTransformer weights.
   ```

The MQTT path expects the deployment script to publish answers on `kg_llm_new/response`.

## WebQSP Workflow

1. **Prepare labeled data:**
  ```powershell
  python -m kg_llm_new.tasks prepare-webqsp --input .\WebQSP.train.json --output .\webqsp_train.jsonl
  python -m kg_llm_new.tasks prepare-webqsp --input .\WebQSP.test.json --output .\webqsp_test.jsonl
  ```
  The command logs per-label counts and the most frequent composite label combinations so you can sanity-check the heuristics.

2. **Train classifier head:**
  ```powershell
  python -m kg_llm_new.tasks train-classifier --train .\webqsp_train.jsonl --val .\webqsp_test.jsonl --output .\weights.json
  ```

3. **Evaluate classifier:**
  ```powershell
  python -m kg_llm_new.tasks evaluate-classifier --head .\weights.json --data .\webqsp_test.jsonl
  ```

## Firebase Knowledge Integration

1. **Download with optional filters:**
  ```powershell
  python -m kg_llm_new.tasks download-firebase `
     --credentials .\service-account.json `
     --collection knowledge_shards `
     --project my-firebase-project `
     --output-dir .\kg_data `
     --where shard_type == "one_hop" `
     --limit 5000 `
     --process-shards
  ```
  - `--where FIELD OP VALUE` may be repeated; `VALUE` is parsed as JSON when possible.
  - `--process-shards` groups documents by `shard_type` and writes `one_hop.jsonl`, `two_hop.jsonl`, etc.

2. **Process an existing raw dump:**
  ```powershell
  python -m kg_llm_new.tasks process-firebase --input .\firebase_raw.jsonl --output-dir .\kg_data
  ```

Documents are expected to include `shard_type` (one of `one_hop`, `two_hop`, `literal`, `description`) and a `payload` matching the shard schema (e.g., `{ "head": ..., "relation": ..., "tail": ... }`).

## Freebase Easy Knowledge Integration

### Standard Processing (Text Files)

1. **Download and extract the dump:** grab `freebase-easy-latest.zip`, unpack it, and note the directory containing `facts.txt`, `scores.txt`, and `freebase-links.txt`.
2. **Generate shard JSONL files:**
  ```powershell
  python -m kg_llm_new.tasks prepare-freebase-easy `
    --root .\freebase-easy-latest `
    --output-dir .\kg_data `
    --languages en `
    --max-facts 100000
  ```
  - Use `--facts`/`--scores` to override individual files, `--skip-scores` to ignore `scores.txt`, and `--allow-all-languages` to keep every language tag.
  - `--max-facts` is optional but handy for creating a manageable subset during development.
3. **Point the pipeline at the new shards:** either pass `--kg-path .\kg_data` to the CLI or enable `freebase_easy` in `PipelineConfig` so the pipeline auto-builds/consumes the dump.

### Parquet Support (Recommended for Large Datasets)

For **22GB+ datasets**, use Parquet format for 60-70% compression and memory-safe processing:

1. **Convert text files to Parquet** (one-time operation):
  ```powershell
  cd freebase-easy-latest
  python convert_to_parquet.py
  ```
  This creates `facts.parquet` (~7-8GB), `scores.parquet` (~1GB), saving disk space and processing time.

2. **Configure pipeline to use Parquet**:
  ```python
  from kg_llm_new.config import PipelineConfig, FreebaseEasyConfig
  
  config = PipelineConfig(
      freebase_easy=FreebaseEasyConfig(
          enabled=True,
          root_path=Path("./freebase-easy-latest"),  # Auto-detects .parquet files
          use_parquet=True,  # Prefer Parquet (default)
          chunk_size=100000,  # Adjust based on your RAM
      ),
  )
  ```

3. **Benefits**:
   - 2-3x faster processing
   - 80% less memory usage (chunked processing)
   - Works with 4GB+ RAM systems
   - No need to load entire 22GB file

**See [docs/PARQUET_INTEGRATION.md](docs/PARQUET_INTEGRATION.md) for complete guide.**

## Notes & Adjustments

- The original manuscript assumed dense+BM25 retrieval and two-hop beam expansion. This prototype focuses on lexical BM25 per shard for reproducibility, leaving semantic reranking and path beam search as extension points (`Retriever` class).
- Constrained decoding and literal verification are not hard-coded; hook into `PromptBuilder`/`LLMClient` or extend the pipeline.
- Latency logging, token allocation, and budgets are configurable via `PipelineConfig`.
- Classifier head is externalized to avoid shipping large weight files.

## Pipeline Reference

See `docs/PIPELINE.md` for a stage-by-stage overview of data ingestion, classification, retrieval, prompting, and logging outputs.

## Next Steps

- Implement training utilities for the question classifier head.
- Add reranker integration (e.g., cosine similarity) and type-aware filtering heuristics.
- Integrate constrained decoding strategies when llama.cpp adds support for logit bias / grammar constraints.
- Expand end-to-end tests with synthetic KG shards to validate retrieval coverage and prompt assembly.

python -m kg_llm_new.cli "When was the director of the film starring Tom Hanks born?" Tom_Hanks --classifier-head .\weights.json --kg-path .\kg_data --mode mqtt --mqtt-broker 47.89.252.2:1883 --mqtt-username TangClinic --mqtt-password Tang123