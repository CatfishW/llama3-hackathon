#!/usr/bin/env python3
import gzip
import json
from collections import defaultdict, deque
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Set, Tuple

Triple = Tuple[str, str, str]

class KnowledgeGraph:
    def __init__(self, triples: Iterable[Triple], alias: Optional[Dict[str, str]] = None):
        self.triples: List[Triple] = list(triples)
        self.alias = alias or {}

        # Indexes
        self.sp_index: Dict[str, List[Tuple[str, str]]] = defaultdict(list)      # subject -> [(predicate, object)]
        self.po_index: Dict[str, List[Tuple[str, str]]] = defaultdict(list)      # predicate -> [(subject, object)]
        self.os_index: Dict[str, List[Tuple[str, str]]] = defaultdict(list)      # object -> [(subject, predicate)]
        self.s_index: Dict[str, int] = defaultdict(int)
        self.p_index: Dict[str, int] = defaultdict(int)
        self.o_index: Dict[str, int] = defaultdict(int)

        for s, p, o in self.triples:
            self.sp_index[s].append((p, o))
            self.po_index[p].append((s, o))
            self.os_index[o].append((s, p))
            self.s_index[s] += 1
            self.p_index[p] += 1
            self.o_index[o] += 1

    # ---- Basic lookups ----
    def objects(self, subject: str, predicate: Optional[str] = None) -> List[str]:
        return [o for p, o in self.sp_index.get(subject, []) if predicate is None or p == predicate]

    def subjects(self, obj: str, predicate: Optional[str] = None) -> List[str]:
        return [s for s, p in self.os_index.get(obj, []) if predicate is None or p == predicate]

    def triples_with_predicate(self, predicate: str) -> List[Triple]:
        return [(s, predicate, o) for s, o in self.po_index.get(predicate, [])]

    def predicates(self) -> List[str]:
        return list(self.po_index.keys())

    def degree(self, node: str) -> int:
        return len(self.sp_index.get(node, [])) + len(self.os_index.get(node, []))

    # ---- Search ----
    def search_subject_contains(self, substring: str, max_results: int = 20) -> List[str]:
        sub = substring.lower()
        out = []
        for s in self.sp_index:
            if sub in s.lower():
                out.append(s)
                if len(out) >= max_results:
                    break
        return out

    # ---- Path (unweighted BFS over directed edges) ----
    def shortest_path(self, start: str, goal: str, max_depth: int = 5) -> Optional[List[Triple]]:
        if start == goal:
            return []
        visited: Set[str] = {start}
        q = deque([(start, [])])
        while q:
            node, path = q.popleft()
            if len(path) >= max_depth:
                continue
            for p, o in self.sp_index.get(node, []):
                if o in visited:
                    continue
                new_path = path + [(node, p, o)]
                if o == goal:
                    return new_path
                visited.add(o)
                q.append((o, new_path))
        return None

    # ---- Stats ----
    def summary(self) -> Dict[str, int]:
        return {
            "n_triples": len(self.triples),
            "n_subjects": len(self.sp_index),
            "n_predicates": len(self.po_index),
            "n_objects": len(self.os_index),
        }

    def head(self, n: int = 10) -> List[Triple]:
        """Return first n triples."""
        return self.triples[:n]

# -------- Load helpers --------
def load_triples_tsv_gz(path: Path, limit: Optional[int] = None) -> Iterable[Triple]:
    with gzip.open(path, "rt", encoding="utf-8") as f:
        for i, line in enumerate(f):
            if limit and i >= limit:
                break
            s, p, o = line.rstrip("\n").split("\t", 2)
            yield (s, p, o)

def load_alias(path: Path) -> Dict[str, str]:
    if not path.is_file():
        return {}
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)

def load_kg(triples_path: str, alias_path: Optional[str] = None, limit: Optional[int] = None) -> KnowledgeGraph:
    triples = list(load_triples_tsv_gz(Path(triples_path), limit=limit))
    alias = load_alias(Path(alias_path)) if alias_path else {}
    return KnowledgeGraph(triples, alias=alias)

# -------- CLI (optional) --------
if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser(description="Load KG and run simple queries.")
    ap.add_argument("--triples", required=True, help="Path to *_triples.tsv.gz")
    ap.add_argument("--alias", help="Path to *_alias_map.json")
    ap.add_argument("--limit", type=int, help="Limit triples for quick test")
    ap.add_argument("--search", help="Substring to search in subjects")
    ap.add_argument("--show-triples", type=int, metavar="N", help="Print first N triples")
    args = ap.parse_args()

    kg = load_kg(args.triples, args.alias, args.limit)
    print("Summary:", kg.summary())

    if args.search:
        print("Subject matches:", kg.search_subject_contains(args.search))

    if args.show_triples:
        n = args.show_triples
        print(f"First {min(n, len(kg.triples))} triples:")
        for s, p, o in kg.head(n):
            print(f"{s}\t{p}\t{o}")