"""Project-wide configuration for Cranfield IR HW1."""
import os
from pathlib import Path

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
ROOT_DIR = Path(__file__).resolve().parent
DATA_DIR = ROOT_DIR / "data"
OUTPUT_DIR = ROOT_DIR / "output"

CORPUS_FILE = DATA_DIR / "cran.all.1400"
QUERY_FILE = DATA_DIR / "cran.qry"
QRELS_FILE = DATA_DIR / "cranqrel"

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# ---------------------------------------------------------------------------
# Elasticsearch
# ---------------------------------------------------------------------------
ES_HOST = os.environ.get("ES_HOST", "https://localhost:9200")
ES_USER = os.environ.get("ES_USER", "elastic")
ES_PASSWORD = os.environ.get("ES_PASSWORD", "MFZVm=cRC6mLp3FiuXp0")
# Set to False if you are using a self-signed cert in dev (default for ES 8)
ES_VERIFY_CERTS = os.environ.get("ES_VERIFY_CERTS", "false").lower() == "false"

INDEX_NAME = "cranfield"

# Number of results to return per query (assignment asks for top 100; keep room)
TOP_K = 100

# ---------------------------------------------------------------------------
# Retrieval-model hyperparameters
# ---------------------------------------------------------------------------
BM25_K1 = 1.2
BM25_K2 = 100.0
BM25_B = 0.75

LM_JM_LAMBDA = 0.6
