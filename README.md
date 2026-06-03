# codefaith — POC

Generates AST-based factual / counter-factual code pairs from a directory of `.py` files.

- ast-grep (a single parse, embedding tree-sitter) backs both a factual layer that reads the `SgNode` tree for a canonical s-expression and structured facts, and a counter-factual layer whose "intervention operators" each apply one minimal structural rewrite (e.g. `age >= 18` → `age < 18`)

- every mutation passes a mandatory `compile()` gate so only legal Python is emitted, and a behavioral oracle then executes both versions over a deterministic input battery to tag each pair `diverged` (a true counter-factual), `equivalent`, or `indeterminate` 

- run it with `uv run python -m src.run samples` to write the `(factual, counter-factual, label, diff, behavior)` tuples to `out/pairs.jsonl`.
# codefaith_poc
