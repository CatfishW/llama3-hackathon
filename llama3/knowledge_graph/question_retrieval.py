#!/usr/bin/env python3
"""Question-focused related node retrieval for WebQSP-style KG QA.

This module adds an *efficient and interpretable* heuristic retriever that, given a
natural language question (e.g. a WebQSP question) and a KnowledgeGraph instance
(`kg_loader.KnowledgeGraph`), identifies:

1. Candidate topic entities (seeds) likely mentioned in the question.
2. Predicates (relations) in the local 1–2 hop neighborhood whose surface form
   matches or is semantically proxied via token overlap / fuzzy similarity.
3. Related nodes reachable through those predicates, ranked by a composite score.

Design goals:
---------------------------------
* Fast: purely Python stdlib; precomputes lightweight token → entity/predicate
  inverted indexes (sets) for O(k) candidate gathering where k = number of query tokens.
* Transparent: scoring is explicit (token overlap, length reward, fuzzy ratio).
* Extensible: can later plug in embedding similarity without changing outer API.
* Safe for large graphs: caps expansion breadth & depth; uses early pruning.

Core Steps:
---------------------------------
Given a question:
    1. Normalize & tokenize (lowercase, alnum tokens).
    2. Candidate entity detection:
         - Longest matching n-gram substrings that exactly occur as a KG subject.
         - Alias map lookups (alias value appears in question → canonical entity).
         - Token overlap between question tokens and entity label tokens via inverted index.
       Score = (overlap / entity_tokens) + 0.1 * log(len(entity_text)+1) + 0.05 * degree.
    3. For top-N seed entities (default 3):
         - Collect 1-hop triples; score each predicate by token overlap & fuzzy ratio.
         - Keep top-K predicates per seed (default 8) with score ≥ predicate_threshold.
         - Expand a constrained second hop only through selected predicates and only
           if the intermediate / target node introduces new question-relevant tokens.
    4. Aggregate nodes: a node score = max path predicate score * path_length_factor
       (shorter better) + small bonus if node surface tokens overlap question.
    5. Return structured result with provenance (paths) for explainability.

Efficiency Considerations:
---------------------------------
* Index build: O(|V| + |E|) tokenization (single pass over subjects & predicates).
* Query time: O(T + C * (deg_1 + filtered_deg_2)) where T = #question tokens, C = #candidate seeds (small).
* All sets/lists kept bounded by configuration parameters.

Edge Cases:
---------------------------------
* No entity candidates → we fall back to predicate-centric retrieval (scan predicates that match tokens) and return their subjects/objects as weak candidates.
* Ambiguous multi-entity mention (e.g., "New York City mayor") → select multiple seeds.
* Questions answerable by literal (date/number) nodes still surfaced if reachable within constraints.

Public API:
---------------------------------
Class: QuestionGraphRetriever
    constructor(kg, alias_weight=0.5, predicate_threshold=0.15, ...)

    retrieve(question: str, max_paths_per_node=3) -> Dict
        Returns a dict with keys:
            'question', 'question_tokens', 'candidates', 'related_nodes', 'triples'

Lightweight CLI (optional):
    python question_retrieval.py --triples rogkg_triples.tsv.gz --question "..."

Future Improvements (not implemented here):
---------------------------------
* Embedding similarity (e.g. MiniLM) for predicates / entity labels.
* Constrained logical form induction.
* Dynamic BFS guided by learned policy.

"""

from __future__ import annotations

import argparse
import math
import re
from collections import defaultdict, deque, Counter
from dataclasses import dataclass
from typing import Dict, List, Set, Tuple, Optional, Iterable

from kg_loader import KnowledgeGraph, load_kg, Triple

# ---------------- Tokenization Helpers ---------------- #

TOKEN_RE = re.compile(r"[a-z0-9]+")

def tokenize(text: str) -> List[str]:
    return TOKEN_RE.findall(text.lower()) if text else []

def ngrams(tokens: List[str], max_n: int = 5) -> Iterable[Tuple[int,int,Tuple[str,...]]]:
    L = len(tokens)
    for n in range(min(max_n, L), 0, -1):  # start from longest
        for i in range(L - n + 1):
            yield i, i+n, tuple(tokens[i:i+n])

