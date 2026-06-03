from __future__ import annotations

import json
import re

_WORD = re.compile(r"[A-Za-z_][A-Za-z_0-9]*")
_BACKTICK = re.compile(r"`([^`]+)`")

_DIVERGE_WORDS = ("diverge", "different output", "behavior changes", "behavior changed", "not equivalent")
_EQUIV_WORDS = ("equivalent", "no behavioral change", "behavior is preserved", "same behavior")
_ALLOW = {
    "diverged", "equivalent", "indeterminate", "oracle", "ast", "input", "output",
    "factual", "counterfactual", "true", "false", "none", "behavior",
}


def _tokens(text: str) -> set[str]:
    return set(_WORD.findall(text))


def validate(record: dict, sections: dict) -> list[str]:
    fails = []
    blob = " ".join(sections.values()).lower()
    verdict = record["oracle"]
    family = record["family"]
    sd = record["structural_diff"]
    ev = record["oracle_evidence"]

    if verdict == "diverged" and any(w in blob for w in _EQUIV_WORDS):
        fails.append("contradicts_verdict")
    if verdict == "equivalent" and any(w in blob for w in _DIVERGE_WORDS):
        fails.append("contradicts_verdict")

    if not any(v in blob for v in (family.lower(), family.replace("_", " ").lower())):
        fails.append("missing_family")

    before_txt = sd["before"].split(": ", 1)[-1].lower()
    after_txt = sd["after"].split(": ", 1)[-1].lower()
    if before_txt not in blob or after_txt not in blob:
        fails.append("missing_ast_diff")

    if verdict == "diverged":
        need = list(ev["input"].keys()) + [str(ev["factual_output"]), str(ev["counterfactual_output"])]
        if not all(str(x).lower() in blob for x in need):
            fails.append("missing_evidence")
    elif verdict == "equivalent":
        if not any(w in blob for w in ("no distinguishing", "every tested", "all tested", "no counterexample", "agreed on every")):
            fails.append("missing_evidence")
    else:
        if not any(w in blob for w in ("abstain", "effectful", "non-deterministic", "nondeterministic", "randomness", "i/o")):
            fails.append("missing_evidence")

    vocab = _tokens(
        " ".join([
            record["factual_code"], record["counterfactual_code"], sd["before"], sd["after"],
            record["intervention"], family, record["operator"], json.dumps(ev),
        ])
    ) | _ALLOW
    for span in _BACKTICK.findall(" ".join(sections.values())):
        if any(tok not in vocab for tok in _tokens(span)):
            fails.append("hallucinated_symbol")
            break

    return fails


async def self_verify(client, record: dict, sections: dict, cfg) -> tuple[bool, str]:
    from .llm import chat

    prompt = (
        "An AST analyzer and behavioral oracle ALREADY decided this verdict; it is authoritative "
        "and you must not change it.\n"
        f"ORACLE VERDICT: {record['oracle']}\n"
        f"STRUCTURAL DIFF: {record['structural_diff']['before']} -> {record['structural_diff']['after']}\n"
        f"ORACLE EVIDENCE: {json.dumps(record['oracle_evidence'])}\n\n"
        "CANDIDATE EXPLANATION:\n"
        f"{sections['corrected']}\n\n"
        "Is the explanation faithful — consistent with the verdict and evidence, contradicting "
        "nothing and inventing no code? End your reply with a final line exactly "
        "`FAITHFUL: YES` or `FAITHFUL: NO`."
    )
    _, content = await chat(client, [{"role": "user", "content": prompt}], cfg)
    verdicts = re.findall(r"FAITHFUL:\s*(YES|NO)", (content or "").upper())
    ok = verdicts[-1] == "YES" if verdicts else True
    return ok, " ".join((content or "").split())[-200:] or "empty"
