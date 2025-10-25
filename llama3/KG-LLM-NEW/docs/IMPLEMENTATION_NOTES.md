# Implementation Notes & Deviations

This document records engineering choices that refine or deviate from the research manuscript.

## Question Classification (Paper §4.2)
- **New tooling:** Added WebQSP preprocessing and a scikit-learn `OneVsRest` logistic regression trainer (`kg_llm_new.tasks`). Label inference now inspects annotated `InferentialChain` metadata and answer types (with text fallbacks) rather than regex-ing the SPARQL alone; tune heuristics if higher fidelity supervision is available.

- **Adjustment:** Semantic re-ranking and PMI-guided path expansion are abstracted but not fully implemented. The `Retriever` currently performs BM25 lookup per shard and returns entity-specific shards respecting label budgets.
  - Rationale: pragmatic initial milestone; future work can plug in dense rerankers and relation priors.
- **Two-hop Paths:** Loader expects precomputed two-hop records. Dynamic beam expansion is outside scope; provide TODO hook in retriever.

## Filtering & Regularization (Paper §4.4)
- **Adjustment:** Candidate filter currently trims shard sizes but does not compute explicit degree penalties or relation priors. Hooks exist in `FilterConfig` for subsequent enhancements.

## Prompt Construction & Constrained Decoding (Paper §4.5–4.6)
- **Adjustment:** Prompt builder produces a grounded message with evidence sections and probability cues. Constrained decoding (entity whitelisting, literals) depends on llama.cpp capabilities; not enforced at the code level.

## LLM Backend Integration (Paper §3)
- **Improvement:** Added explicit abstraction for llama.cpp HTTP and MQTT modes, reusing the existing `llamacpp_mqtt_deploy.py` infrastructure. MQTT path assumes deployment publishes answers on `kg_llm_new/response`.

## System Architecture (Paper §5)
- **Adjustment:** Storage layer loads JSONL shards without tiered caching. Users can mount caches via `StorageConfig` if required.
- **New capability:** Added Firestore ingestion helpers (`FirebaseDownloader`, `FirebaseProcessor`) with CLI hooks for filtered exports and shard generation. Documents must expose `shard_type` plus a shard-specific payload.
- **New capability:** Added a streaming Freebase Easy shard builder (`FreebaseEasyShardBuilder`) so the public dump can feed the pipeline without loading all 22 GB into memory. Config handles language filtering, score ingestion, and subset sampling.

## Future Enhancements
- Train and release classifier head weights.
- Attach semantic rerankers and entity-typing heuristics.
- Implement literal verification and citation alignment before rendering final answers.
- Provide evaluation scripts to reproduce dataset benchmarks.
