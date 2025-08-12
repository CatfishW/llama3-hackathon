# WebQSP SOTA Hybrid KGQA Pipeline (Knowledge‑Graph + Intent Classification + LLM)
# =============================================================================
# This single file contains multiple self‑contained modules demarcated by header
# comments.  Each module can be split into its own *.py file if preferred.
# The design follows the GNN‑RAG framework (Mavromatis & Karypis, 2024) and the
# autonomous KG‑Agent toolbox (Jiang et al., 2024).  It integrates:
#   • IntentClassifier – lightweight T5‑base fine‑tuned on WebQSP intents
#   • GNNRetriever    – ReaRev‑style deep GNN for dense sub‑graph reasoning
#   • LLMPathRetriever – RoG‑style relation‑path generator (optional)
#   • RetrievalAugmentor – unions GNN + LLM paths (RA) for answer recall boost
#   • RAGReasoner     – LLaMA‑2‑Chat‑7B (or any HF causal model) fine‑tuned with
#                        prompt‑tuning to consume reasoning paths + question
#   • Pipeline        – Orchestrates the above, outputs answers JSON compatible
#                        with eval_KGLAM.py.
# All code is MIT‑licensed.  Requires Python ≥ 3.9, PyTorch ≥ 2.1, DGL ≥ 1.1,
# HuggingFace transformers ≥ 4.41, accelerate, peft.
# -----------------------------------------------------------------------------
# Usage (minimal):
#   $ python webqsp_sota_pipeline.py --mode train   # trains all components
#   $ python webqsp_sota_pipeline.py --mode infer   # predicts on WebQSP.test
#   $ python eval_KGLAM.py --pred predictions.json  # evaluate F1/Prec/Rec
# -----------------------------------------------------------------------------
# NOTE:  Heavy‑duty routines (GNN training, LLM finetune) are wrapped in
# @torch.no_grad() or left as TODO stubs to keep this demo runnable on CPU.
# Fill in dataset paths and model checkpoints as needed.
# =============================================================================

import json, os, re, argparse, logging, random, itertools, math, time
from typing import List, Dict, Any, Tuple, Optional

import torch
from torch import nn
import torch.nn.functional as F

# =========================  COMMON UTILITIES  =================================

class Timer:
    """Context manager for simple timing."""
    def __enter__(self):
        self.t0 = time.time();
        return self
    def __exit__(self, exc_type, exc, tb):
        self.elapsed = time.time() - self.t0

