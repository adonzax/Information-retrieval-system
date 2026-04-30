# -*- coding: utf-8 -*-
"""
Unstemmed (stop-word removed) inverted index builder for the Cranfield collection.

Reads `cranfield/cran.all.1400` (the standard 1400-document Cranfield file
formatted with `.I`, `.T`, `.A`, `.B`, `.W` field markers), tokenizes each
document, removes stop-words, and produces:

    Files/Unstemmed/invertedFile<n>.txt   - partial / merged index files
    Files/Unstemmed/catalogFile<n>.txt    - per-partial catalogs
    Files/Unstemmed/catalogFile.txt       - final merged catalog (termid,offset,length)
    Files/Unstemmed/Maps/termMap.txt      - human readable term -> termid map
    Files/Unstemmed/Maps/docMap.txt       - human readable docid -> docno map
    Files/Unstemmed/Pickles/termMap.p     - pickled term -> termid
    Files/Unstemmed/Pickles/docMap.p      - pickled docid -> docno
    Files/Unstemmed/Pickles/docInfo.p     - pickled docno -> doc_length
"""
from __future__ import division, print_function

import os
import re
import time
from collections import defaultdict, OrderedDict

import dill

# ---------------------------------------------------------------------------
# CONFIG -- adjust these paths if your Cranfield files live somewhere else.
# ---------------------------------------------------------------------------
CRAN_DOCS_FILE = os.path.join(os.path.dirname(__file__), "cranfield", "cran.all.1400")
STOPLIST_FILE  = os.path.join(os.path.dirname(__file__), "stoplist.txt")
OUT_DIR        = os.path.join(os.path.dirname(__file__), "Files", "Unstemmed")
# ---------------------------------------------------------------------------


# To store the term_freq and positions of the term
class TermVector(object):
    def __init__(self, tf, pos):
        self.tf = tf
        self.pos = pos

    def getTF(self):
        return self.tf

    def getPos(self):
        return self.pos


# To store the terms, termMap (term -> termid), file names containing the term,
# with offset and length within each partial inverted file.
class Catalog(object):
    def __init__(self):
        self.terms = {}
        self.termMap = {}

    def addTerm(self, term, offset, length, fileName, termid):
        if term not in self.terms:
            self.terms[term] = {}
            self.termMap[term] = termid
        self.terms[term][fileName] = CatalogTerm(term, offset, length)

    def removeTerm(self, term):
        del self.terms[term]
        del self.termMap[term]


class CatalogTerm(object):
    def __init__(self, term, offset, length):
        self.term = term
        self.offset = offset
        self.length = length


# ---------------------------------------------------------------------------
# Cranfield-specific document reader
# ---------------------------------------------------------------------------
def parseCranfieldDocs(path):
    """
    Yield (docno, text) tuples from a Cranfield `cran.all.1400` style file.
    Each document begins with `.I <id>` and contains `.T`, `.A`, `.B`, `.W`
    sections.  We use Title (.T) + Body (.W) as the document text - this is
    the conventional choice for Cranfield experiments.
    """
    with open(path, "r", encoding="utf-8", errors="ignore") as fh:
        content = fh.read()

    # Split on lines starting with ".I "
    raw_docs = re.split(r"(?m)^\.I\s+", content)
    for chunk in raw_docs:
        chunk = chunk.strip()
        if not chunk:
            continue
        # First whitespace token after ".I" is the doc id
        first_line, _, rest = chunk.partition("\n")
        docno = first_line.strip()

        # Split rest into sections by .T .A .B .W markers
        sections = re.split(r"(?m)^\.([TABW])\s*$", rest)
        # sections = ['', 'T', 'title-text', 'A', 'author-text', 'B', 'bib-text', 'W', 'body-text']
        section_map = {}
        for i in range(1, len(sections) - 1, 2):
            tag = sections[i]
            text = sections[i + 1]
            section_map[tag] = text

        title = section_map.get("T", "")
        body  = section_map.get("W", "")
        text  = (title + " " + body).strip()
        yield docno, text


# ---------------------------------------------------------------------------
# Tokenisation and cleaning
# ---------------------------------------------------------------------------
def cleanText(text):
    text = text.replace("`", " ")
    text = text.replace("-", " ")
    text = text.replace(",", " ")
    text = re.sub(r"\.\.+", " ", text)
    # Drop punctuation we don't want, keep . , % - which may be part of tokens
    text = re.sub(r"[^A-Za-z0-9.\-,% \n\t]", "", text)
    return text


