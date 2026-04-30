"""Convert the 3-column Cranfield `cranqrel` file into trec_eval format.

Cranfield format:    <qid> <docno> <relevance>
trec_eval format:    <qid> 0 <docno> <relevance>

Cranfield's relevance levels are: 1 (most relevant) ... 4 (least), and -1
(not relevant). For trec_eval we want non-negative grades where higher = more
relevant, so we map:

    -1 -> 0     (not relevant)
     1 -> 4
     2 -> 3
     3 -> 2
     4 -> 1

Usage:
    python scripts/convert_qrels.py data/cranqrel data/cranqrel.trec
"""
from __future__ import annotations

import sys
from pathlib import Path

CRAN_TO_TREC = {-1: 0, 1: 4, 2: 3, 3: 2, 4: 1}


def main(src: Path, dst: Path) -> None:
    n_in = n_out = 0
    with src.open("r", encoding="utf-8", errors="ignore") as fin, \
         dst.open("w", encoding="utf-8") as fout:
        for line in fin:
            parts = line.split()
            if len(parts) != 3:
                continue
            n_in += 1
            qid, docno, rel = parts
            try:
                rel_i = int(rel)
            except ValueError:
                continue
            mapped = CRAN_TO_TREC.get(rel_i, max(rel_i, 0))
            fout.write(f"{qid} 0 {docno} {mapped}\n")
            n_out += 1
    print(f"[convert_qrels] read {n_in} lines, wrote {n_out} -> {dst}")


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python scripts/convert_qrels.py <cranqrel> <out.trec>")
        sys.exit(1)
    main(Path(sys.argv[1]), Path(sys.argv[2]))
