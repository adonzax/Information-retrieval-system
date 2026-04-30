"""Shared helpers: Cranfield parsing and Elasticsearch client factory."""
from __future__ import annotations

import re
from pathlib import Path
from typing import Dict, Iterator, List, Tuple

from elasticsearch import Elasticsearch

from config import ES_HOST, ES_USER, ES_PASSWORD, ES_VERIFY_CERTS


# ---------------------------------------------------------------------------
# Elasticsearch
# ---------------------------------------------------------------------------
def get_es_client() -> Elasticsearch:
    """Return a configured Elasticsearch client."""
    return Elasticsearch(
        ES_HOST,
        basic_auth=(ES_USER, ES_PASSWORD),
        verify_certs=ES_VERIFY_CERTS,
        request_timeout=60,
    )


# ---------------------------------------------------------------------------
# Cranfield corpus parsing
#
# Each document looks like:
#   .I 1
#   .T
#   experimental investigation ...
#   .A
#   brenckman,m.
#   .B
#   j. ae. scs. 25, 1958, 324.
#   .W
#   experimental investigation ... (body)
# ---------------------------------------------------------------------------
_TAG_RE = re.compile(r"^\.([ITABW])(?:\s+(.*))?$")


def parse_cranfield_corpus(path: Path) -> Iterator[Dict[str, str]]:
    """Yield {'docno', 'title', 'author', 'biblio', 'body_text'} for each doc."""
    current: Dict[str, List[str]] = {}
    section: str | None = None

    def flush() -> Dict[str, str] | None:
        if not current:
            return None
        return {
            "docno": current.get("I", [""])[0].strip(),
            "title": " ".join(current.get("T", [])).strip(),
            "author": " ".join(current.get("A", [])).strip(),
            "biblio": " ".join(current.get("B", [])).strip(),
            "body_text": " ".join(current.get("W", [])).strip(),
        }

    with path.open("r", encoding="utf-8", errors="ignore") as fh:
        for raw in fh:
            line = raw.rstrip("\n")
            m = _TAG_RE.match(line)
            if m:
                tag, rest = m.group(1), m.group(2)
                if tag == "I":
                    # New document boundary -> flush previous one
                    doc = flush()
                    if doc and doc["docno"]:
                        yield doc
                    current = {"I": [rest or ""]}
                    section = None
                else:
                    section = tag
                    current.setdefault(section, [])
            else:
                if section is not None:
                    current.setdefault(section, []).append(line.strip())

    # Final document
    doc = flush()
    if doc and doc["docno"]:
        yield doc


# ---------------------------------------------------------------------------
# Cranfield query parsing
#
# Same .I / .W layout. Note: the .I numbering in cran.qry restarts at 001
# and is *not* the same as the relevance-judgement query ids, which are
# 1..225 in cranqrel. We therefore renumber sequentially as we read.
# ---------------------------------------------------------------------------
def parse_cranfield_queries(path: Path) -> List[Tuple[str, str]]:
    """Return [(query_id, query_text), ...] with sequential ids '1'..'N'."""
    queries: List[Tuple[str, str]] = []
    current_text: List[str] = []
    in_w = False
    qid = 0

    def flush():
        nonlocal current_text
        if qid > 0:
            text = " ".join(current_text).strip()
            queries.append((str(qid), text))
            current_text = []

    with path.open("r", encoding="utf-8", errors="ignore") as fh:
        for raw in fh:
            line = raw.rstrip("\n")
            m = _TAG_RE.match(line)
            if m:
                tag = m.group(1)
                if tag == "I":
                    flush()
                    qid += 1
                    in_w = False
                elif tag == "W":
                    in_w = True
                else:
                    in_w = False
            else:
                if in_w:
                    current_text.append(line.strip())
    flush()
    return queries


# ---------------------------------------------------------------------------
# TREC-style output writing
# ---------------------------------------------------------------------------
def write_trec_run(
    out_path: Path,
    run_name: str,
    ranked: Dict[str, List[Tuple[str, float]]],
) -> None:
    """Write a TREC run file: <qid> Q0 <docno> <rank> <score> <run>."""
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", encoding="utf-8") as fh:
        for qid in sorted(ranked.keys(), key=lambda x: int(x)):
            for rank, (docno, score) in enumerate(ranked[qid], start=1):
                fh.write(f"{qid} Q0 {docno} {rank} {score:.6f} {run_name}\n")