def tokenizer(text):
    """
    Tokens are sequences of letters/digits, optionally containing single
    periods between alphanumeric characters (so 192.168.0.1 and 98.6 are
    tokens but `aunt's` and `123,456` are not). All output is lowercase.
    Returns a list of [token, position] pairs (1-indexed positions).
    """
    posToken = []
    i = 0
    tokens = re.split(r"[^\w\.]+", text)
    for token in tokens:
        token = re.sub(r"\.(?=\s)", "", token).rstrip(".")
        if "." in token:
            chars = token.split(".")
            for c in chars:
                if not c.isdigit():
                    if len(c) > 1:
                        token = re.sub(r"\.", " ", token)
                        break
                else:
                    break
        token = token.lower()
        if token != "":
            i += 1
            posToken.append([token, i])
    return posToken


def getDocLen(text):
    count = 0
    for line in text.splitlines():
        word = re.sub(r"\s+", " ", line).strip().split(" ")
        count += len([w for w in word if w])
    return count


# ---------------------------------------------------------------------------
# Indexing helpers
# ---------------------------------------------------------------------------
def constructDict(tokens, docID):
    termDict = defaultdict(lambda: defaultdict(TermVector))
    for token in tokens:
        if token[2] == docID:
            if token[0] not in stopWords:
                if token[0] in termDict:
                    if docID in termDict[token[0]]:
                        termDict[token[0]][docID].tf = termDict[token[0]][docID].getTF() + 1
                        termDict[token[0]][docID].pos.append(token[1])
                    else:
                        termDict[token[0]][docID] = TermVector(1, [token[1]])
                else:
                    docDict = defaultdict(TermVector)
                    docDict[docID] = TermVector(1, [token[1]])
                    termDict[token[0]] = docDict
        else:
            docID = token[2]
            if token[0] not in stopWords:
                if token[0] in termDict:
                    termDict[token[0]][docID] = TermVector(1, [token[1]])
                else:
                    docDict = defaultdict(TermVector)
                    docDict[docID] = TermVector(1, [token[1]])
                    termDict[token[0]] = docDict
    return termDict


def calcTTF(termdict, term):
    return sum(termdict[term][docid].getTF() for docid in termdict[term])


def calcDF(termdict, term):
    return len(termdict[term])


docNoSet = {}


def loadCatalog(termDict, fileName, invFileNo, catalogFile=None):
    fName = "%s%s.txt" % (fileName, invFileNo)
    invFile = open(fName, "a+")
    for term in termDict:
        offset = invFile.tell()
        ttf = calcTTF(termDict, term)
        df = calcDF(termDict, term)
        if catalogFile is not None:
            termid = catalog.termMap[term]
            catalog.removeTerm(term)
        else:
            if term not in catalog.termMap:
                termid = len(catalog.termMap) + 1
            else:
                termid = catalog.termMap[term]

        inputStr = [str(termid), ",", str(df), ",", str(ttf), ":"]
        for docno in termDict[term]:
            if catalogFile is not None:
                docid = docno
            else:
                if docno not in docNoSet:
                    docid = len(docMap) + 1
                    docNoSet[docno] = docid
                    docMap[docid] = docno
                else:
                    docid = docNoSet[docno]
            inputStr.append(str(docid))
            inputStr.append(",")
            inputStr.append(str(termDict[term][docno].getTF()))
            inputStr.append(",")
            inputStr.append(",".join(str(e) for e in termDict[term][docno].getPos()))
            inputStr.append(";")
        inputStr[-1] = "\n"
        writeStr = "".join(inputStr)
        length = len(writeStr)
        catalog.addTerm(term, offset, length, fName, termid)

        if catalogFile is not None:
            catalogFile.write("%s,%s,%s\n" % (termid, offset, length))
        else:
            tempCatalogFile = open(os.path.join(OUT_DIR, "catalogFile%d.txt" % invFileNo), "a+")
            tempCatalogFile.write("%s,%s,%s\n" % (termid, offset, length))
            tempCatalogFile.close()

        invFile.write(writeStr)
    invFile.close()
    return invFileNo + 1


def loadInvList(offset, length, invFile, term, docMap=None):
    invList = OrderedDict()
    invFile.seek(offset)
    s = invFile.read(length)
    docDict = OrderedDict()
    remStr = s.split(":")[1].split(";")
    for item in remStr:
        parts = item.split(",")
        docno = parts[0]
        docID = docMap.get(int(docno)) if docMap is not None else docno
        tf = int(parts[1])
        pos = [int(e) for e in parts[2:]]
        docDict[docID] = TermVector(tf, pos)
    invList[term] = docDict
    return invList