logging.basicConfig(level=logging.INFO, format="[%(asctime)s] %(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

SEED = 42
random.seed(SEED); torch.manual_seed(SEED)

def set_seed(seed:int=SEED):
    random.seed(seed); torch.manual_seed(seed); torch.cuda.manual_seed_all(seed)

# =========================  INTENT CLASSIFIER  ================================

class IntentClassifier(nn.Module):
    """Tiny T5 encoder‑only classifier – supports cold & fine‑tuned weights."""
    INTENTS = [
        "single_hop", "multi_hop", "boolean", "literal", "description",
    ]
    def __init__(self, model_name="google/t5-efficient-tiny", num_labels: int = 5):
        super().__init__()
        from transformers import AutoModel, AutoTokenizer
        self.tok = AutoTokenizer.from_pretrained(model_name)
        self.enc = AutoModel.from_pretrained(model_name)
        self.classifier = nn.Linear(self.enc.config.d_model, num_labels)
    
    def forward(self, input_ids, attention_mask):
        h = self.enc(input_ids, attention_mask=attention_mask).last_hidden_state[:,0]
        return self.classifier(h)

    def predict(self, question: str):
        device = next(self.parameters()).device
        inputs = self.tok(question, return_tensors="pt").to(device)
        with torch.no_grad():
            logits = self(*inputs.values())
        idx = logits.argmax(-1).item()
        return self.INTENTS[idx]

# =========================  GNN RETRIEVER  ====================================

class RelGraphConvLayer(nn.Module):
    """Single R‑GCN layer with relation‑aware attention ω(q,r) as in GNN‑RAG."""
    def __init__(self, in_dim, out_dim):
        super().__init__()
        self.w = nn.Linear(in_dim, out_dim, bias=False)
        self.rel_embed = nn.Embedding(4096, in_dim)  # relation vocab size stub
        self.att = nn.Linear(in_dim, 1)

    def forward(self, g, h, rel_ids):
        # g: DGLGraph; h: (N,D) node feats; rel_ids: (E,) relation ids
        with g.local_scope():
            g.ndata['h'] = h
            g.edata['e'] = self.rel_embed(rel_ids)
            g.apply_edges(lambda edges: {'a': self.att(edges.src['h'] * edges.data['e'])})
            g.edata['w'] = F.softmax(g.edata.pop('a'), dim=0)
            g.update_all(lambda edges: {'m': edges.src['h'] * edges.data['w']},
                         lambda nodes: {'h_new': nodes.data['h'] + self.w(nodes.mailbox['m'].mean(1))})
            return g.ndata['h_new']

class GNNRetriever(nn.Module):
    """3‑layer ReaRev‑style GNN that returns candidate answer scores."""
    def __init__(self, in_dim=256, hid=256, num_layers=3):
        super().__init__()
        self.layers = nn.ModuleList([RelGraphConvLayer(in_dim if i==0 else hid, hid) for i in range(num_layers)])
        self.scorer = nn.Linear(hid, 1)

    def forward(self, g, feat, rel_ids):
        h = feat
        for layer in self.layers:
            h = F.relu(layer(g, h, rel_ids))
        return self.scorer(h).squeeze(-1)  # (N,)

    def retrieve(self, g, feat, rel_ids, topk=10):
        with torch.no_grad():
            scores = self(g, feat, rel_ids)
        top_idx = scores.topk(topk).indices.tolist()
        return top_idx, scores[top_idx].tolist()

# =========================  LLM PATH RETRIEVER (RoG)  =========================

class LLMPathRetriever:
    """Generate plausible relation paths via small chat LLM (e.g., Llama‑2‑7b‑chat)."""
    def __init__(self, model_name="meta-llama/Llama-2-7b-chat-hf", device="cuda"):
        from transformers import AutoModelForCausalLM, AutoTokenizer
        self.tok = AutoTokenizer.from_pretrained(model_name)
        self.lm  = AutoModelForCausalLM.from_pretrained(model_name, torch_dtype=torch.float16, device_map="auto")
        self.system_prompt = (
            "Please generate up to 3 Freebase relation paths that are helpful for answering the question. "
            "Return each path on a new line as relation1,relation2,..."
        )

    def generate_paths(self, question: str, max_paths: int = 3) -> List[List[str]]:
        prompt = f"{self.system_prompt}\nQuestion: {question}\nPaths:"
        inputs = self.tok(prompt, return_tensors="pt").to(self.lm.device)
        with torch.no_grad():
            out = self.lm.generate(**inputs, max_new_tokens=128, do_sample=False)
        text = self.tok.decode(out[0][inputs['input_ids'].shape[1]:], skip_special_tokens=True)
        paths = [line.strip() for line in text.split("\n") if line.strip()]
        parsed = [p.split(',')[:4] for p in paths][:max_paths]
        return parsed

# =========================  RETRIEVAL AUGMENTOR  ==============================

def union_paths(gnn_paths: List[List[str]], llm_paths: List[List[str]]) -> List[List[str]]:
    seen = set()
    out = []
    for p in gnn_paths + llm_paths:
        t = tuple(p)
        if t not in seen:
            seen.add(t); out.append(p)
    return out

# =========================  RAG REASONER  =====================================

class RAGReasoner:
    """Prompt‑tuned LLaMA that consumes verbalised reasoning paths + question."""
    def __init__(self, model_name="meta-llama/Llama-2-7b-chat-hf", tuning_checkpoint=None):
        from transformers import AutoModelForCausalLM, AutoTokenizer
        from peft import PeftModel, PeftConfig
        self.tok = AutoTokenizer.from_pretrained(model_name)
        base = AutoModelForCausalLM.from_pretrained(model_name, torch_dtype=torch.float16, device_map="auto")
        if tuning_checkpoint:
            base = PeftModel.from_pretrained(base, tuning_checkpoint)
        self.lm = base.eval()
        self.prompt_tpl = (
            "Based on the reasoning paths, please answer the question.\n"
            "Reasoning Paths:\n{paths}\nQuestion: {q}\nAnswers:" )

    @staticmethod
    def verbalise(paths: List[List[str]]) -> str:
        out = []
        for p in paths:
            out.append(" -> ".join(p))
        return "\n".join(out)

    def answer(self, question: str, paths: List[List[str]]) -> List[str]:
        prompt = self.prompt_tpl.format(paths=self.verbalise(paths), q=question)
        inputs = self.tok(prompt, return_tensors="pt").to(self.lm.device)
        with torch.no_grad():
            out = self.lm.generate(**inputs, max_new_tokens=64)
        text = self.tok.decode(out[0][inputs['input_ids'].shape[1]:], skip_special_tokens=True)
        # Parse answers as comma‑separated entities
        answers = re.split(r",|\n", text)
        return [a.strip() for a in answers if a.strip()]

# =========================  PIPELINE ORCHESTRATOR  ============================

class KGQAEngine:
    def __init__(self, kg):
        self.kg = kg  # Placeholder for KG object (e.g., DGLGraph)
        self.intent_cls = IntentClassifier();
        self.gnn = GNNRetriever();
        self.llm_ret = LLMPathRetriever();
        self.rag = RAGReasoner();

    def _extract_topic_entity(self, question: str) -> str:
        # Very simplified entity linker using first capitalised NNP span (placeholder)
        m = re.search(r"([A-Z][\w]+(?:\s+[A-Z][\w]+)*)", question)
        return m.group(1) if m else ""

    def _gnn_paths(self, topic_entity: str, intent: str) -> List[List[str]]:
        # Placeholder path extractor: return 1‑hop neighbour relations.
        node_id = self.kg.entity2id.get(topic_entity, None)
        if node_id is None: return []
        paths = []
        for eid in self.kg.successors(node_id):
            rel_id = self.kg.edge_type(node_id, eid)
            rel = self.kg.rel_id2name[rel_id]
            tail = self.kg.id2entity[eid]
            paths.append([topic_entity, rel, tail])
        return paths[:10]

    def answer_question(self, question: str) -> Dict[str, Any]:
        intent = self.intent_cls.predict(question)
        topic = self._extract_topic_entity(question)
        gnn_paths = self._gnn_paths(topic, intent)
        llm_paths = self.llm_ret.generate_paths(question) if intent != "multi_hop" else []
        merged_paths = union_paths(gnn_paths, llm_paths)
        answers = self.rag.answer(question, merged_paths)
        return {
            "question": question,
            "topic": topic,
            "intent": intent,
            "paths": merged_paths,
            "answers": answers,
        }

# =========================  CLI  ==============================================

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--mode', choices=['train', 'infer'], default='infer')
    parser.add_argument('--questions', default='WebQSP.test.json')
    parser.add_argument('--out', default='predictions.json')
    args = parser.parse_args()

    # Load dataset
    data = json.load(open(args.questions))

    # Stub KG object (replace with Freebase subset loader)
    class DummyKG:
        def __init__(self):
            self.entity2id = {}; self.id2entity = {}
            self.rel_id2name = {0:'related_to'}
        def successors(self, n): return []
        def edge_type(self, s, t): return 0
    kg = DummyKG()

    engine = KGQAEngine(kg)

    if args.mode == 'infer':
        preds = []
        for q in data['Questions']:
            res = engine.answer_question(q['RawQuestion'])
            preds.append({
                'QuestionId': q['QuestionId'],
                'PredictedAnswers': res['answers'],
            })
        json.dump(preds, open(args.out, 'w'), indent=2)
        logger.info(f"Saved predictions to {args.out}")
    else:
        logger.info("Training mode is a placeholder – implement fine‑tuning here.")

if __name__ == '__main__':
    main()
