from __future__ import annotations

import argparse
import json
import pathlib
from collections import Counter

from .loader import load_corpus
from .pipeline import build


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("corpus_dir")
    args = ap.parse_args()

    records, stats = build(load_corpus(args.corpus_dir))

    out = pathlib.Path("out/ground_truth.jsonl")
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w") as f:
        for r in records:
            f.write(json.dumps(r, default=repr) + "\n")

    counts = Counter(r["oracle"] for r in records)
    print(f"records: {len(records)} -> {out}")
    for verdict in ("diverged", "equivalent", "indeterminate"):
        if counts[verdict]:
            print(f"  {verdict}: {counts[verdict]} ({counts[verdict] / len(records):.0%})")
    print(json.dumps(stats))


if __name__ == "__main__":
    main()
