# -*- coding: utf-8 -*-
"""Sanity check: print the number of documents in the stemmed docInfo pickle."""
from __future__ import print_function

import os
import dill


def unpickler(path):
    with open(path, "rb") as f:
        return dill.load(f)


if __name__ == "__main__":
    here = os.path.dirname(__file__)
    docInfo = unpickler(os.path.join(here, "Files", "Stemmed", "Pickles", "docInfo.p"))
    print(len(docInfo))
