"""Parse the Cranfield corpus and index it in Elasticsearch.

Run with:
    python -m src.CreateIndex
"""
from __future__ import annotations

import sys
from pathlib import Path

# Allow running both as `python -m src.CreateIndex` and `python src/CreateIndex.py`
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from elasticsearch.helpers import bulk
from tqdm import tqdm

from config import CORPUS_FILE, INDEX_NAME
from src.utils import get_es_client, parse_cranfield_corpus


# ---------------------------------------------------------------------------
# Index settings — enable term vectors + positions so we can pull TF later.
# ---------------------------------------------------------------------------
INDEX_SETTINGS = {
    "settings": {
        "number_of_shards": 1,
        "number_of_replicas": 0,
        "analysis": {
            "analyzer": {
                "stopped": {
                    "type": "custom",
                    "tokenizer": "standard",
                    "filter": ["lowercase", "english_stop"],
                }
            },
            "filter": {
                "english_stop": {
                    "type": "stop",
                    "stopwords": "_english_",
                }
            },
        },
    },
    "mappings": {
        "properties": {
            "docno": {"type": "keyword"},
            "title": {"type": "text", "analyzer": "stopped"},
            "author": {"type": "text", "analyzer": "stopped"},
            "biblio": {"type": "text", "analyzer": "stopped"},
            "body_text": {
                "type": "text",
                "analyzer": "stopped",
                "term_vector": "with_positions_offsets_payloads",
                "store": True,
                "fielddata": True,
            },
        }
    },
}


def create_index(es) -> None:
    if es.indices.exists(index=INDEX_NAME):
        print(f"[CreateIndex] Deleting existing index '{INDEX_NAME}'")
        es.indices.delete(index=INDEX_NAME)
    print(f"[CreateIndex] Creating index '{INDEX_NAME}'")
    es.indices.create(index=INDEX_NAME, **INDEX_SETTINGS)


def actions(corpus_path: Path):
    for doc in parse_cranfield_corpus(corpus_path):
        yield {
            "_op_type": "index",
            "_index": INDEX_NAME,
            "_id": doc["docno"],
            "_source": doc,
        }


def main() -> None:
    if not CORPUS_FILE.exists():
        raise SystemExit(
            f"Corpus file not found: {CORPUS_FILE}\n"
            "Place 'cran.all.1400' inside the data/ directory."
        )

    es = get_es_client()
    create_index(es)

    print(f"[CreateIndex] Bulk-indexing documents from {CORPUS_FILE} ...")
    success, errors = bulk(
        es,
        tqdm(actions(CORPUS_FILE), desc="indexing"),
        chunk_size=500,
        request_timeout=120,
    )
    es.indices.refresh(index=INDEX_NAME)

    count = es.count(index=INDEX_NAME)["count"]
    print(f"[CreateIndex] Done. Indexed {success} docs (errors={len(errors) if isinstance(errors, list) else errors}).")
    print(f"[CreateIndex] Index '{INDEX_NAME}' now contains {count} documents.")


if __name__ == "__main__":
    main()