def fuzzy_ratio(a: str, b: str) -> float:
    # lightweight similarity (SequenceMatcher ratio) without external deps
    # Avoid import cost at module import time (lazy import)
    from difflib import SequenceMatcher
    return SequenceMatcher(None, a.lower(), b.lower()).ratio()


# ---------------- Data Structures ---------------- #

@dataclass
class CandidateEntity:
    name: str
    score: float
    method: str
    overlap: float
    degree: int

@dataclass
class RelatedNode:
    node: str
    score: float
    reasons: List[str]
    paths: List[List[Triple]]  # multiple provenance paths


class QuestionGraphRetriever:
    """Heuristic retriever mapping natural language questions to related KG nodes.

    Parameters
    ----------
    kg : KnowledgeGraph
        Loaded KG instance.
    alias_weight : float
        Bonus weight applied if an alias exact match triggers an entity.
    predicate_threshold : float
        Minimum predicate relevance score to be considered during expansion.
    max_seed_entities : int
        Top-N entity seeds kept.
    max_predicates_per_entity : int
        Limit of predicates considered per seed entity.
    max_expanded_nodes : int
        Global cap on distinct related nodes returned (excluding seeds).
    max_two_hop_per_seed : int
        Bound second hop expansions (per seed) for efficiency.
    """

    def __init__(
        self,
        kg: KnowledgeGraph,
        alias_weight: float = 0.5,
        predicate_threshold: float = 0.15,
        max_seed_entities: int = 3,
        max_predicates_per_entity: int = 8,
        max_expanded_nodes: int = 200,
        max_two_hop_per_seed: int = 80,
    ):
        self.kg = kg
        self.alias_weight = alias_weight
        self.predicate_threshold = predicate_threshold
        self.max_seed_entities = max_seed_entities
        self.max_predicates_per_entity = max_predicates_per_entity
        self.max_expanded_nodes = max_expanded_nodes
        self.max_two_hop_per_seed = max_two_hop_per_seed
        # Embedding config (hash-based, no external model download needed)
        self.embed_dim = 256  # power of two preferred
        self.use_embeddings = True  # can be toggled off if desired

        # Precompute indexes / structures
        self.subject_token_index: Dict[str, Set[str]] = defaultdict(set)
        self.object_token_index: Dict[str, Set[str]] = defaultdict(set)
        self.predicate_token_index: Dict[str, Set[str]] = defaultdict(set)
        self.alias_inv_index: Dict[str, str] = {}  # alias token sequence → canonical entity
        self.normalized_label_map: Dict[str, Set[str]] = defaultdict(set)  # normalized surface → set(entities)
        self.token_df: Counter = Counter()  # document frequency over nodes
        self.total_nodes: int = 0
        self.stopwords = {
            'the','a','an','of','to','in','on','for','is','are','was','were','by','and','or','which','that','who','whom','whose','what','when','where','why','how'
        }
        # Simple predicate token synonym / expansion map
        self.synonym_map = {
            'country': {'country','nation','state'},
            'part': {'part','member','component','portion','within','in','of','belong','belongs','belonging','included'},
            'belong': {'belong','belongs','belonging','part','within','in'},
            'located': {'located','location','situated','in','within'},
        }
        self._build_indexes()

    # -------- Index building -------- #
    def _build_indexes(self):
        subjects = list(self.kg.sp_index.keys())
        objects = list(self.kg.os_index.keys())
        # Distinct node set for IDF
        node_set = set(subjects) | set(objects)
        self.total_nodes = len(node_set)
        for node in node_set:
            toks = set(tokenize(node))
            for t in toks:
                self.token_df[t] += 1
            norm = " ".join(sorted(toks))
            self.normalized_label_map[norm].add(node)
        for subj in subjects:
            for t in tokenize(subj):
                self.subject_token_index[t].add(subj)
        for obj in objects:
            for t in tokenize(obj):
                self.object_token_index[t].add(obj)
        for pred in self.kg.po_index.keys():
            for t in tokenize(pred):
                self.predicate_token_index[t].add(pred)
        for alias, canonical in self.kg.alias.items():
            self.alias_inv_index[alias.lower()] = canonical

    def _idf(self, token: str) -> float:
        df = self.token_df.get(token, 0) + 1
        return math.log(1 + (self.total_nodes + 1) / df)

    def _expand_synonym(self, token: str) -> Set[str]:
        return self.synonym_map.get(token, {token})

    # -------- Hash / IDF Embeddings (lightweight semantic proxy) -------- #
    def _hash_token(self, token: str) -> int:
        # Stable hash -> index
        import hashlib
        h = hashlib.md5(token.encode('utf-8')).hexdigest()
        return int(h[:8], 16) % self.embed_dim

    def _text_embedding(self, tokens: List[str]) -> List[float]:
        vec = [0.0] * self.embed_dim
        if not tokens:
            return vec
        for t in tokens:
            idx = self._hash_token(t)
            vec[idx] += self._idf(t)
        # L2 normalize
        import math as _m
        norm = _m.sqrt(sum(x*x for x in vec)) + 1e-9
        return [x / norm for x in vec]

    def _cosine(self, a: List[float], b: List[float]) -> float:
        return sum(x*y for x, y in zip(a, b))

    # -------- Candidate Entities -------- #
    def _entity_candidates(self, question: str, q_tokens: List[str]) -> List[CandidateEntity]:
        q_text_lower = question.lower()
        seen: Dict[str, CandidateEntity] = {}

        content_tokens = [t for t in q_tokens if t not in self.stopwords]
        if not content_tokens:
            content_tokens = q_tokens

        # Alias exact phrase matches
        for alias_lower, canonical in self.alias_inv_index.items():
            if alias_lower in q_text_lower:
                deg = self.kg.degree(canonical)
                score = 2.0 + self.alias_weight + 0.05 * math.log(deg + 1)
                seen[canonical] = CandidateEntity(canonical, score, "alias", 1.0, deg)

        # Exact n-gram matches (subjects or objects)
        subj_keys = self.kg.sp_index.keys()
        obj_keys = self.kg.os_index.keys()
        key_sets = (subj_keys, obj_keys)
        for start, end, ng in ngrams(content_tokens, max_n=6):
            phrase = " ".join(ng)
            for key_set in key_sets:
                for ent in key_set:
                    if ent.lower() == phrase:
                        deg = self.kg.degree(ent)
                        base = len(ng) / (len(content_tokens) + 1e-6)
                        score = 1.5 + base + 0.05 * math.log(deg + 1)
                        cur = seen.get(ent)
                        if not cur or score > cur.score:
                            seen[ent] = CandidateEntity(ent, score, "ngram", base, deg)

        # Token overlap (subjects + objects) with IDF weighting
        token_entity_scores: Dict[str, float] = defaultdict(float)
        for t in content_tokens:
            idf = self._idf(t)
            for subj in self.subject_token_index.get(t, []):
                token_entity_scores[subj] += idf
            for obj in self.object_token_index.get(t, []):
                token_entity_scores[obj] += idf
        for ent, accum in token_entity_scores.items():
            ent_toks = tokenize(ent)
            if not ent_toks:
                continue
            norm = sum(self._idf(tok) for tok in set(ent_toks)) + 1e-6
            overlap_ratio = accum / norm
            if overlap_ratio <= 0:
                continue
            deg = self.kg.degree(ent)
            score = overlap_ratio + 0.1 * math.log(len(ent) + 1) + 0.04 * math.log(deg + 1)
            cur = seen.get(ent)
            if not cur or score > cur.score:
                seen[ent] = CandidateEntity(ent, score, "idf_overlap", overlap_ratio, deg)

        candidates = sorted(seen.values(), key=lambda x: x.score, reverse=True)
        return candidates[: self.max_seed_entities]

    # -------- Predicate scoring -------- #
    def _predicate_relevance(self, predicate: str, q_tokens: List[str]) -> float:
        ptoks = tokenize(predicate)
        if not ptoks:
            return 0.0
        q_expanded: Set[str] = set()
        for qt in q_tokens:
            q_expanded |= self._expand_synonym(qt)
        ptok_set = set(ptoks)
        overlap_tokens = ptok_set & q_expanded
        if overlap_tokens:
            # IDF-weighted predicate overlap
            score = sum(self._idf(t) for t in overlap_tokens) / (sum(self._idf(t) for t in ptok_set) + 1e-6)
            return score
        # fuzzy fallback
        joined = " ".join(ptoks)
        joined_q = " ".join(q_tokens)
        fuzz = fuzzy_ratio(joined, joined_q)
        return 0.3 * fuzz if fuzz > 0.8 else 0.0

    # -------- Expansion -------- #
    def _expand_from_seed(self, seed: CandidateEntity, q_tokens: List[str]) -> Tuple[List[Triple], Dict[str, List[List[Triple]]]]:
        collected_triples: List[Triple] = []
        node_paths: Dict[str, List[List[Triple]]] = defaultdict(list)

        # gather 1-hop
        predicate_scores: Dict[Triple, float] = {}
        pred_rank: List[Tuple[float, Triple]] = []

        def record(triple: Triple, score: float):
            collected_triples.append(triple)
            predicate_scores[triple] = score
            s, p, o = triple
            node_paths[o].append([triple])
            node_paths[s].append([triple])  # include reverse for completeness

        # Out edges
        for p, o in self.kg.sp_index.get(seed.name, []):
            sc = self._predicate_relevance(p, q_tokens)
            if sc >= self.predicate_threshold:
                t = (seed.name, p, o)
                pred_rank.append((sc, t))
        # In edges (treat as predicates too)
        for s, p in self.kg.os_index.get(seed.name, []):
            sc = self._predicate_relevance(p, q_tokens)
            if sc >= self.predicate_threshold:
                t = (s, p, seed.name)
                pred_rank.append((sc, t))

        pred_rank.sort(reverse=True, key=lambda x: x[0])
        if not pred_rank:
            # adaptive lower threshold: take top 5 predicates ignoring threshold
            for p, o in self.kg.sp_index.get(seed.name, [])[:5]:
                t = (seed.name, p, o)
                pred_rank.append((0.05, t))
            for s, p in self.kg.os_index.get(seed.name, [])[:5]:
                t = (s, p, seed.name)
                pred_rank.append((0.05, t))
        for sc, t in pred_rank[: self.max_predicates_per_entity]:
            record(t, sc)

        # Second hop expansion (guided)
        second_hop_budget = self.max_two_hop_per_seed
        visited = {seed.name}
        frontier_nodes = {t[2] for _, t in pred_rank[: self.max_predicates_per_entity]} | {t[0] for _, t in pred_rank[: self.max_predicates_per_entity]}
        for node in list(frontier_nodes):
            if second_hop_budget <= 0:
                break
            # Outgoing
            for p, o in self.kg.sp_index.get(node, []):
                if second_hop_budget <= 0:
                    break
                sc = self._predicate_relevance(p, q_tokens)
                if sc < self.predicate_threshold:
                    continue
                triple = (node, p, o)
                path_extend_ok = True
                if path_extend_ok:
                    collected_triples.append(triple)
                    node_paths[o].append(self._best_path_to(node, node_paths) + [triple])
                    second_hop_budget -= 1
            # Incoming
            for s, p in self.kg.os_index.get(node, []):
                if second_hop_budget <= 0:
                    break
                sc = self._predicate_relevance(p, q_tokens)
                if sc < self.predicate_threshold:
                    continue
                triple = (s, p, node)
                collected_triples.append(triple)
                node_paths[s].append(self._best_path_to(node, node_paths) + [triple])
                second_hop_budget -= 1

        return collected_triples, node_paths

    def _best_path_to(self, node: str, node_paths: Dict[str, List[List[Triple]]]) -> List[Triple]:
        paths = node_paths.get(node)
        if not paths:
            return []
        # prefer shortest path (could incorporate score weighting later)
        return min(paths, key=len)

    # -------- Main Public Method -------- #
    def retrieve(self, question: str, max_paths_per_node: int = 3) -> Dict:
        q_tokens = tokenize(question)
        expanded_synonyms = sorted({syn for t in q_tokens for syn in self._expand_synonym(t)})
        candidates = self._entity_candidates(question, q_tokens)

        if not candidates:
            matching_preds = set()
            for t in q_tokens:
                matching_preds.update(self.predicate_token_index.get(t, set()))
            triples = []
            for pred in list(matching_preds)[:10]:
                for s, o in self.kg.po_index.get(pred, [])[:25]:
                    triples.append((s, pred, o))
            return {
                "question": question,
                "question_tokens": q_tokens,
                "expanded_tokens": expanded_synonyms,
                "candidates": [],
                "related_nodes": [],
                "triples": triples,
                "note": "No entity candidates found; predicate-centric fallback used.",
            }

        all_triples: List[Triple] = []
        node_paths_agg: Dict[str, List[List[Triple]]] = defaultdict(list)
        seed_names = {c.name for c in candidates}
        per_seed_predicate_scores: Dict[str, List[Tuple[str, float]]] = {}

        for seed in candidates:
            triples, node_paths = self._expand_from_seed(seed, q_tokens)
            all_triples.extend(triples)
            pred_scores: Dict[str, float] = defaultdict(float)
            for (s,p,o) in triples:
                if s == seed.name or o == seed.name:
                    pred_scores[p] = max(pred_scores.get(p, 0.0), self._predicate_relevance(p, q_tokens))
            per_seed_predicate_scores[seed.name] = sorted(pred_scores.items(), key=lambda x: x[1], reverse=True)[:15]
            for node, paths in node_paths.items():
                node_paths_agg[node].extend(paths[:max_paths_per_node])

        related_nodes: List[RelatedNode] = []
        q_tok_set = set(q_tokens)
        for node, paths in node_paths_agg.items():
            if node in seed_names:
                continue
            ntoks = tokenize(node)
            overlap = len(q_tok_set & set(ntoks)) / (len(ntoks) + 1e-6) if ntoks else 0.0
            path_scores = []
            reasons = []
            for path in paths:
                if not path:
                    continue
                pred_overlaps = 0
                predicates = []
                for (_, p, _) in path:
                    predicates.append(p)
                    pred_overlaps += len(set(tokenize(p)) & q_tok_set)
                length_penalty = 1 / len(path)
                ps = (pred_overlaps + 1) * length_penalty
                path_scores.append(ps)
                reasons.append(f"path len={len(path)} preds={predicates} score={ps:.2f}")
            if not path_scores:
                continue
            score_base = max(path_scores) + 0.5 * overlap
            related_nodes.append(RelatedNode(node=node, score=score_base, reasons=reasons[:3], paths=paths[:max_paths_per_node]))

        embedding_debug: Dict[str, float] = {}
        if self.use_embeddings and related_nodes:
            q_embed = self._text_embedding([t for t in q_tokens if t not in self.stopwords])
            for rn in related_nodes:
                label_tokens = [tok for tok in tokenize(rn.node) if tok not in self.stopwords]
                node_embed = self._text_embedding(label_tokens)
                sim = self._cosine(q_embed, node_embed)
                rn.score = rn.score + 0.6 * sim
                embedding_debug[rn.node] = sim
        related_nodes.sort(key=lambda r: r.score, reverse=True)

        if not related_nodes and candidates:
            seed0 = candidates[0].name
            for p, o in self.kg.sp_index.get(seed0, [])[:10]:
                if o not in seed_names:
                    related_nodes.append(RelatedNode(node=o, score=0.05, reasons=["fallback 1-hop"], paths=[[(seed0,p,o)]]))
            for s, p in self.kg.os_index.get(seed0, [])[:10]:
                if s not in seed_names:
                    related_nodes.append(RelatedNode(node=s, score=0.05, reasons=["fallback 1-hop"], paths=[[(s,p,seed0)]]))
            related_nodes.sort(key=lambda r: r.score, reverse=True)

        if len(related_nodes) > self.max_expanded_nodes:
            related_nodes = related_nodes[: self.max_expanded_nodes]

        seen_triple = set()
        dedup_triples: List[Triple] = []
        for t in all_triples:
            if t not in seen_triple:
                dedup_triples.append(t)
                seen_triple.add(t)

        answer_type = None
        q_lower = " ".join(q_tokens)
        if any(t in q_lower for t in ["country","nation","state"]):
            answer_type = "country"
        elif any(t in q_lower for t in ["who","person","individual","artist"]):
            answer_type = "person"
        elif any(t in q_lower for t in ["when","year","date"]):
            answer_type = "date"
        elif any(t in q_lower for t in ["where","location","place","city"]):
            answer_type = "location"

        return {
            "question": question,
            "question_tokens": q_tokens,
            "expanded_tokens": expanded_synonyms,
            "expected_answer_type": answer_type,
            "candidates": [c.__dict__ for c in candidates],
            "per_seed_predicates": {seed: [(p, round(sc,4)) for p, sc in preds] for seed, preds in per_seed_predicate_scores.items()},
            "related_nodes": [
                {
                    "node": rn.node,
                    "score": rn.score,
                    "reasons": rn.reasons,
                    "paths": rn.paths,
                    "embedding_sim": embedding_debug.get(rn.node),
                }
                for rn in related_nodes
            ],
            "triples": dedup_triples,
            "debug": {
                "predicate_threshold": self.predicate_threshold,
                "seed_entities": [c.name for c in candidates],
                "embedding_used": self.use_embeddings,
                "total_related": len(related_nodes),
            }
        }


