# -*- coding: utf-8 -*-
"""
Retrieval models on the **stemmed** Cranfield index.  Output goes to
`Files/Stemmed/Results/`.  Toggle which models to run inside `main()`.
"""
from __future__ import division, print_function

import math
import os
import string
from collections import defaultdict
from operator import itemgetter

import dill

from Stemmed_Stopwords_Removed_Index import TermVector  # noqa: F401  (needed for unpickling)

# ---------------------------------------------------------------------------
# CONFIG
# ---------------------------------------------------------------------------
CRAN_QRY_FILE = os.path.join(os.path.dirname(__file__), "cranfield", "cran.qry")
INDEX_DIR     = os.path.join(os.path.dirname(__file__), "Files", "Stemmed")
RESULTS_DIR   = os.path.join(INDEX_DIR, "Results")

D = 1400
# ---------------------------------------------------------------------------


def restructureTV(termVector):
    dictDocID = defaultdict(lambda: defaultdict(list))
    for key in termVector:
        for docid in termVector[key]:
            dictDocID[docid][key] = [termVector[key][docid].getTF(),
                                     termVector[key][docid].getPos()]
    return dictDocID


def Total_okapiTF(qNo, termVector, termStats, docInfo, avgDocLen):
    docScore = []
    dictDocID = restructureTV(termVector)
    for docid in dictDocID:
        tf = 0
        for key in dictDocID[docid]:
            tfwd = dictDocID[docid][key][0]
            docLen = int(docInfo.get(docid))
            tf += (tfwd / (tfwd + 0.5 + (1.5 * (docLen / avgDocLen))))
        docScore.append([docid, tf])
    docScore.sort(key=itemgetter(1), reverse=True)
    with open(os.path.join(RESULTS_DIR, "OkapiTF_Results_File.txt"), "a+") as out:
        rank = 1
        for ds in docScore:
            out.write("%s Q0 %s %d %lf Exp\n" % (qNo, ds[0], rank, ds[1]))
            if rank == 1000:
                break
            rank += 1


def Okapi_BM25(qNo, termVector, termStats, docInfo, avgDocLen):
    k1, k2, b = 1.2, 1.2, 0.75
    docScore = []
    dictDocID = restructureTV(termVector)
    for docid in dictDocID:
        bm25 = 0
        for key in dictDocID[docid]:
            tfwd = dictDocID[docid][key][0]
            docLen = int(docInfo.get(docid))
            df = int(termStats[key][0])
            op1 = math.log10((D + 0.5) / (df + 0.5))
            op2 = ((tfwd + (k1 * tfwd)) /
                   (tfwd + (k1 * ((1 - b) + (b * (docLen / avgDocLen))))))
            op3 = ((tfwd + (k2 * tfwd)) / (tfwd + k2))
            bm25 += op1 * op2 * op3
        docScore.append([docid, bm25])
    docScore.sort(key=itemgetter(1), reverse=True)
    with open(os.path.join(RESULTS_DIR, "OkapiBM25_Results_File.txt"), "a+") as out:
        rank = 1
        for ds in docScore:
            out.write("%s Q0 %s %d %lf Exp\n" % (qNo, ds[0], rank, ds[1]))
            if rank == 1000:
                break
            rank += 1


def UnigramLM_Laplace(qNo, termVector, termStats, docInfo, V):
    keys = set()
    dictDocID = restructureTV(termVector)
    for doc_id in dictDocID:
        for key in dictDocID[doc_id]:
            keys.add(key)
    keys = list(keys)

    docScoreDict = {}
    for word in keys:
        for docid in dictDocID:
            d = dictDocID[docid]
            docLen = int(docInfo.get(docid))
            if word in d:
                tfwd = d[word][0]
                score = float(tfwd + 1) / float(docLen + V)
            else:
                score = float(1) / float(docLen + V)
            docScoreDict.setdefault(docid, 0.0)
            docScoreDict[docid] += math.log(score)
    DocScore = sorted(docScoreDict.items(), key=itemgetter(1), reverse=True)
    with open(os.path.join(RESULTS_DIR, "UnigramLMLaplace_Results_File.txt"), "a+") as out:
        rank = 1
        for ds in DocScore:
            out.write("%s Q0 %s %d %f Exp\n" % (qNo, ds[0], rank, ds[1]))
            if rank == 1000:
                break
            rank += 1


