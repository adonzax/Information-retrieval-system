"""Manual implementations of the five retrieval models required for HW1.

All models use TF / DF statistics pulled from Elasticsearch (not its built-in
scoring). The ES built-in `match` query is implemented separately in
Query_Processing.py.

Models implemented here:
    * Okapi TF
    * TF-IDF
    * Okapi BM25
    * Unigram LM with Laplace smoothing
    * Unigram LM with Jelinek-Mercer smoothing
"""
from __future__ import annotations

import math
from collections import Counter, defaultdict
from typing import Dict, List, Tuple

from elasticsearch import Elasticsearch

from config import (
    INDEX_NAME,
    BM25_K1,
    BM25_K2,
    BM25_B,
    LM_JM_LAMBDA,
)


# ---------------------------------------------------------------------------
# Corpus-level statistics  (computed once and reused by every query)
# ---------------------------------------------------------------------------
class CorpusStats:
    """Holds D, V, avg(len(d)), and per-document length, plus a cf cache."""

    def __init__(self, es: Elasticsearch, field: str = "body_text"):
        self.es = es
        self.field = field

        # D = number of docs
        self.D: int = es.count(index=INDEX_NAME)["count"]

        # Vocabulary size + total token length of the field, via _stats API.
        # We use indices.stats for total_term_freq via term_vectors below; for V
        # we rely on the field's unique-terms count by aggregating term vectors
        # of all docs (small corpus -> fine for Cranfield).
        self.doc_len: Dict[str, int] = {}
        self.total_len: int = 0
        self.cf: Dict[str, int] = {}      # collection frequency per term
        self.df_cache: Dict[str, int] = {}

        self._bootstrap()
        self.V: int = len(self.cf)
        self.avg_len: float = self.total_len / max(self.D, 1)

    # ------------------------------------------------------------------ #
    def _bootstrap(self) -> None:
        """One scan over the index to compute lengths + collection frequencies."""
        # Pull every doc id (Cranfield is small: 1400 docs)
        resp = self.es.search(
            index=INDEX_NAME,
            query={"match_all": {}},
            _source=False,
            size=10_000,
        )
        ids = [hit["_id"] for hit in resp["hits"]["hits"]]

        # mtermvectors is the fastest way to get TF + length for all docs
        body = {
            "ids": ids,
            "parameters": {
                "fields": [self.field],
                "term_statistics": True,
                "field_statistics": True,
                "offsets": False,
                "positions": False,
                "payloads": False,
            },
        }
        mtv = self.es.mtermvectors(index=INDEX_NAME, body=body)

        for d in mtv["docs"]:
            docno = d["_id"]
            tv = d.get("term_vectors", {}).get(self.field)
            if not tv:
                self.doc_len[docno] = 0
                continue
            terms = tv["terms"]
            length = sum(t["term_freq"] for t in terms.values())
            self.doc_len[docno] = length
            self.total_len += length
            for term, info in terms.items():
                self.cf[term] = self.cf.get(term, 0) + info["term_freq"]
                # ttf / doc_freq are corpus-wide, take max (same value across docs)
                if "doc_freq" in info:
                    prev = self.df_cache.get(term, 0)
                    if info["doc_freq"] > prev:
                        self.df_cache[term] = info["doc_freq"]

    # ------------------------------------------------------------------ #
    def df(self, term: str) -> int:
        return self.df_cache.get(term, 0)

    def collection_freq(self, term: str) -> int:
        return self.cf.get(term, 0)


# ---------------------------------------------------------------------------
# Per-query helpers
# ---------------------------------------------------------------------------
def analyze_query(es: Elasticsearch, text: str, field: str = "body_text") -> List[str]:
    """Run the query through the same analyzer used at index time."""
    resp = es.indices.analyze(index=INDEX_NAME, field=field, text=text)
    return [tok["token"] for tok in resp["tokens"]]


def fetch_postings(
    es: Elasticsearch,
    term: str,
    field: str = "body_text",
) -> Dict[str, int]:
    """Return {docno: tf} for every document containing `term`."""
    postings: Dict[str, int] = {}
    # Use a `term` query to find candidate docs, then read TF from term vectors.
    resp = es.search(
        index=INDEX_NAME,
        query={"term": {field: term}},
        _source=False,
        size=10_000,
    )
    ids = [h["_id"] for h in resp["hits"]["hits"]]
    if not ids:
        return postings

    body = {
        "ids": ids,
        "parameters": {
            "fields": [field],
            "term_statistics": False,
            "field_statistics": False,
            "offsets": False,
            "positions": False,
            "payloads": False,
        },
    }
    mtv = es.mtermvectors(index=INDEX_NAME, body=body)
    for d in mtv["docs"]:
        tv = d.get("term_vectors", {}).get(field)
        if not tv:
            continue
        info = tv["terms"].get(term)
        if info:
            postings[d["_id"]] = info["term_freq"]
    return postings


