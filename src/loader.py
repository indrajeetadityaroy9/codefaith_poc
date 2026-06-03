from __future__ import annotations

import pathlib


def load_corpus(path: str) -> dict[str, str]:
    root = pathlib.Path(path)
    return {
        f.relative_to(root).as_posix(): f.read_text(encoding="utf-8")
        for f in sorted(root.rglob("*.py"))
    }
