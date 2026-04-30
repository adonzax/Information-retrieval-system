#!/usr/bin/env bash
# End-to-end pipeline: index -> run all models -> evaluate with trec_eval.
#
# Prereqs:
#   - Elasticsearch running and reachable via env vars in config.py
#   - data/cran.all.1400, data/cran.qry, data/cranqrel present
#   - `trec_eval` on PATH
set -euo pipefail

cd "$(dirname "$0")/.."

echo "==> 1. Building Elasticsearch index"
python -m src.CreateIndex

echo "==> 2. Running all six retrieval models"
python -m src.Query_Processing

echo "==> 3. Converting cranqrel to trec_eval format"
python scripts/convert_qrels.py data/cranqrel data/cranqrel.trec

echo "==> 4. Evaluating each run with trec_eval"
for model in es_builtin okapi_tf tfidf bm25 lm_laplace lm_jm; do
    echo
    echo "----- $model -----"
    trec_eval data/cranqrel.trec "output/${model}.txt" | head -n 25
done
