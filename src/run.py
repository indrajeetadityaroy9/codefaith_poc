from __future__ import annotations

import argparse
import json
import pathlib
from collections import Counter
from dataclasses import asdict

from .loader import load_corpus
from .pipeline import make_dataset


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("corpus_dir")
    args = ap.parse_args()

    pairs = make_dataset(load_corpus(args.corpus_dir))

    out_path = pathlib.Path("out/pairs.jsonl")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w") as f:
        for p in pairs:
            f.write(json.dumps(asdict(p)) + "\n")

    by_behavior = Counter(p.behavior for p in pairs)
    print(f"pairs: {len(pairs)} -> {out_path}")
    for behavior in ("diverged", "equivalent", "indeterminate"):
        if by_behavior[behavior]:
            print(f"  {behavior}: {by_behavior[behavior]}")


if __name__ == "__main__":
    main()
