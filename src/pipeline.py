from __future__ import annotations

from . import counterfactual, factual, oracle

# A function using any of these can't be trusted to the deterministic oracle
# (non-determinism, I/O, hidden state) — such mutations are tagged indeterminate.
_EFFECTFUL = (
    "random.", "time.", "datetime", "open(", "input(", "print(",
    "socket", "requests", "urllib", "os.", "sys.", "subprocess",
    "global ", ".write(", ".read(",
)


def _effectful(text: str) -> bool:
    return any(marker in text for marker in _EFFECTFUL)


def build(corpus: dict[str, str]) -> tuple[list[dict], dict]:
    records: list[dict] = []
    skipped_module_level = 0
    for source_id, source in corpus.items():
        for cf in counterfactual.generate(source):
            try:
                compile(cf.counterfactual, "<cf>", "exec")
            except SyntaxError:
                continue
            fn = factual.enclosing_function(source, (cf.start["row"], cf.start["column"]))
            if fn is None:
                skipped_module_level += 1
                continue
            if _effectful(fn.text()):
                verdict, evidence = "indeterminate", None
            else:
                verdict, evidence = oracle.compare(
                    source, cf.counterfactual, fn.field("name").text()
                )
            records.append(
                {
                    "id": f"{source_id}:{cf.operator}:{cf.start['row']}:{cf.start['column']}",
                    "language": "python",
                    "family": cf.family,
                    "operator": cf.operator,
                    "intervention": f"{cf.matched_text} -> {cf.replacement_text}",
                    "factual_code": source,
                    "counterfactual_code": cf.counterfactual,
                    "structural_diff": {
                        "before": f"{cf.node_kind}: {cf.matched_text}",
                        "after": f"{cf.node_kind}: {cf.replacement_text}",
                        "span": {"start": cf.start, "end": cf.end},
                    },
                    "compile_result": "passed",
                    "oracle": verdict,
                    "oracle_evidence": evidence,
                    "label": verdict,
                }
            )
    return records, {"skipped_module_level": skipped_module_level}
