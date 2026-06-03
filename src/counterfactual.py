from __future__ import annotations

import re
from dataclasses import dataclass

from ast_grep_py import SgRoot

_METAVAR = re.compile(r"\$([A-Z][A-Z0-9_]*)")


@dataclass(frozen=True)
class CFRule:
    id: str
    label: str
    pattern: str
    template: str


@dataclass
class CFResult:
    rule_id: str
    label: str
    counterfactual: str
    matched_text: str
    replacement_text: str
    start: dict[str, int]
    end: dict[str, int]


_COMPARISON_NEGATION = {">=": "<", "<=": ">", ">": "<=", "<": ">=", "==": "!=", "!=": "=="}


def _comparison_rules() -> list[CFRule]:
    rules = []
    for op, neg in _COMPARISON_NEGATION.items():
        safe = op.replace("=", "eq").replace("<", "lt").replace(">", "gt").replace("!", "ne")
        rules.append(CFRule(f"cmp_{safe}", "comparison-negation", f"$A {op} $B", f"$A {neg} $B"))
    return rules


RULES: list[CFRule] = [
    *_comparison_rules(),
    CFRule("bool_true_false", "boolean-literal-flip", "True", "False"),
    CFRule("bool_false_true", "boolean-literal-flip", "False", "True"),
    CFRule("logic_and_or", "logical-connective-swap", "$A and $B", "$A or $B"),
    CFRule("arith_add_sub", "arithmetic-op-swap", "$A + $B", "$A - $B"),
    CFRule("range_off_by_one", "loop-bound-offset", "range($N)", "range($N + 1)"),
]


def generate(source: str) -> list[CFResult]:
    root = SgRoot(source, "python").root()
    out: list[CFResult] = []
    for rule in RULES:
        names = _METAVAR.findall(rule.template)
        for node in root.find_all(pattern=rule.pattern):
            metavars = {n: node.get_match(n).text() for n in names}
            replacement = _METAVAR.sub(lambda m: metavars[m.group(1)], rule.template)
            rng = node.range()
            out.append(
                CFResult(
                    rule.id,
                    rule.label,
                    root.commit_edits([node.replace(replacement)]),
                    node.text(),
                    replacement,
                    {"row": rng.start.line, "column": rng.start.column},
                    {"row": rng.end.line, "column": rng.end.column},
                )
            )
    return out
