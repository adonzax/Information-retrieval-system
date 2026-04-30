"""Run all six retrieval models over cran.qry and write TREC-format runs.

Run with:
    python -m src.Query_Processing
"""
from __future__ import annotations

import sys
from collections import defaultdict
from pathlib import Path
from typing import Dict, List, Tuple

# Allow running both as a module and a script
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tqdm import tqdm

from config import INDEX_NAME, OUTPUT_DIR, QUERY_FILE, TOP_K
from src.Retrieval_Models import (
    MODELS,
    CorpusStats,
    analyze_query,
    top_k,
)
from src.utils import get_es_client, parse_cranfield_queries, write_trec_run


# ---------------------------------------------------------------------------
# Elasticsearch built-in `match` (BM25-ish) — model #1
# ---------------------------------------------------------------------------
def es_builtin_search(es, query_text: str, k: int) -> List[Tuple[str, float]]:
    resp = es.search(
        index=INDEX_NAME,
        query={"match": {"body_text": query_text}},
        size=k,
        _source=False,
    )
    return [(hit["_id"], hit["_score"]) for hit in resp["hits"]["hits"]]


# ---------------------------------------------------------------------------
# Driver
# ---------------------------------------------------------------------------
def main() -> None:
    if not QUERY_FILE.exists():
        raise SystemExit(
            f"Query file not found: {QUERY_FILE}\n"
            "Place 'cran.qry' inside the data/ directory."
        )

    es = get_es_client()

    print("[Query_Processing] Loading corpus statistics from Elasticsearch ...")
    stats = CorpusStats(es)
    print(f"  D = {stats.D}    V = {stats.V}    avg(len(d)) = {stats.avg_len:.2f}")

    queries = parse_cranfield_queries(QUERY_FILE)
    print(f"[Query_Processing] Loaded {len(queries)} queries from {QUERY_FILE.name}")

    # results[model][qid] = [(docno, score), ...]
    results: Dict[str, Dict[str, List[Tuple[str, float]]]] = {
        name: defaultdict(list) for name in (["es_builtin"] + list(MODELS.keys()))
    }

    for qid, qtext in tqdm(queries, desc="queries"):
        if not qtext.strip():
            continue

        # 1) ES built-in
        results["es_builtin"][qid] = es_builtin_search(es, qtext, TOP_K)

        # 2..6) Custom models — share a single analysed query
        terms = analyze_query(es, qtext)
        if not terms:
            continue

        for name, scorer in MODELS.items():
            scores = scorer(es, stats, terms)
            results[name][qid] = top_k(scores, TOP_K)

    # ---------------------------------------------------------------- write
    print(f"[Query_Processing] Writing run files to {OUTPUT_DIR}")
    for name, ranked in results.items():
        out_path = OUTPUT_DIR / f"{name}.txt"
        write_trec_run(out_path, name, ranked)
        print(f"  - {out_path}  ({sum(len(v) for v in ranked.values())} lines)")

    print("[Query_Processing] Done.")


if __name__ == "__main__":
    main()
