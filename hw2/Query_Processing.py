# -*- coding: utf-8 -*-
"""
Read each Cranfield query (`cranfield/cran.qry`) and look up the inverted
list of every (non-stop) query term in the **unstemmed** index.  Save the
per-query (termVector, termStats) into pickled files that the retrieval
models will consume.
"""
from __future__ import division, print_function

import os
import re
import string
import time
from collections import OrderedDict

import dill

from Unstemmed_With_Stopwords_Index import TermVector

# ---------------------------------------------------------------------------
# CONFIG
# ---------------------------------------------------------------------------
CRAN_QRY_FILE = os.path.join(os.path.dirname(__file__), "cranfield", "cran.qry")
STOPLIST_FILE = os.path.join(os.path.dirname(__file__), "stoplist.txt")
INDEX_DIR     = os.path.join(os.path.dirname(__file__), "Files", "Unstemmed")
INDEX_FILE    = os.path.join(INDEX_DIR, "invertedFile0.txt")
# ---------------------------------------------------------------------------


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


def parseCranfieldQueries(path):
    """
    Yield (qNo, query_text) tuples from a Cranfield-style `cran.qry` file.
    Each query begins with `.I <id>` and the text follows `.W`.
    """
    with open(path, "r", encoding="utf-8", errors="ignore") as fh:
        content = fh.read()

    raw = re.split(r"(?m)^\.I\s+", content)
    for chunk in raw:
        chunk = chunk.strip()
        if not chunk:
            continue
        first_line, _, rest = chunk.partition("\n")
        qno = first_line.strip().lstrip("0") or first_line.strip()
        sections = re.split(r"(?m)^\.W\s*$", rest)
        if len(sections) >= 2:
            qtext = sections[1].strip()
        else:
            qtext = ""
        yield qno, qtext


def queryMaker():
    """Returns list of (qNo, cleaned_query_text)."""
    out = []
    digits = str.maketrans("", "", "0123456789")
    for qno, text in parseCranfieldQueries(CRAN_QRY_FILE):
        clean = re.sub(r"[\-\.\"\s]+", " ", text).strip().translate(digits)
        out.append((qno, clean))
    return out


def queryProcessor(query):
    with open(STOPLIST_FILE, "r", encoding="utf-8") as sfile:
        stopWords = [w.strip() for w in sfile if w.strip()]
    keywords = []
    for word in query.split():
        if word.lower() not in stopWords:
            keywords.append(word)
    cleaned = " ".join(keywords).translate(str.maketrans("", "", string.punctuation))
    return cleaned.strip()


def getInfo(key, catalog, termMap, docMap):
    keyInfo = OrderedDict()
    invList = OrderedDict()
    docDict = OrderedDict()

    keyId = str(termMap.get(key))
    if keyId == "None" or keyId not in catalog:
        # Term not in index - return empty results
        keyInfo[key] = ["0", "0"]
        invList[key] = docDict
        return invList, keyInfo

    offset = catalog[keyId][0]
    length = catalog[keyId][1]

    with open(INDEX_FILE, "r") as indexFile:
        indexFile.seek(int(offset))
        line = indexFile.read(int(length)).rstrip("\n")

    df  = line.split(":")[0].split(",")[1]
    ttf = line.split(":")[0].split(",")[2]
    keyInfo[key] = [df, ttf]
    remStr = line.split(":")[1].split(";")
    for item in remStr:
        parts = item.split(",")
        docno = parts[0]
        docID = docMap.get(int(docno))
        tf = int(parts[1])
        pos = [int(e) for e in parts[2:]]
        docDict[docID] = TermVector(tf, pos)
    invList[key] = docDict
    return invList, keyInfo


def getParameters(query, qNo, catalog, termMap, docMap):
    keywords = queryProcessor(query)
    termVector = OrderedDict()
    termStats  = OrderedDict()
    for key in keywords.split():
        key = key.lower()
        invList, keyInfo = getInfo(key, catalog, termMap, docMap)
        termVector.update(invList)
        termStats.update(keyInfo)

    with open(os.path.join(INDEX_DIR, "Pickles", "termStats%s.p" % qNo), "wb") as f:
        dill.dump(termStats, f)
    with open(os.path.join(INDEX_DIR, "Pickles", "termVector%s.p" % qNo), "wb") as f:
        dill.dump(termVector, f)


def main():
    start_time = time.time()
    docInfo  = unpickler(os.path.join(INDEX_DIR, "Pickles", "docInfo.p"))
    catalog  = parseCatalog(os.path.join(INDEX_DIR, "catalogFile.txt"))
    termMap  = unpickler(os.path.join(INDEX_DIR, "Pickles", "termMap.p"))
    docMap   = unpickler(os.path.join(INDEX_DIR, "Pickles", "docMap.p"))

    queries = queryMaker()
    print("Loaded %d Cranfield queries" % len(queries))
    qIdx = 0
    for qNo, query in queries:
        qIdx += 1
        getParameters(query, qIdx, catalog, termMap, docMap)
        print("Created %d termVector for query %s" % (qIdx, qNo))

    elapsed = time.time() - start_time
    print(elapsed)
    hours = int(elapsed // 3600)
    elapsed -= 3600 * hours
    minutes = int(elapsed // 60)
    seconds = elapsed - 60 * minutes
    print("%d:%d:%d" % (hours, minutes, seconds))


if __name__ == "__main__":
    main()
