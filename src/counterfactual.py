from __future__ import annotations

import re
from dataclasses import dataclass

from ast_grep_py import SgRoot

from .families import ConceptFamily

_METAVAR = re.compile(r"\$([A-Z][A-Z0-9_]*)")


@dataclass(frozen=True)
class CFRule:
    id: str
    family: ConceptFamily
    pattern: str
    template: str


@dataclass
class CFResult:
    operator: str
    family: ConceptFamily
    node_kind: str
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
        rules.append(CFRule(f"cmp_{safe}", "COMPARISON_BOUNDARY", f"$A {op} $B", f"$A {neg} $B"))
    return rules


RULES: list[CFRule] = [
    *_comparison_rules(),
    CFRule("bool_true_false", "BOOLEAN_LOGIC", "True", "False"),
    CFRule("bool_false_true", "BOOLEAN_LOGIC", "False", "True"),
    CFRule("logic_and_or", "BOOLEAN_LOGIC", "$A and $B", "$A or $B"),
    CFRule("range_off_by_one", "LOOP_STRUCTURE", "range($N)", "range($N + 1)"),
    CFRule("return_negate", "RETURN_FLOW", "return $A", "return not $A"),
    CFRule("call_swap_args", "FUNCTION_CALL", "$F($A, $B)", "$F($B, $A)"),
    # Semantics-preserving controls (the oracle still decides the label; these
    # are rewrites *expected* to be equivalent, mixed into existing families so
    # family does not leak the label).
    CFRule("redundant_parens", "RETURN_FLOW", "return $A", "return ($A)"),
    CFRule("reorder_commutative_add", "DATA_FLOW", "$A + $B", "$B + $A"),
    CFRule("eq_double_negation", "BOOLEAN_LOGIC", "$A == $B", "not ($A != $B)"),
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
                    rule.family,
                    node.kind(),
                    root.commit_edits([node.replace(replacement)]),
                    node.text(),
                    replacement,
                    {"row": rng.start.line, "column": rng.start.column},
                    {"row": rng.end.line, "column": rng.end.column},
                )
            )
    return out
