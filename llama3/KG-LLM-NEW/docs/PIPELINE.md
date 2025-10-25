# KG-LLM-NEW Pipeline Overview

```
┌─────────────┐      ┌─────────────────────┐      ┌─────────────────────┐      ┌─────────────────────┐      ┌──────────────────────┐
│ Data Source │ ───► │ Preprocessing Layer │ ───► │ Question Typing     │ ───► │ Retrieval + Filtering│ ───► │ Prompting & LLM      │
│ (Firebase / │      │  (shard builders,   │      │  (multi-label        │      │  (multi-granular     │      │  (llama.cpp via HTTP │
│  JSONL / KG)│      │   WebQSP, custom)   │      │   classifier)         │      │   BM25 + heuristics) │      │   or MQTT backend)   │
└─────────────┘      └─────────────────────┘      └─────────────────────┘      └─────────────────────┘      └──────────────────────┘
                                        │                                             │
                                        │                                             ▼
                                        │                             ┌───────────────────────────────┐
                                        └──────────────────────────► │ Evidence Bundling & Analytics │
                                                                      (token reports, latency logs)
```

## Stage-by-Stage Outcomes

| Stage | Input | Output | Notes |
|-------|-------|--------|-------|
| Data Source | Firestore collections, Freebase Easy TSVs, JSONL shards, or WebQSP dumps | Raw documents or KG shards | `kg_llm_new.tasks download-firebase` filters Firestore collections; `prepare-freebase-easy` streams the public dump into shards. |
| Preprocessing | Raw Firebase/Freebase/WebQSP dumps | Typed shard files (`one_hop.jsonl`, `two_hop.jsonl`, etc.) | `FirebaseProcessor` groups docs by `shard_type`; the Freebase builder writes shard JSONL directly; WebQSP tooling emits classifier training JSONL. |
| Question Typing | User query text | Active label set + per-label probabilities | `QuestionClassifier` (SentenceTransformer + logistic head) predicts required evidence granularities. |
| Retrieval + Filtering | Active labels + seed entities | Evidence shards limited by budgets | `Retriever` runs BM25 over shard corpora, applies per-label budget, and optional heuristics (degree penalties configurable). |
| Prompting & LLM | Question + evidence | Final answer text, evidence token counts, latency metrics | `PromptBuilder` constructs grounded prompt; `LLMClient` routes to llama.cpp via HTTP or MQTT. Debug logs capture timings and token usage. |

## Typical Execution Flow

1. **Ingest knowledge**
   - Use `python -m kg_llm_new.tasks download-firebase ... --process-shards` to pull Firestore knowledge and build shard JSONL files.
   - Use `python -m kg_llm_new.tasks prepare-freebase-easy ...` to turn the Freebase Easy dump (`facts.txt`, `scores.txt`) into shard files without loading everything into memory.
   - Alternatively, place handcrafted shard files in `storage/` and point `PipelineConfig.storage.kg_path` to that directory.

2. **(Optional) Train classifier head**
   - Prepare labeled questions via `prepare-webqsp` (or your own dataset).
   - Train the logistic head with `train-classifier` and evaluate with `evaluate-classifier`.

3. **Run inference**
   - From the CLI: `python -m kg_llm_new.cli "Question" Entity --classifier-head weights.json --kg-path ./kg_data --mode http --server-url http://localhost:8080/v1`.
   - Inspect logs for label probabilities, evidence token budget usage, and total latency.

4. **Monitor outputs**
   - Debug logs (`logs/`) include detailed evidence bundles, LLM responses, and timing breakdowns.
   - Shard statistics are available via `Retriever` logging (`KG summary` and BM25 index counts).

## Result Artifacts

- **`firebase_raw.jsonl`**: Raw documents captured from Firestore for reproducibility.
- **Shard JSONL files**: One per knowledge granularity, ready for `KnowledgeGraphLoader`.
- **Classifier weights JSON**: Logistic head weights used by `QuestionClassifier`.
- **Pipeline logs**: Latency metrics, evidence token counts, and full prompts for debugging.
- **Answer outputs**: Returned via CLI/adapter; downstream systems can persist through MQTT or HTTP depending on deployment mode.
