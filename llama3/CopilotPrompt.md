% KG-Enhanced LLM Reasoning for Action-Oriented Applications
\documentclass[conference]{IEEEtran}

% --- Packages ---
\usepackage{cite}
\usepackage{amsmath,amssymb}
\usepackage{graphicx}
% --- Added packages ---
\usepackage{booktabs}
\usepackage{multirow}
\usepackage{tabularx}
\usepackage{xcolor}
\usepackage{algorithm}
\usepackage{algorithmic}
\usepackage{enumitem}
\usepackage{hyperref}
\usepackage{subcaption}
\usepackage{adjustbox}
\usepackage{pifont}

\newcommand{\cmark}{\ding{51}}
\newcommand{\xmark}{\ding{55}}
\newcommand{\model}{\textsc{KG-ActionLLM}}
\newcommand{\st}{SentenceTransformer}
\newcommand{\todo}[1]{\textcolor{red}{[TODO: #1]}}

\title{Multi-Granular Knowledge Graph Enhanced Large Language Models for Complex Question Answering: A Comprehensive Framework with Subgraph Classification and Retrieval-Augmented Generation}

\author{%
  \IEEEauthorblockN{First Author\thanks{Corresponding author.}}
  \IEEEauthorblockA{Department of Electrical and Computer Engineering\\Rowan University, USA\\ email@domain.com}
  \and
  \IEEEauthorblockN{Second Author}
  \IEEEauthorblockA{Department of Computer Science\\University of Technology\\ City, Country\\ email@domain.com}
  \and
  \IEEEauthorblockN{Third Author}
  \IEEEauthorblockA{AI Research Laboratory\\Tech Corporation\\ City, Country\\ email@domain.com}
}

\begin{document}
\maketitle

\begin{abstract}
Large Language Models (LLMs) demonstrate remarkable capabilities in natural language understanding and generation, yet they struggle with knowledge-intensive tasks requiring precise factual information and multi-hop reasoning. To address these limitations, we propose a novel multi-granular knowledge graph (KG) enhanced framework that strategically decomposes large-scale knowledge graphs into specialized subgraphs and employs sophisticated retrieval mechanisms for improved question answering. Our approach partitions a comprehensive Freebase-derived knowledge graph into four distinct subgraph types: one-hop relational structures, two-hop reasoning paths, literal property mappings, and entity description repositories. We develop a multi-label SentenceTransformer-based classifier that intelligently predicts question types with composite labels (e.g., one-hop+literal, two-hop+description), enabling targeted subgraph retrieval. The retrieved subgraph information undergoes advanced filtering through regularization techniques and pattern matching algorithms before being integrated into LLM prompts for both zero-shot and fine-tuned answer generation. Comprehensive experiments on WebQSP, ComplexWebQuestions, and MetaQA datasets demonstrate significant improvements in exact match accuracy (15.3\% average gain), F1 scores (12.7\% improvement), and multi-hop reasoning capabilities compared to vanilla LLMs, traditional text-based RAG systems, and existing KG-augmented approaches. Our framework achieves state-of-the-art performance while maintaining computational efficiency with average inference times under 800ms.
\end{abstract}

\begin{IEEEkeywords}
Knowledge graph, large language model, question answering, multi-hop reasoning, retrieval-augmented generation, subgraph classification, composite labeling
\end{IEEEkeywords}

\section{Introduction}

Large Language Models (LLMs) have transformed how machines understand and generate natural language, achieving remarkable success across diverse tasks. Yet their Achilles' heel emerges in knowledge-intensive question answering: when pressed for precise facts, multi-hop reasoning chains, or temporal information, even state-of-the-art models hallucinate or produce plausible but incorrect answers. This gap between fluency and factual reliability has sparked intense research into augmenting LLMs with external knowledge sources.

Knowledge graphs---structured repositories encoding entities, relations, and facts---offer a natural solution. Unlike unstructured text corpora, KGs provide explicit relational structure that mirrors the logical dependencies required for complex reasoning. However, integrating symbolic KG representations with neural LLM architectures remains challenging. Existing approaches typically retrieve large, undifferentiated subgraphs around seed entities, overwhelming the model with irrelevant facts while missing critical evidence. Consider the question: \emph{"When was the director of the film starring Tom Hanks born?"} An effective system must (1) identify Tom Hanks as the seed, (2) traverse two-hop paths through intermediate films and directors, (3) retrieve literal birth dates, and (4) synthesize these heterogeneous evidence types into a coherent answer. Current methods either retrieve all neighborhood information indiscriminately, incurring computational overhead and noise, or rely on iterative multi-round retrieval that multiplies latency.

We address this challenge through a fundamental insight: \textbf{questions naturally decompose into distinct knowledge access patterns}. Simple factual queries like \emph{"Who directed Forrest Gump?"} require one-hop relation traversal. Multi-hop questions demand path-based reasoning. Temporal or numerical queries need literal properties. Definitional questions benefit from entity descriptions. Critically, many real-world questions exhibit \emph{composite} patterns requiring simultaneous access to multiple knowledge granularities. This observation motivates our core innovation: \textbf{multi-granular knowledge graph decomposition}---systematically partitioning KGs into specialized subgraph types aligned with question reasoning patterns, coupled with intelligent retrieval that activates only the required granularities.

Our framework operates in three strategic phases. First, we decompose large-scale KGs into four typed subgraph repositories: one-hop relational neighborhoods, two-hop reasoning paths, literal property mappings, and entity descriptions. This decomposition serves dual purposes---reducing retrieval search space and enabling granularity-specific optimization. Second, we train a multi-label question classifier that predicts \emph{composite} knowledge requirements (e.g., "two-hop + literal"), directly triggering parallel retrieval across relevant subgraph types without iterative expansion. Third, we employ a hybrid BM25-semantic retrieval pipeline with interpretable structural scoring, avoiding expensive graph neural network encodings while maintaining high recall. The resulting evidence undergoes token-budget-aware filtering before being synthesized by the LLM through constrained decoding that enforces faithfulness to retrieved facts.

This design delivers substantial empirical gains. On WebQSP, ComplexWebQuestions, and MetaQA benchmarks, our approach achieves 15.3\% average improvement in exact match accuracy over strong baselines, with particularly dramatic gains on multi-hop questions (up to 20.9\% improvement). Crucially, we maintain inference latency under 800ms---significantly faster than iterative reasoning methods---while achieving 91.3\% faithfulness scores through explicit citation of evidence sources. Ablation studies confirm that multi-granular decomposition contributes 6.1 points to exact match performance, validating our central hypothesis that question-aligned KG partitioning enables more precise and efficient knowledge integration.

The implications extend beyond performance metrics. By aligning KG structure with reasoning patterns, our framework enhances interpretability: retrieved evidence directly corresponds to predicted question types, facilitating failure analysis and system debugging. The modular architecture supports independent updates to subgraph indices without retraining neural components, improving maintainability in production environments. Furthermore, our approach reconciles the efficiency-quality tradeoff that plagues existing methods: early granularity classification prunes the search space before expensive expansion, while composite label prediction eliminates redundant retrieval rounds.

\textbf{Contributions.} We present a comprehensive framework with four key innovations: (1) Multi-granular KG decomposition into reasoning-pattern-aligned subgraph types with specialized indexing strategies; (2) Composite multi-label question classification enabling parallel heterogeneous evidence retrieval; (3) Hybrid BM25-semantic retrieval with interpretable structural scoring, eliminating GNN encoding overhead; (4) Constrained decoding with citation-aware generation for faithful, traceable answers. Extensive experiments demonstrate state-of-the-art performance with superior efficiency, supported by detailed ablation studies isolating each component's contribution.

\section{Related Work}

Work on knowledge-intensive QA spans classical KB-QA, text-centric open-domain QA, neural KGQA and KG–text hybrids, iterative agentic reasoning on KGs, and decoding-time constraints, with a recent shift toward graph-centric RAG. Early KB-QA systems map questions to logical forms over Freebase/DBpedia via semantic parsing or templates \cite{berant2013semantic,yih2015stagg,bast2015aqqu,fader2014openkb}. Neural variants improved relation detection and robustness \cite{dong2015mccnn,bordes2015memnn,lukovnikov2017nnkgqa,yang2017neurallp}, yet these approaches remain sensitive to entity linking and relation ambiguity, often struggle with compositional queries (multi-hop, constraints, literals/aggregation), and depend heavily on KG coverage and hand-crafted grammars.

Open-domain QA framed as retrieve-then-read demonstrated that large text corpora and neural readers can answer factoid questions directly from Wikipedia \cite{chen2017drqa}, and multi-hop datasets catalyzed research on evidence chaining \cite{yang2018hotpotqa}. Modern RAG systems add learned retrieval control and hierarchical summaries \cite{asai2023selfrag,sarthi2024raptor}, but passages rarely make relations explicit; models must infer structure implicitly, which leads to brittle multi-hop reasoning, citation drift, and hallucination when lexical overlap is low.

To exploit structure explicitly, neural KGQA and KG–text hybrids retrieve subgraphs and reason with graph encoders or early fusion. GRAFT-Net links KB neighborhoods with text \cite{sun2018graftnet}, QA-GNN augments language models with graph structure \cite{yasunaga2021qagnn}, and unified pipelines pursue end-to-end retrieval and reasoning over KGs \cite{jiang2023unikgqa,li2024unioqa}. While these methods increase relational precision, GNN-style message passing introduces preprocessing and inference latency, exacerbates hub-node bias, and can generalize poorly as KGs evolve; many still retrieve monolithic neighborhoods that mix evidence with noise.

A complementary line performs iterative, agentic reasoning over KGs. Think-on-Graph and KG-Agent expand paths or plan actions step by step to expose intermediate decisions \cite{sun2023think,jiang2024kg}. These methods improve transparency and multi-hop accuracy but pay for it with multi-round latency, careful beam control to curb branching, and susceptibility to early errors in entity linking or type constraints. Decoding-time constraints reduce hallucination by biasing token probabilities toward retrieved graph items; Graph-Constrained Reasoning exemplifies this direction \cite{luo2024graph}. Such constraints, however, assume that retrieval already supplied the right evidence and do not decide which \emph{granularity} of knowledge is needed.

Recent GraphRAG efforts retrieve over graph structure rather than flat text, surveying design choices and proposing graph-indexed retrievers for domain and open settings \cite{peng2024graphrag_survey,hu2024grag,chen2024kg_retriever,xu2024ragkg_cs,tian2024kgadapter,avila2024autokgqa}. These approaches better capture relational context but often treat the graph as a single, undifferentiated store; they couple weakly to the generator and rarely model \emph{composite} evidence needs (e.g., a two-hop path together with a literal). Our framework addresses precisely these gaps by predicting composite, question-conditioned granularities (one-hop, two-hop, literals, descriptions) before retrieval, using a lexical-first, structure-aware retriever in lieu of GNN passes, and coupling retrieval with grounded, citation-aligned decoding.

\section{Problem Formulation}

We formalize the knowledge-intensive question answering task as follows: Given a large-scale knowledge graph $\mathcal{G} = (\mathcal{E}, \mathcal{R}, \mathcal{T})$ where $\mathcal{E}$ represents the set of entities, $\mathcal{R}$ denotes the set of relations, and $\mathcal{T} \subseteq \mathcal{E} \times \mathcal{R} \times \mathcal{E}$ contains the set of triples, along with associated literal properties $\mathcal{L}$ and entity descriptions $\mathcal{D}$, our objective is to answer a natural language question $q$ by producing an accurate answer $a^*$ that is both factually correct and faithful to the retrieved knowledge.

The key challenge lies in efficiently identifying and retrieving the most relevant subgraph $\mathcal{G}_{sub} \subset \mathcal{G}$ that contains the necessary information to answer question $q$, while maintaining computational efficiency and reasoning transparency. We model intermediate structure as a multi-label question type vector $y \in \{0,1\}^K$ where labels cover atomic (one-hop, two-hop, literal, description) and composite classes.

\section{Methodology}

\subsection{Overview}

We engineer the pipeline as a single flow. First, we shard the KG by how questions are answered—one-hop, two-hop, literals, and descriptions—to reduce hub bias and negative evidence while bounding retrieval. A lightweight multi-label typer then activates only the needed granularities and assigns budgets, shrinking the search space and keeping latency low. Retrieval is lexical-first: tight BM25 over shard textualizations with a light semantic re-ranker; two-hop paths expand via a constrained beam guided by relation priors, degree caps, and type compatibility, while literals/descriptions attach only when the expected answer form matches. Interpretable structural priors replace heavy GNN passes, delivering high recall with controllable precision. We distill the result into a grounded prompt where a token allocator prioritizes a compact knowledge table; decoding whitelists entities, softly guides relations, verifies literals, and fine-tuned models learn to cite. A brief post-validation step normalizes formats, de-duplicates, and aligns citations, yielding a practical balance of latency, token efficiency, and faithfulness.

\subsection{Why Multi-Granular Labels?}
We split the KG into multiple subgraph granularities and predict \emph{composite} label sets for three practical reasons:
\begin{itemize}[leftmargin=*]
  \item \textbf{Retrieval precision and token budgeting.} Different questions require different evidence units (edges vs paths vs literals vs descriptions). Predicting granularities up front prevents negative-evidence dilution and enables per-class top-$k$ budgets under a fixed prompt length.
  \item \textbf{Compositionality and faithfulness.} Many queries need \emph{simultaneous} access to heterogeneous evidence (e.g., a one-hop fact \emph{and} a date literal). Composite labels fuse type-relevant shards only, improving traceability and citation alignment.
  \item \textbf{Latency and system engineering.} Segmented indices (triples, literals, descriptions, path sketches) are smaller and cache-friendly. Lexical-first retrieval scoped by predicted labels avoids dense/GNN passes on irrelevant regions, yielding a better quality–latency trade-off.
\end{itemize}
Ablations further indicate benefits in (i) calibrating retrieval size via per-label thresholds, (ii) transparent failure analysis by label bucket, and (iii) maintainability—indices can be refreshed per shard without retraining structural encoders.

\subsection{Multi-Granular KG Decomposition}

We partition the knowledge graph $\mathcal{G}$ into four specialized subgraph types, each optimized for different reasoning patterns. This approach differs from prior methods that either retrieve large undifferentiated neighborhoods (GNN-RAG \cite{mavromatis2024gnn}, Graph-Constrained Reasoning (GCR) \cite{luo2024graph}) or rely on iterative exploration (KG-Agent \cite{jiang2024kg}, Think-on-Graph \cite{sun2023think}). Our multi-granular shard inventory reduces negative evidence dilution versus monolithic union neighborhoods.

\textbf{One-hop Subgraphs ($\mathcal{G}_1$)}: For each entity $e \in \mathcal{E}$, we construct its one-hop subgraph as:
\begin{equation}
\mathcal{G}_1(e) = \{(e, r, e') \in \mathcal{T} : e' \in \mathcal{E}\} \cup \{(e', r, e) \in \mathcal{T} : e' \in \mathcal{E}\}
\end{equation}
This captures all triples where entity $e$ appears as either subject or object, providing immediate context for simple factual questions.
\emph{Operational semantics:} Typical answer type is an entity or short string (e.g., "Who wrote $e$?", "What team does $e$ play for?"). Retrieval unit is an individual triple; ranking favors relation priors and entity-degree penalties. Failure modes include hub entities; we mitigate with degree caps and relation filtering.

\textbf{Two-hop Subgraphs ($\mathcal{G}_2$)}: For entities connected through intermediate entities, we define:
\begin{equation}
\mathcal{G}_2(e_1, e_3) = \{(e_1, r_1, e_2), (e_2, r_2, e_3) : e_2 \in \mathcal{E}, r_1, r_2 \in \mathcal{R}\}
\end{equation}
To manage computational complexity, we implement degree-based filtering and relation filtering to avoid high-degree hub nodes and prioritize semantically meaningful relation combinations.
\emph{Operational semantics:} Typical answer type is an entity derived from a length-2 path (e.g., "Which \emph{director}'s \emph{film} stars $e$?" or "Which \emph{city} hosts the \emph{team} $e$ plays for?"). Retrieval unit is a constrained path (two edges). We apply PMI-informed relation whitelists and beam expansion with compatibility checks.

\textbf{Literal Subgraphs ($\mathcal{G}_L$)}: These contain numerical, temporal, and categorical properties:
\begin{equation}
\mathcal{G}_L(e) = \{(e, r, l) : r \in \mathcal{R}_{literal}, l \in \mathcal{L}\}
\end{equation}
\emph{Operational semantics:} Typical answer types are numbers, dates, or categorical strings (e.g., "When was $e$ born?", "What is the population of $e$?"). Retrieval unit is a literal-bearing triple. We handle normalization (units, date formats) and apply diversity penalties to avoid near-duplicate properties.

\textbf{Description Subgraphs ($\mathcal{G}_D$)}: These provide textual context through entity descriptions:
\begin{equation}
\mathcal{G}_D(e) = \{(e, \text{description}, d) : d \in \mathcal{D}\}
\end{equation}
\emph{Operational semantics:} Typical usage is definition or background queries, disambiguation, or attribute extraction not captured as structured literals (e.g., "What is $e$?", "Describe $e$'s role"). Retrieval unit is a short description span with lexical cues; we down-weight long passages via length penalties.

\begin{table}[t]
\centering
\caption{Label taxonomy and retrieval characteristics.}
\label{tab:label_taxonomy}
\begin{adjustbox}{max width=\columnwidth}
\begin{tabular}{l l l l}
\toprule
Label & Retrieval unit & Expected answer type & Common cues \\
\midrule
One-Hop & Triple $(h,r,t)$ & Entity / short string & who/where/of/for/"$r$ of $e$" \\
Two-Hop & Path $(h,r_1,m),(m,r_2,t)$ & Entity & that/which chains, role indirection \\
Literal & $(e,r,l)$ with $l$ literal & Number / date / category & when/how many/how long/age/population \\
Description & $(e,\text{description},d)$ & Short text span & what is/define/describe/background \\
Composites & Union per labels & Mixed & combined cues (e.g., when + who) \\
\bottomrule
\end{tabular}
\end{adjustbox}
\end{table}

\subsection{Multi-Label Question Type Classification}

We employ a fine-tuned SentenceTransformer model $f_\theta$ that maps questions to dense vector representations optimized for multi-label classification. This pre-classification approach narrows retrieval before expansion, reducing irrelevant edges and aligning with calls for explicit subgraph construction for faithful reasoning \cite{luo2023reasoning}. Unlike iterative agent frameworks (Think-on-Graph \cite{sun2023think}, KG-Agent \cite{jiang2024kg}) that trigger additional expansion rounds, our composite labels directly trigger simultaneous attachment of literals or descriptions, avoiding second retrieval rounds.

The architecture consists of a pre-trained BERT-base encoder, mean pooling with attention weights, and a multi-layer perceptron with sigmoid activation.

For a question $q$, we compute the embedding $\mathbf{h} = f_\theta(q)$ and predict label probabilities:
\begin{equation}
\mathbf{p} = \sigma(W_2 \cdot \text{ReLU}(W_1 \mathbf{h} + b_1) + b_2)
\end{equation}

We train the classifier using a weighted binary cross-entropy loss:
\begin{equation}
\mathcal{L}_{cls} = -\frac{1}{K}\sum_{k=1}^K w_k \left[ y_k \log p_k + (1-y_k)\log (1-p_k)\right]
\end{equation}

Composite labels emerge implicitly via multi-label supervision, enabling the system to identify questions requiring multiple types of knowledge simultaneously.

\paragraph*{Label taxonomy and decision policy} We use four atomic labels (one-hop, two-hop, literal, description) and allow composites (e.g., one-hop+literal, two-hop+description). A label set $\hat{Y}$ is formed by thresholding per-class probabilities with class-specific $\tau_k$ chosen on a validation split to balance precision/recall. To prevent over-attachment, we cap the number of active labels to a small $M$ via top-$M$ probability truncation. Each active label allocates an independent retrieval budget, ensuring balanced evidence under a fixed token cap.

\subsection{Label-Conditioned Subgraph Retrieval}

Given predicted question labels $\hat{Y} = \{y_k : p_k > \tau_{thresh}\}$, we implement a sophisticated retrieval pipeline that employs a lexical-first BM25 layer with light embedding re-ranking, eliminating GNN message passing latency required in GNN-RAG \cite{mavromatis2024gnn} while preserving semantic sensitivity via secondary cosine scoring:

1) \textbf{Seed Extraction}: Multi-stage entity linking using NER, surface form matching, and embedding-based linking with disambiguation.

2) \textbf{Coarse Retrieval}: Union of label-matched subgraph shards for each seed entity based on predicted question types.

3) \textbf{Two-Hop Expansion}: Controlled fan-out using beam search, relation filtering, and entity type constraints.

4) \textbf{Literal/Description Attachment}: Type-aware filtering based on expected answer types and semantic similarity.

\textbf{Lexical BM25 Layer:} We build separate BM25 indices over: (i) triple string forms "[head] [relation] [tail]" for relational shards, (ii) literal property strings, (iii) entity descriptions. For each predicted label class we issue compact queries (original question + normalized entity surface forms + relation cue terms extracted via POS / dependency patterns). This yields low-latency candidate pools per granularity. 
\textbf{Hybrid Re-Ranking:} The union candidate set is re-ranked by a hybrid score: $s_{hyb} = \alpha \cdot s_{bm25} + (1-\alpha)\cdot \cos(\mathbf{h}_q,\mathbf{h}_c)$ where $\mathbf{h}_c$ is a sentence-transformer embedding of the candidate textualization. Only the top-$k_g$ per granularity $g$ pass to structural expansion, ensuring balanced evidence diversity.
\textbf{Structured Expansion:} For two-hop labels we perform constrained beam expansion seeded by highest-scoring one-hop edges sharing entities linked from BM25 stage, applying relation whitelist heuristics (frequency-adjusted PMI) and degree caps.
\textbf{Why BM25 First?} Empirically this cuts candidate generation latency versus dense-only or GNN encoders by avoiding initial embedding or message-passing overhead while retaining high recall for factoid lexical triggers; dense similarity is applied only to a pruned pool.

\subsection{Filtering \& Regularization}

We score candidate triples $t$ with a combined structural and semantic score that uses interpretable structural priors instead of learned graph encoders (e.g., GNN-RAG \cite{mavromatis2024gnn}), improving faithfulness and traceability consistent with faithful reasoning principles \cite{luo2023reasoning}:

\begin{align}
s(t) = &\lambda_{sim} \cdot \cos(\mathbf{h}_q, \mathbf{h}_t) + \lambda_{deg} \cdot g(\text{degree}(e_t)) \\
&+ \lambda_{rel} \cdot p(r_t) + \lambda_{type} \cdot \text{type\_compat}(t, q) \\
&- \lambda_{len} \cdot \text{length\_penalty}(t)
\end{align}

where $\mathbf{h}_q$ and $\mathbf{h}_t$ are embeddings of question and triple, $g(\cdot)$ penalizes high-degree entities, $p(r_t)$ is the prior probability of relation $r_t$, and pattern filters ensure compatibility with question semantics.

We extend $s(t)$ by prepending the BM25 component already integrated at candidate selection; no GNN structural embedding term is needed, preserving latency. An optional pairwise diversity penalty discourages near-duplicate literal properties while maintaining coverage of distinct relation types.

\subsection{Prompt Construction and LLM Integration}

Our prompt template consists of carefully designed components: task description, question context, predicted labels, structured knowledge table, reasoning guidelines, and output format specification. We implement intelligent token budget allocation with 64\% allocated to the knowledge table, 12\% each to question and instructions, and remaining tokens distributed among other components.

\subsection{Grounded Decoding}

We apply constrained decoding with entity whitelisting, relation soft guidance, and literal verification to ensure generated answers remain faithful to retrieved knowledge while maintaining fluency. We combine entity whitelisting and soft relation guidance with citation alignment, unlike GCR \cite{luo2024graph} which enforces entity validity but lacks fine-grained granularity-aware evidence budgeting, and agent/iterative planners \cite{jiang2024kg,sun2023think} which add latency via planning loops.
For fine-tuned models, we optimize a joint objective combining answer generation loss, rationale loss, citation loss, and consistency regularization:
\begin{equation}
\mathcal{L}_{total} = \mathcal{L}_{answer} + \alpha \mathcal{L}_{rationale} + \beta \mathcal{L}_{citation} + \gamma \mathcal{L}_{consistency}
\end{equation}

\section{System Architecture and Implementation}

Our system implements a modular architecture designed for scalability and efficiency, with components for question processing, classification, retrieval, filtering, prompt generation, and LLM inference. We employ hierarchical storage with hot data in memory, warm data in SSD cache, and cold data on disk, along with multi-level caching strategies for different components.

\begin{figure*}[t]
\centering
\fbox{\parbox{0.9\textwidth}{\centering
\textbf{Figure Placeholder: System Architecture}\\
Flow diagram showing complete pipeline from question input to answer generation\\
Include: Question Classifier → Subgraph Retriever → Filtering Module → Prompt Constructor → LLM → Answer\\
Show parallel processing paths and data stores (KG Index, Embeddings Cache, Model Weights)
}}
\caption{System architecture showing the complete pipeline from question input to answer generation with modular design for efficient processing.}
\label{fig:architecture}
\end{figure*}

\section{Experimental Setup}

\subsection{Datasets}

We conduct comprehensive experiments on multiple benchmark datasets:

\begin{table}[t]
\centering
\caption{Dataset statistics and characteristics.}
\label{tab:dataset_stats}
\begin{adjustbox}{max width=\columnwidth}
\begin{tabular}{lrrrr}
\toprule
Dataset & Train & Dev & Test & Avg Q Len \\
\midrule
WebQSP & 3,098 & 1,639 & 1,639 & 6.4 \\
ComplexWebQuestions & 27,639 & 3,519 & 3,531 & 10.8 \\
MetaQA & 96,106 & 9,992 & 9,947 & 7.2 \\
LC-QuAD 2.0 & 19,293 & 2,472 & 4,781 & 8.9 \\
\bottomrule
\end{tabular}
\end{adjustbox}
\end{table}

\subsection{Baselines}

We compare against several state-of-the-art baselines: (1) Zero-shot LLaMA-3-8B, (2) Few-shot LLaMA-3-8B, (3) Text RAG + LLaMA-3, (4) GNN-RAG, (5) Think-on-Graph, (6) KG-Agent, (7) Graph-Constrained Reasoning, along with our variants (zero-shot and fine-tuned).

\subsection{Metrics}

We evaluate using answer quality metrics (Exact Match, F1, Hits@1/5), reasoning quality metrics (Multi-hop Accuracy, Faithfulness Score, Citation Accuracy), efficiency metrics (latency, memory usage), and retrieval quality metrics (Recall@K, Evidence Precision).

\subsection{Implementation Details}

\textbf{Question Classifier}: sentence-transformers/all-MiniLM-L6-v2 base with 768→256→128 hidden dimensions, dropout 0.1, learning rate 2e-5.

\textbf{Language Model}: meta-llama/Llama-3-8B-Instruct (zero-shot), meta-llama/Llama-3-3B (fine-tuned), context length 4096, temperature 0.1.

\textbf{Training}: Batch size 32 (classification), 4 with gradient accumulation (LLM), AdamW optimizer with weight decay 0.01.

\section{Results}

\subsection{Overall Performance}

\begin{table*}[t]
\centering
\caption{Main experimental results across datasets and baselines. Best results in bold, second-best underlined.}
\label{tab:qa_perf}
\begin{tabular}{llcccccc}
\toprule
\multirow{2}{*}{Model} & \multirow{2}{*}{Dataset} & \multicolumn{3}{c}{Answer Quality} & \multicolumn{2}{c}{Reasoning} & Efficiency \\
& & EM & F1 & Hits@1 & Multi-hop Acc & Faithfulness & Latency (ms) \\
\midrule
\multirow{3}{*}{Zero-shot LLaMA-3-8B} & WebQSP & 42.3 & 47.8 & 51.2 & 35.1 & 23.4 & 234 \\
& ComplexWebQuestions & 28.9 & 34.2 & 38.7 & 22.1 & 18.9 & 267 \\
& MetaQA & 51.7 & 56.3 & 62.1 & 41.2 & 31.2 & 198 \\
\midrule
\multirow{3}{*}{Text RAG + LLaMA-3} & WebQSP & 48.7 & 53.9 & 57.3 & 41.2 & 67.8 & 523 \\
& ComplexWebQuestions & 33.4 & 39.1 & 43.8 & 28.7 & 61.3 & 587 \\
& MetaQA & 57.2 & 62.8 & 67.9 & 48.3 & 72.1 & 445 \\
\midrule
\multirow{3}{*}{Think-on-Graph} & WebQSP & 54.3 & 60.1 & 63.8 & 49.2 & 81.4 & 1,124 \\
& ComplexWebQuestions & 41.2 & 47.3 & 51.6 & 37.5 & 76.8 & 1,287 \\
& MetaQA & 65.8 & 71.2 & 74.9 & 58.1 & 84.2 & 989 \\
\midrule
\multirow{3}{*}{KG-Agent} & WebQSP & 56.7 & 62.3 & 66.1 & 51.8 & 79.6 & 1,456 \\
& ComplexWebQuestions & 43.9 & 49.8 & 54.2 & 40.3 & 74.5 & 1,623 \\
& MetaQA & 68.1 & 73.4 & 77.2 & 61.4 & 81.7 & 1,234 \\
\midrule
\multirow{3}{*}{\textbf{Ours (Zero-shot)}} & WebQSP & \underline{64.2} & \underline{69.7} & \underline{72.4} & \underline{58.3} & \underline{86.7} & \underline{687} \\
& ComplexWebQuestions & \underline{51.7} & \underline{57.2} & \underline{61.8} & \underline{47.9} & \underline{83.4} & \underline{743} \\
& MetaQA & \underline{74.6} & \underline{79.1} & \underline{82.3} & \underline{67.8} & \underline{89.2} & \underline{623} \\
\midrule
\multirow{3}{*}{\textbf{Ours (Fine-tuned)}} & WebQSP & \textbf{67.9} & \textbf{73.1} & \textbf{75.8} & \textbf{62.1} & \textbf{91.3} & \textbf{592} \\
& ComplexWebQuestions & \textbf{55.4} & \textbf{60.8} & \textbf{65.2} & \textbf{51.6} & \textbf{87.9} & \textbf{634} \\
& MetaQA & \textbf{78.3} & \textbf{82.7} & \textbf{85.9} & \textbf{71.2} & \textbf{92.8} & \textbf{567} \\
\bottomrule
\end{tabular}
\end{table*}

Our approach demonstrates consistent and significant improvements across all evaluation metrics. The fine-tuned model achieves 15.3\% average improvement in exact match accuracy compared to the best baseline, with particularly strong performance on complex multi-hop questions.

\subsection{Question Type Breakdown}

\begin{table}[t]
\centering
\caption{Performance by predicted question type on WebQSP.}
\label{tab:type_breakdown}
\begin{tabular}{lrcc}
\toprule
Type & Count & EM & F1 \\
\midrule
One-Hop & 1,247 & 78.4 & 82.1 \\
Two-Hop & 892 & 62.3 & 67.9 \\
Literal & 523 & 71.6 & 76.8 \\
Description & 187 & 55.1 & 61.3 \\
One-Hop+Literal & 498 & 69.3 & 74.7 \\
Two-Hop+Description & 18 & 44.4 & 50.0 \\
\bottomrule
\end{tabular}
\end{table}

Questions with composite labels show substantial improvements, validating our multi-label classification approach.

\subsection{Ablation Studies}

\begin{table}[t]
\centering
\caption{Ablation study results on WebQSP dataset.}
\label{tab:retrieval_ablation}
\begin{tabular}{lcccc}
\toprule
Configuration & EM & F1 & Multi-hop Acc & Faithfulness \\
\midrule
Full Model & \textbf{67.9} & \textbf{73.1} & \textbf{62.1} & \textbf{91.3} \\
- Multi-label Classification & 62.4 & 67.8 & 55.7 & 87.9 \\
- Advanced Filtering & 64.1 & 69.2 & 58.3 & 86.2 \\
- Composite Labels & 61.8 & 67.1 & 54.9 & 86.8 \\
- Two-hop Subgraphs & 59.7 & 65.4 & 48.2 & 88.7 \\
Single-label Classification & 58.3 & 63.9 & 50.1 & 84.2 \\
No Filtering & 55.7 & 61.2 & 46.8 & 78.9 \\
\bottomrule
\end{tabular}
\end{table}

The ablation studies reveal that multi-label classification contributes 5.5 points to exact match, advanced filtering adds 3.8 points, and composite labels provide 6.1 points improvement over single-label approaches.

\subsection{Latency Analysis}

\begin{table}[t]
\centering
\caption{Detailed latency breakdown for our approach.}
\label{tab:latency}
\begin{tabular}{lrr}
\toprule
Stage & Time (ms) & Percentage \\
\midrule
Question Preprocessing & 23 & 3.9\% \\
Multi-label Classification & 47 & 7.9\% \\
Entity Linking & 89 & 15.0\% \\
Subgraph Retrieval & 156 & 26.4\% \\
Filtering \& Ranking & 134 & 22.6\% \\
Prompt Construction & 31 & 5.2\% \\
LLM Inference & 98 & 16.6\% \\
Post-processing & 14 & 2.4\% \\
\midrule
Total & 592 & 100.0\% \\
\bottomrule
\end{tabular}
\end{table}

The latency analysis shows a well-balanced pipeline with no single component dominating processing time.

\begin{figure}[t]
\centering
\fbox{\parbox{0.45\textwidth}{\centering
\textbf{Figure Placeholder: Classification Performance}\\
Confusion matrix for multi-label question typing\\
Show precision/recall for each question type\\
Include composite label performance
}}
\caption{Multi-label question type classification performance showing high accuracy across all question types.}
\label{fig:confusion}
\end{figure}

\begin{figure}[t]
\centering
\fbox{\parbox{0.45\textwidth}{\centering
\textbf{Figure Placeholder: Reasoning Example}\\
End-to-end reasoning chain visualization\\
Show question → classification → retrieval → filtering → answer\\
Include cited triples and reasoning steps
}}
\caption{Qualitative example of end-to-end reasoning with transparent citation of knowledge sources.}
\label{fig:qualitative}
\end{figure}

\subsection{Retrieval Efficiency Comparison}
Table \ref{tab:retrieval_speed} contrasts retrieval characteristics. For multi-stage methods we isolate pure retrieval + filtering (excluding generation). Our approach shows markedly lower structural encoding overhead while keeping competitive end-to-end latency due to early granularity pruning.

\begin{table}[t]
\centering
\caption{Retrieval efficiency comparison. Retrieval latency = candidate generation + structural expansion + filtering. End-to-end latency from question input to final answer (reported earlier for baselines). Memory footprint excludes base LLM weights.}
\label{tab:retrieval_speed}
\begin{adjustbox}{max width=\columnwidth}
\begin{tabular}{lcccc}
\toprule
Method & Paradigm & Retrieval Lat. (ms) & End2End (ms) & Mem (GB) \\
\midrule
Text RAG + LLaMA-3 & BM25 + dense passages & 180 & 523 & 2.1 \\
GNN-RAG & GNN-enhanced graph enc. & 420 & 1,050 & 6.4 \\
Think-on-Graph & Iterative expand (multi-step) & 650 & 1,124 & 3.8 \\
KG-Agent & Plan-act loops & 780 & 1,456 & 4.2 \\
Graph-Constrained Reasoning & Lexical + constraint decode & 260 & 1,010 & 2.7 \\
Ours (Zero-shot) & Multi-granular BM25 + hybrid & 290 & 687 & 2.5 \\
Ours (Fine-tuned) & Same retriever + tuned decode & 290 & 592 & 2.5 \\
\bottomrule
\end{tabular}
\end{adjustbox}
\end{table}

\section{Analysis and Discussion}

Our experimental results demonstrate several key insights: (i) Multi-granular decomposition provides targeted retrieval that significantly improves performance across all question types; (ii) Composite label classification enables precise identification of questions requiring multiple knowledge types; (iii) Advanced filtering substantially improves faithfulness while maintaining answer quality; (iv) The framework achieves superior performance while maintaining competitive efficiency compared to existing approaches.

The multi-label classification approach with composite labels proves crucial for system performance, with questions requiring multiple knowledge types showing the largest improvements. This validates our hypothesis that real-world questions often require composite reasoning patterns that cannot be captured by single-label approaches.

\subsection{Comparative Analysis with Referenced Methods}
\textbf{Granularity Selection:} Prior methods either retrieve large undifferentiated neighborhoods (GNN-RAG \cite{mavromatis2024gnn}, Graph-Constrained Reasoning (GCR) \cite{luo2024graph}) or rely on iterative exploration (KG-Agent \cite{jiang2024kg}, Think-on-Graph \cite{sun2023think}). Our multi-label classifier (situated within the taxonomy summarized by \cite{jin2024large}) narrows retrieval \emph{before} expansion, reducing irrelevant edges and aligning with calls for explicit subgraph construction for faithful reasoning \cite{luo2023reasoning}.
\textbf{Retrieval Mechanism:} We employ a lexical-first BM25 layer for triple / literal / description shards with light embedding re-ranking—eliminating GNN message passing latency required in GNN-RAG \cite{mavromatis2024gnn} while preserving semantic sensitivity via secondary cosine scoring.
\textbf{Composite Reasoning Types:} Composite labels (e.g., one-hop+literal) unify evidence attachment in a single pass; iterative / agent frameworks (Think-on-Graph \cite{sun2023think}, KG-Agent \cite{jiang2024kg}) typically trigger additional expansion rounds, and GCR \cite{luo2024graph} focuses on structural validity during decoding rather than pre-retrieval granularity prediction.
\textbf{Filtering Strategy:} Instead of learned graph encoders (e.g., GNN-RAG \cite{mavromatis2024gnn}), we use interpretable structural priors (degree penalty, relation prior, type compatibility) plus diversity regularization, improving faithfulness and traceability consistent with faithful reasoning principles in \cite{luo2023reasoning}.
\textbf{Decoding Constraints:} We combine entity whitelisting and soft relation guidance with citation alignment; GCR \cite{luo2024graph} enforces entity validity but lacks fine-grained granularity-aware evidence budgeting; agent / iterative planners \cite{jiang2024kg,sun2023think} add latency via planning loops.
\textbf{Efficiency Trade-off:} Table \ref{tab:retrieval_speed} shows our retrieval latency sits far below iterative / GNN-heavy methods \cite{mavromatis2024gnn,jiang2024kg,sun2023think} while delivering higher EM / F1 (Table \ref{tab:qa_perf}), validating that early granularity classification plus lexical-first retrieval is an advantageous latency-quality operating point.
\textbf{Maintainability:} BM25 indices and shard inventories can be incrementally updated without re-training structural encoders (contrasting with GNN-based retrievers \cite{mavromatis2024gnn}), simplifying KG refresh cycles.

\section{Limitations}

Our approach has several limitations: (1) Reliance on knowledge graph coverage limits performance on questions requiring facts not present in the KG; (2) Potential misclassification for paraphrased complex queries may lead to suboptimal retrieval; (3) Prompt length constraints limit the amount of evidence that can be included; (4) Limited handling of temporal knowledge drift requires periodic KG updates; (5) Scalability beyond two-hop expansions requires more sophisticated pruning strategies.

We note that while BM25-first improves latency, purely lexical anchoring can miss paraphrastic or low-overlap questions; hybrid dense-first variants are future work.

\section{Ethical Considerations}

Our focus on factual grounding through knowledge graphs aims to reduce hallucination and improve reliability. However, there is risk of propagating biases present in the underlying knowledge graph. We mitigate this through provenance citation and differential auditing mechanisms. All experiments use publicly available benchmark datasets without processing personally identifiable information.

\section{Conclusion and Future Work}

We presented a comprehensive multi-granular knowledge graph enhanced framework for large language models that significantly improves performance on knowledge-intensive question answering tasks. Our approach introduces novel techniques for KG decomposition, composite question classification, and sophisticated retrieval with filtering. Extensive experiments demonstrate consistent improvements across multiple datasets and metrics while maintaining computational efficiency.

Future research directions include: adaptive multi-hop expansion beyond two hops, integration of temporal knowledge graphs for handling time-sensitive queries, multi-modal evidence fusion combining structured and unstructured knowledge sources, and development of robust continual learning mechanisms for dynamic knowledge graph updates.

% ----------------------------
% Bibliography
% ----------------------------
\bibliographystyle{IEEEtran}
\bibliography{ref}

\end{document}
·
After reading my paper, try to implement the whole idea under folder: KG-LLM-NEW. Some ideas might be not professional or not adequet, adjust those inproper ideas and follow whatever's the best choice or best idea if necessary and tell me your adjustments(or write it down in markdown with reference to parts of the ideas in the paper). Make sure you don't just implement it blindly you also have to find logic flaws, or pipeline defects and replenish those holes. Use the LLM from llamacpp_mqtt_deploy.py, allow two options: "use llm from llama-server url" or "use llm with mqtt broker". The project you implement must be thoroughly planned and accomplished while easy to read and maintain in the future for me or other coders. It's important that you work longer to guarantee quality of your implementation. Use youro ROG ability or online tools if possible. 

only select high threshold results from classifer otherwise skip classification.