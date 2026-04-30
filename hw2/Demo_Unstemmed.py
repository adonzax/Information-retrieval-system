# -*- coding: utf-8 -*-
"""
Quick demo: read a list of words from `in.0.50.txt` and look up their
df / ttf in the **unstemmed** Cranfield index.  Output goes to
`Files/out.0.no.stop.no.stem.txt`.
"""
from __future__ import division, print_function

import os
import dill

HERE = os.path.dirname(__file__)
INDEX_DIR = os.path.join(HERE, "Files", "Unstemmed")


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


def main():
    docInfo = unpickler(os.path.join(INDEX_DIR, "Pickles", "docInfo.p"))
    catalog = parseCatalog(os.path.join(INDEX_DIR, "catalogFile.txt"))
    termMap = unpickler(os.path.join(INDEX_DIR, "Pickles", "termMap.p"))
    docMap  = unpickler(os.path.join(INDEX_DIR, "Pickles", "docMap.p"))

    in_path  = os.path.join(HERE, "in.0.50.txt")
    out_path = os.path.join(HERE, "Files", "out.0.no.stop.no.stem.txt")
    idx_path = os.path.join(INDEX_DIR, "invertedFile0.txt")

    with open(in_path, "r") as inFile, \
         open(idx_path, "r") as indexFile, \
         open(out_path, "a+") as outFile:
        for line in inFile:
            key = line.strip()
            keyId = str(termMap.get(key))
            if keyId in catalog:
                offset = catalog[keyId][0]
                length = catalog[keyId][1]
                indexFile.seek(int(offset))
                termLine = indexFile.read(int(length))
                df  = termLine.split(":")[0].split(",")[1]
                ttf = termLine.split(":")[0].split(",")[2]
                outFile.write("%s %s %s\n" % (line.strip(), df, ttf))
            else:
                outFile.write(line)


if __name__ == "__main__":
    main()