# ---------------------------------------------------------------------------
# Scoring functions.  All return  Dict[docno, score].
# ---------------------------------------------------------------------------
def okapi_tf_term(tf: int, doc_len: int, avg_len: float) -> float:
    if tf == 0:
        return 0.0
    return tf / (tf + 0.5 + 1.5 * (doc_len / avg_len))


def score_okapi_tf(
    es: Elasticsearch,
    stats: CorpusStats,
    query_terms: List[str],
) -> Dict[str, float]:
    scores: Dict[str, float] = defaultdict(float)
    for term in set(query_terms):
        for docno, tf in fetch_postings(es, term).items():
            scores[docno] += okapi_tf_term(tf, stats.doc_len[docno], stats.avg_len)
    return scores


def score_tfidf(
    es: Elasticsearch,
    stats: CorpusStats,
    query_terms: List[str],
) -> Dict[str, float]:
    scores: Dict[str, float] = defaultdict(float)
    for term in set(query_terms):
        df = stats.df(term)
        if df == 0:
            continue
        idf = math.log(stats.D / df)
        for docno, tf in fetch_postings(es, term).items():
            scores[docno] += okapi_tf_term(tf, stats.doc_len[docno], stats.avg_len) * idf
    return scores


def score_bm25(
    es: Elasticsearch,
    stats: CorpusStats,
    query_terms: List[str],
) -> Dict[str, float]:
    scores: Dict[str, float] = defaultdict(float)
    qtf = Counter(query_terms)
    for term, tfwq in qtf.items():
        df = stats.df(term)
        if df == 0:
            continue
        idf = math.log((stats.D + 0.5) / (df + 0.5))
        q_part = (tfwq + BM25_K2 * tfwq) / (tfwq + BM25_K2)
        for docno, tf in fetch_postings(es, term).items():
            dl = stats.doc_len[docno]
            denom = tf + BM25_K1 * ((1 - BM25_B) + BM25_B * (dl / stats.avg_len))
            d_part = (tf + BM25_K1 * tf) / denom
            scores[docno] += idf * d_part * q_part
    return scores


def score_lm_laplace(
    es: Elasticsearch,
    stats: CorpusStats,
    query_terms: List[str],
) -> Dict[str, float]:
    """log-sum of (tf+1)/(len(d)+V).  Computed for every document in the corpus."""
    V = stats.V
    # Pre-fetch postings for each unique query term
    postings_by_term = {t: fetch_postings(es, t) for t in set(query_terms)}

    scores: Dict[str, float] = {}
    for docno, dl in stats.doc_len.items():
        s = 0.0
        for term in query_terms:
            tf = postings_by_term[term].get(docno, 0)
            s += math.log((tf + 1) / (dl + V))
        scores[docno] = s
    return scores


def score_lm_jm(
    es: Elasticsearch,
    stats: CorpusStats,
    query_terms: List[str],
    lam: float = LM_JM_LAMBDA,
) -> Dict[str, float]:
    """log-sum of  lambda*tf/len(d) + (1-lambda)*cf/total_len."""
    total_len = stats.total_len
    postings_by_term = {t: fetch_postings(es, t) for t in set(query_terms)}

    scores: Dict[str, float] = {}
    for docno, dl in stats.doc_len.items():
        s = 0.0
        skip_doc = False
        for term in query_terms:
            tf = postings_by_term[term].get(docno, 0)
            cf = stats.collection_freq(term)
            fg = (tf / dl) if dl > 0 else 0.0
            bg = (cf / total_len) if total_len > 0 else 0.0
            p = lam * fg + (1 - lam) * bg
            if p <= 0:
                # OOV term — skip to avoid log(0). With JM this should be rare
                # because background prob is nonzero for any in-vocab term.
                skip_doc = True
                break
            s += math.log(p)
        if not skip_doc:
            scores[docno] = s
    return scores


# ---------------------------------------------------------------------------
# Public registry used by Query_Processing.py
# ---------------------------------------------------------------------------
MODELS = {
    "okapi_tf":   score_okapi_tf,
    "tfidf":      score_tfidf,
    "bm25":       score_bm25,
    "lm_laplace": score_lm_laplace,
    "lm_jm":      score_lm_jm,
}


def top_k(scores: Dict[str, float], k: int) -> List[Tuple[str, float]]:
    """Return the k highest-scoring (docno, score) tuples."""
    items = [(d, s) for d, s in scores.items() if s != 0.0]
    items.sort(key=lambda x: x[1], reverse=True)
    return items[:k]
