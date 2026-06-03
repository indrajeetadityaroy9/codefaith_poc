from __future__ import annotations

import difflib
from dataclasses import dataclass, asdict
from typing import Any

from . import counterfactual, factual, oracle


@dataclass
class Pair:
    pair_id: str
    source_id: str
    rule_id: str
    label: str
    factual_code: str
    counterfactual_code: str
    factual_facts: dict[str, Any]
    sexp_changed: bool
    behavior: str
    behavior_witness: str | None
    span: dict[str, dict[str, int]]
    matched_text: str
    replacement_text: str
    diff: str


def _unified_diff(a: str, b: str, name: str) -> str:
    return "".join(
        difflib.unified_diff(
            a.splitlines(keepends=True),
            b.splitlines(keepends=True),
            fromfile=f"{name} (factual)",
            tofile=f"{name} (counterfactual)",
            n=1,
        )
    )


def make_dataset(corpus: dict[str, str]) -> list[Pair]:
    pairs: list[Pair] = []
    for source_id, source in corpus.items():
        facts = factual.extract(source)
        facts_dict = asdict(facts)
        for cf in counterfactual.generate(source):
            try:
                compile(cf.counterfactual, "<cf>", "exec")
            except SyntaxError:
                continue
            cf_sexp = factual.canonical_sexp(factual.parse(cf.counterfactual))
            func = factual.enclosing_function(source, (cf.start["row"], cf.start["column"]))
            behavior, witness = oracle.compare(source, cf.counterfactual, func)
            pairs.append(
                Pair(
                    pair_id=f"{source_id}:{cf.rule_id}:{cf.start['row']}:{cf.start['column']}",
                    source_id=source_id,
                    rule_id=cf.rule_id,
                    label=cf.label,
                    factual_code=source,
                    counterfactual_code=cf.counterfactual,
                    factual_facts=facts_dict,
                    sexp_changed=cf_sexp != facts.sexp,
                    behavior=behavior,
                    behavior_witness=witness,
                    span={"start": cf.start, "end": cf.end},
                    matched_text=cf.matched_text,
                    replacement_text=cf.replacement_text,
                    diff=_unified_diff(source, cf.counterfactual, source_id),
                )
            )
    return pairs
