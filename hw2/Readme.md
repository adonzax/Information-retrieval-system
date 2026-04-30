# HW2 (Cranfield edition)

This is a port of the HW2 inverted-index/retrieval-models project from the
AP89 collection to the **Cranfield** test collection (1,400 documents,
225 queries).

The folder structure intentionally mirrors the original AP89 layout so the
downstream scripts (Query_Processing, Retrieval_Models, demos) work the
same way.

```
hw2/
├── Readme.md
├── requirements.txt
├── stoplist.txt
├── cranfield/                     <- drop the Cranfield data here
│   ├── cran.all.1400
│   ├── cran.qry
│   └── cranqrel
├── Files/
│   ├── Stemmed/
│   │   ├── Maps/                  <- termMap.txt, docMap.txt
│   │   ├── Pickles/               <- termMap.p, docMap.p, docInfo.p,
│   │   │                              termVector{i}.p, termStats{i}.p,
│   │   │                              termVector_Proximity{i}.p, …
│   │   ├── Results/               <- TREC run files
│   │   ├── invertedFile{n}.txt
│   │   └── catalogFile{n}.txt
│   └── Unstemmed/                 <- mirror of Stemmed/
├── Unstemmed_With_Stopwords_Index.py
├── Stemmed_Stopwords_Removed_Index.py
├── Query_Processing.py
├── Query_Processing_Stemmed.py
├── Query_Processing_Unstemmed_Proximity.py
├── Query_Processing_Stemmed_Proximity.py
├── Retrieval_Models.py
├── Retrieval_Models_Stemmed.py
├── Demo_Unstemmed.py
├── Demo_Stemmed.py
└── Demo_Related.py
```

## What changed vs. the AP89 version

| Concern                  | AP89 original                                  | Cranfield port                                 |
| ------------------------ | ---------------------------------------------- | ---------------------------------------------- |
| Document parser          | BeautifulSoup over `<DOC><TEXT>` SGML files    | Custom regex on `.I/.T/.A/.B/.W` markers       |
| Document path            | hard-coded `/Users/Zion/Downloads/AP_DATA/...` | `cranfield/cran.all.1400` (relative)           |
| Query file               | `QueryUpdated.txt`                             | `cranfield/cran.qry`                           |
| Proximity query file     | `ProximityQueryModel.txt`                      | `cranfield/cran.qry` (configurable)            |
| Total document count `D` | 84 678                                         | **1 400**                                      |
| Python version           | Python 2 (`print 'x'`, `translate(None, …)`)   | Python 3                                       |
| Stopword list            | NLTK list                                      | Same NLTK-style list, bundled as `stoplist.txt`|

## Setup

```bash
cd hw2
pip install -r requirements.txt
# put cran.all.1400, cran.qry, cranqrel into ./cranfield/
```

## Pipeline

1.  **Build both indexes** (this fills `Files/Stemmed/` and `Files/Unstemmed/`):

    ```bash
    python Unstemmed_With_Stopwords_Index.py
    python Stemmed_Stopwords_Removed_Index.py
    ```

2.  **Process the queries** (creates per-query `termVector{i}.p` /
    `termStats{i}.p` pickles):

    ```bash
    python Query_Processing.py
    python Query_Processing_Stemmed.py
    python Query_Processing_Unstemmed_Proximity.py
    python Query_Processing_Stemmed_Proximity.py
    ```

3.  **Score with the retrieval models** (writes TREC runs into
    `Files/{Stemmed,Unstemmed}/Results/`):

    ```bash
    python Retrieval_Models.py
    python Retrieval_Models_Stemmed.py
    ```

    Edit the `main()` of either file to enable / disable individual models
    (OkapiTF, BM25, LM-Laplace, LM-Jelinek-Mercer, Proximity).  The
    `USE_PROXIMITY_PICKLES` flag toggles which set of pickles is consumed
    (`termStats{i}.p` vs `termStats_Proximity{i}.p`).

4.  **Evaluate** with `trec_eval`:

    ```bash
    trec_eval -m map -m P.10 cranqrel Files/Stemmed/Results/OkapiBM25_Results_File.txt
    ```

## Notes / caveats

* Cranfield only contains 1 400 docs, well under the 1 000-postings-per-term
  in-memory cap, so the per-1000-doc partial flush in the indexer effectively
  fires once.  The merge step still runs and produces `invertedFile0.txt`
  + `catalogFile.txt`, which is what every downstream script expects.
* The original tokenizer kept periods inside numeric tokens (e.g. `192.168.0.1`,
  `98.6`).  The same rule is preserved here.
* The proximity model uses the minimum-window-of-all-query-terms scoring from
  the original code, with `c = 1500`.
