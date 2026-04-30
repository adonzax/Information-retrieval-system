# Information Retrieval - HW1 (Cranfield Collection)

Implementation and comparison of various retrieval systems using vector space models
and language models on the **Cranfield** collection (1400 abstracts on aerodynamics)
indexed with **Elasticsearch**.

## Project Structure

```
hw1/
├── README.md
├── requirements.txt
├── config.py                    # Elasticsearch + path config
├── src/
│   ├── __init__.py
│   ├── CreateIndex.py           # Parse Cranfield corpus & index in ES
│   ├── Query_Processing.py      # Parse queries, run all models, write TREC files
│   ├── Retrieval_Models.py      # Okapi TF, TF-IDF, BM25, LM Laplace, LM JM
│   └── utils.py                 # Shared parsing / ES helpers
├── data/                        # Place cran.all.1400, cran.qry, cranqrel here
│   ├── cran.all.1400
│   ├── cran.qry
│   └── cranqrel
├── output/                      # TREC-format result files (one per model)
└── scripts/
    ├── run_all.sh
    └── convert_qrels.py         # Adds the "0" iteration column for trec_eval
```

## Setup

1. Install Elasticsearch 8.x and start it locally (default `https://localhost:9200`).
2. Install Python deps:

   ```bash
   pip install -r requirements.txt
   ```

3. Download the Cranfield collection and place the three files in `data/`:
   - `cran.all.1400` — the 1400 documents
   - `cran.qry` — the queries
   - `cranqrel` — the relevance judgments

4. (Optional) export ES credentials if security is enabled:

   ```bash
   export ES_HOST="https://localhost:9200"
   export ES_USER="elastic"
   export ES_PASSWORD="changeme"
   ```

## Run

```bash
# 1. Build the index
python -m src.CreateIndex

# 2. Run all six retrieval models (writes files to output/)
python -m src.Query_Processing

# 3. Convert qrels to trec_eval format and evaluate
python scripts/convert_qrels.py data/cranqrel data/cranqrel.trec
trec_eval data/cranqrel.trec output/es_builtin.txt
trec_eval data/cranqrel.trec output/okapi_tf.txt
trec_eval data/cranqrel.trec output/tfidf.txt
trec_eval data/cranqrel.trec output/bm25.txt
trec_eval data/cranqrel.trec output/lm_laplace.txt
trec_eval data/cranqrel.trec output/lm_jm.txt
```

## Notes on Cranfield vs. AP89

The Cranfield format uses SGML-ish tags rather than TREC `<DOC>` blocks:

```
.I 1          <- document id
.T            <- title
.A            <- author
.B            <- bibliography
.W            <- text body  (we index this as `body_text`)
```

We treat each `.I` block as one document and use the integer id as `<DOCNO>`.
The query file `cran.qry` uses the same `.I` / `.W` tags. The original `cranqrel`
file is **3-column** (`qid docid rel`); `trec_eval` expects 4 columns
(`qid 0 docid rel`), so we provide `scripts/convert_qrels.py`.