def UnigramLM_JelinekMercer(qNo, termVector, termStats, docInfo, V):
    keys = set()
    dictDocID = restructureTV(termVector)
    for doc_id in dictDocID:
        for key in dictDocID[doc_id]:
            keys.add(key)
    keys = list(keys)
    l = 0.8
    docScoreDict = {}
    for word in keys:
        cTF = int(termStats[word][1]) if termStats.get(word) else 0
        if cTF == 0:
            continue
        for docid in dictDocID:
            d = dictDocID[docid]
            docLen = int(docInfo.get(docid))
            pML = cTF / V
            if word in d:
                tfwd = d[word][0]
                score = float(l * float(tfwd / docLen)) + (float(1 - l) * pML)
            else:
                score = (float(1 - l) * pML)
            docScoreDict.setdefault(docid, 0.0)
            docScoreDict[docid] += math.log(score)
    DocScore = sorted(docScoreDict.items(), key=itemgetter(1), reverse=True)
    with open(os.path.join(RESULTS_DIR, "UnigramLMJM_Results_File.txt"), "a+") as out:
        rank = 1
        for ds in DocScore:
            out.write("%s Q0 %s %d %lf Exp\n" % (qNo, ds[0], rank, ds[1]))
            if rank == 1000:
                break
            rank += 1


def TF_IDF(qNo, termVector, termStats, docInfo, avgDocLen):
    """
    TF-IDF scoring function with Okapi TF normalization.
    Outputs to TF-IDF_Results_File.txt
    """
    docScore = []
    dictDocID = restructureTV(termVector)
    
    for docid in dictDocID:
        tfidf_score = 0.0
        for term in dictDocID[docid]:
            tfwd = dictDocID[docid][term][0]
            docLen = int(docInfo.get(docid, 1))
            
            # Okapi TF normalization (same as Total_okapiTF)
            norm_tf = tfwd / (tfwd + 0.5 + 1.5 * (docLen / avgDocLen))
            
            # IDF calculation with smoothing
            if term in termStats:
                df = int(termStats[term][0])
            else:
                df = 1
            idf = math.log10((D + 0.5) / (df + 0.5))
            
            tfidf_score += norm_tf * idf
        
        docScore.append([docid, tfidf_score])
    
    # Sort by score descending
    docScore.sort(key=itemgetter(1), reverse=True)
    
    # Write results
    output_file = os.path.join(RESULTS_DIR, "TF-IDF_Results_File.txt")
    with open(output_file, "a+") as out:
        rank = 1
        for ds in docScore:
            out.write("%s Q0 %s %d %lf Exp\n" % (qNo, ds[0], rank, ds[1]))
            if rank == 1000:
                break
            rank += 1


def rangeOfWindow(pos):
    minROW = float("inf")
    keyPos = {key: pos[key][0] for key in pos}
    maxLen = len(keyPos)
    while maxLen == len(keyPos):
        row = keyPos[max(keyPos, key=keyPos.get)] - keyPos[min(keyPos, key=keyPos.get)]
        minKey = min(keyPos, key=keyPos.get)
        minPos = pos[minKey].index(keyPos[min(keyPos, key=keyPos.get)])
        if minPos < (len(pos[minKey]) - 1):
            keyPos[minKey] = pos[minKey][minPos + 1]
        else:
            keyPos.pop(minKey)
        if row < minROW:
            minROW = row
    return minROW