# ---------------- CLI for quick manual testing ---------------- #
def _cli():
    import json
    ap = argparse.ArgumentParser(description="Question-focused related node retrieval")
    ap.add_argument("--triples", required=True, help="Path to triples .tsv.gz")
    ap.add_argument("--alias", help="Path to alias map JSON")
    ap.add_argument("--question", required=True, help="Natural language question")
    ap.add_argument("--limit", type=int, help="Limit triples for faster test")
    ap.add_argument("--top-n-related", type=int, default=15, help="How many related nodes to show")
    ap.add_argument("--no-paths", action='store_true', help="Hide detailed paths in output")
    ap.add_argument("--json", action='store_true', help="Print full JSON result and exit")
    args = ap.parse_args()

    kg = load_kg(args.triples, args.alias, args.limit)
    retriever = QuestionGraphRetriever(kg)
    result = retriever.retrieve(args.question)

    if args.json:
        print(json.dumps(result, indent=2))
        return

    # Pretty print structured debug output
    print("=== QUESTION ===")
    print(result['question'])
    print(f"Tokens: {result['question_tokens']}")
    print(f"Expanded tokens: {result.get('expanded_tokens')}  | Expected answer type: {result.get('expected_answer_type')}")

    print("\n=== CANDIDATE ENTITIES ===")
    if not result['candidates']:
        print("(none)")
    else:
        for i, c in enumerate(result['candidates'], 1):
            print(f"{i:2d}. {c['name']} | score={c['score']:.4f} | method={c['method']} | overlap={c['overlap']:.3f} | degree={c['degree']}")

    print("\n=== PER-SEED TOP PREDICATES ===")
    per_seed = result.get('per_seed_predicates', {})
    if not per_seed:
        print('(none)')
    else:
        for seed, plist in per_seed.items():
            print(f"- {seed}:")
            if not plist:
                print("    (no matching predicates)")
            for p, sc in plist:
                print(f"    {p}  (rel_score={sc})")

    print("\n=== RETRIEVED RELATED NODES (top {args.top_n_related}) ===")
    related = result.get('related_nodes', [])
    if not related:
        print('(none)')
    for idx, rn in enumerate(related[:args.top_n_related], 1):
        print(f"{idx:2d}. node={rn['node']} | score={rn['score']:.4f} | embed_sim={(rn.get('embedding_sim') if rn.get('embedding_sim') is not None else 'NA')}")
        print("    Reasons:")
        for r in rn.get('reasons', []):
            print(f"      - {r}")
        if not args.no_paths:
            paths = rn.get('paths', [])
            if paths:
                print("    Paths:")
                for p_i, path in enumerate(paths, 1):
                    triple_str = " | ".join(f"({s} --{pr}--> {o})" for s, pr, o in path)
                    print(f"      [{p_i}] {triple_str}")
            else:
                print("    Paths: (none)")

    print("\n=== TRIPLES SUMMARY ===")
    print(f"Total supporting triples collected: {len(result.get('triples', []))}")

    dbg = result.get('debug', {})
    if dbg:
        print("\n=== DEBUG META ===")
        for k, v in dbg.items():
            print(f"{k}: {v}")
    if 'note' in result:
        print(f"\nNOTE: {result['note']}")

if __name__ == "__main__":  # pragma: no cover (manual invocation)
    _cli()