def mergeInvFiles():
    termDict = OrderedDict()
    catalogFile = open(os.path.join(OUT_DIR, "catalogFile.txt"), "a+")
    for term in list(catalog.terms.keys()):
        for fname in catalog.terms[term]:
            invFile = open(fname, "r")
            invList = loadInvList(
                catalog.terms[term][fname].offset,
                catalog.terms[term][fname].length,
                invFile, term)
            invFile.close()
            if term not in termDict:
                termDict[term] = invList[term]
            else:
                for docId in invList[term]:
                    if docId in termDict[term]:
                        termDict[term][docId].tf = termDict[term][docId].getTF() + 1
                        termDict[term][docId].pos.extend(invList[term][docId].pos)
                    else:
                        termDict[term][docId] = TermVector(invList[term][docId].tf,
                                                          invList[term][docId].pos)
        termDict[term] = OrderedDict(sorted(termDict[term].items(),
                                            key=lambda x: x[1].tf, reverse=True))
        if len(termDict) == 1000:
            loadCatalog(termDict, os.path.join(OUT_DIR, "invertedFile"), 0, catalogFile)
            termDict = OrderedDict()
    if len(termDict) > 0:
        loadCatalog(termDict, os.path.join(OUT_DIR, "invertedFile"), 0, catalogFile)
    catalogFile.close()


def indexer(tokens, flag, invFile):
    docID = tokens[0][2]
    termDict = constructDict(tokens, docID)
    invFile = loadCatalog(termDict, os.path.join(OUT_DIR, "invertedFile"), invFile)
    return invFile


def writeHashMap(hashMap, fileName):
    mapFile = open(os.path.join(OUT_DIR, "Maps", fileName), "a+")
    for key, value in hashMap.items():
        mapFile.write("%s,%s\n" % (key, value))
    mapFile.close()


def pickler(path, ds):
    with open(path, "wb") as f:
        dill.dump(ds, f)


# ---------------------------------------------------------------------------
# Main pipeline: tokenize Cranfield -> partial indexes -> merged index
# ---------------------------------------------------------------------------
def getTokens():
    tokens = []
    docInfo = {}
    flag = 1
    countDoc = 0
    fileIter = 0
    invFile = 1

    docs = list(parseCranfieldDocs(CRAN_DOCS_FILE))
    fileCount = len(docs)
    print("Found %d Cranfield documents in %s" % (fileCount, CRAN_DOCS_FILE))

    for docNo, text in docs:
        fileIter += 1
        countDoc += 1
        print("Processing %d / %d : doc %s" % (fileIter, fileCount, docNo))

        text = cleanText(text)
        docInfo[docNo] = getDocLen(text)
        posTokens = tokenizer(text)
        for token in posTokens:
            token.append(docNo)
        tokens += posTokens

        # Flush every 1000 documents (per the homework spec)
        if countDoc == 1000:
            countDoc = 0
            invFile = indexer(tokens, flag, invFile)
            tokens = []
            flag = 0

    if countDoc > 0:
        invFile = indexer(tokens, flag, invFile)

    pickler(os.path.join(OUT_DIR, "Pickles", "termMap.p"), catalog.termMap)
    writeHashMap(catalog.termMap, "termMap.txt")
    pickler(os.path.join(OUT_DIR, "Pickles", "docMap.p"), docMap)
    writeHashMap(docMap, "docMap.txt")
    pickler(os.path.join(OUT_DIR, "Pickles", "docInfo.p"), docInfo)


# ---------------------------------------------------------------------------
# Globals
# ---------------------------------------------------------------------------
docMap = {}
catalog = Catalog()

with open(STOPLIST_FILE, "r", encoding="utf-8") as sfile:
    stopWords = sfile.readlines()
stopWords = set(map(str.strip, stopWords))


def main():
    start_time = time.time()
    getTokens()
    mergeInvFiles()
    elapsed = time.time() - start_time
    print(elapsed)
    hours = int(elapsed // 3600)
    elapsed -= 3600 * hours
    minutes = int(elapsed // 60)
    seconds = elapsed - 60 * minutes
    print("%d:%d:%d" % (hours, minutes, seconds))


if __name__ == "__main__":
    main()