def proximity(qNo, termVector, termStats, docInfo, V):
    docScore = []
    dictDocID = restructureTV(termVector)
    c = 1500
    for docid in dictDocID:
        i = 0
        docLen = int(docInfo.get(docid))
        pos = {}
        for key in dictDocID[docid]:
            pos[key] = dictDocID[docid][key][1]
            i += 1
        if not pos:
            continue
        row = rangeOfWindow(pos) if len(pos) > 1 else 0
        score = (c - row) * i / (docLen + V)
        docScore.append([docid, score])
    docScore.sort(key=itemgetter(1), reverse=True)
    with open(os.path.join(RESULTS_DIR, "Proximity_Results_File.txt"), "a+") as out:
        rank = 1
        for ds in docScore:
            out.write("%s Q0 %s %d %lf Exp\n" % (qNo, ds[0], rank, ds[1]))
            if rank == 1000:
                break
            rank += 1


def queryNums():
    import re
    with open(CRAN_QRY_FILE, "r", encoding="utf-8", errors="ignore") as fh:
        content = fh.read()
    raw = re.split(r"(?m)^\.I\s+", content)
    out = []
    for chunk in raw:
        chunk = chunk.strip()
        if not chunk:
            continue
        first_line, _, _ = chunk.partition("\n")
        qno = first_line.strip().lstrip("0") or first_line.strip()
        out.append(qno.translate(str.maketrans("", "", string.punctuation)))
    return out


def unpickler(path):
    with open(path, "rb") as f:
        return dill.load(f)


def parseCatalog(path):
    cat = {}
    with open(path, "r") as fh:
        for line in fh:
            content = line.strip().split(",")
            cat[content[0]] = content[1:]
    return cat


# Set to False for standard models (TF, BM25, LM)
# Set to True for proximity model only
USE_PROXIMITY_PICKLES = False


def main():
    print("Loading data...")
    termMap   = unpickler(os.path.join(INDEX_DIR, "Pickles", "termMap.p"))
    catalog   = parseCatalog(os.path.join(INDEX_DIR, "catalogFile.txt"))
    docInfo   = unpickler(os.path.join(INDEX_DIR, "Pickles", "docInfo.p"))
    avgDocLen = sum(docInfo.values()) / len(docInfo)
    V         = len(catalog.keys())
    
    print(f"Loaded {len(docInfo)} documents")
    print(f"Vocabulary size: {V}")
    print(f"Average document length: {avgDocLen:.2f}")

    qNums = queryNums()
    print(f"Processing {len(qNums)} queries...")
    
    for i, qNo in enumerate(qNums, start=1):
        suffix = "_Proximity%s" % i if USE_PROXIMITY_PICKLES else "%s" % i
        ts_path = os.path.join(INDEX_DIR, "Pickles", "termStats%s.p" % suffix)
        tv_path = os.path.join(INDEX_DIR, "Pickles", "termVector%s.p" % suffix)
        
        if not (os.path.exists(ts_path) and os.path.exists(tv_path)):
            print(f"Skip query {qNo} (missing pickles)")
            continue
        
        termStats  = unpickler(ts_path)
        termVector = unpickler(tv_path)
        print(f"Running Query {i} / {len(qNums)} (ID: {qNo})")

        # Run all models
        Total_okapiTF(qNo, termVector, termStats, docInfo, avgDocLen)
        Okapi_BM25(qNo, termVector, termStats, docInfo, avgDocLen)
        UnigramLM_Laplace(qNo, termVector, termStats, docInfo, V)
        UnigramLM_JelinekMercer(qNo, termVector, termStats, docInfo, V)
        TF_IDF(qNo, termVector, termStats, docInfo, avgDocLen)
        # proximity(qNo, termVector, termStats, docInfo, V)  # Uncomment if needed
        
    print("Done! All result files saved to:", RESULTS_DIR)


if __name__ == "__main__":
    # Create Results directory if it doesn't exist
    os.makedirs(RESULTS_DIR, exist_ok=True)
    main()