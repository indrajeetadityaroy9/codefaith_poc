from __future__ import annotations

import json
import re

_HEADERS = ["FAITHFUL REASONING", "VERIFICATION", "CORRECTED REASONING"]
_HEADER_RE = re.compile(
    r"^#{1,6}\s*(" + "|".join(re.escape(h) for h in _HEADERS) + r")\s*$", re.MULTILINE
)


def _evidence_text(record: dict) -> str:
    verdict, ev = record["oracle"], record["oracle_evidence"]
    if verdict == "diverged":
        return (
            f"The oracle ran both versions and they DIVERGED. Witnessing input (by parameter "
            f"name): {json.dumps(ev['input'])}. Factual output: {json.dumps(ev['factual_output'])}. "
            f"Counterfactual output: {json.dumps(ev['counterfactual_output'])}."
        )
    if verdict == "equivalent":
        return (
            "The oracle ran both versions over its full input battery and found NO distinguishing "
            "input — outputs agreed on every tested input. There is no counterexample; do not invent one."
        )
    return (
        "The oracle ABSTAINED: the function is effectful / non-deterministic (it touches I/O, "
        "randomness, time, or hidden state), so equivalence cannot be decided by execution."
    )


def build_user_prompt(record: dict, task: str, repair_failures: list[str] | None = None) -> str:
    sd = record["structural_diff"]
    verdict = record["oracle"]
    before_txt = sd["before"].split(": ", 1)[-1]
    after_txt = sd["after"].split(": ", 1)[-1]
    required = [
        f"the concept-family token   {record['family']}",
        f"the before expression   {before_txt}",
        f"the after expression   {after_txt}",
    ]
    if verdict == "diverged":
        ev = record["oracle_evidence"]
        required += [
            f"the witnessing input   {json.dumps(ev['input'])}",
            f"the factual output   {json.dumps(ev['factual_output'])}",
            f"the counterfactual output   {json.dumps(ev['counterfactual_output'])}",
        ]
    elif verdict == "equivalent":
        required.append("the phrase   no distinguishing input   (outputs agreed on every tested input)")
    else:
        required.append("the word   effectful   (the oracle abstains)")
    mandatory = "\n".join("  - " + r for r in required)

    repair = ""
    if repair_failures:
        repair = (
            "\n\nYOUR PREVIOUS ANSWER WAS REJECTED for: "
            + ", ".join(repair_failures)
            + ". Fix these and re-emit all three sections."
        )
    return f"""{task}

AUTHORITATIVE FACTS (an AST analyzer and a behavioral oracle already decided this; you must NOT change or contradict the verdict):
- concept family: {record['family']}
- structural diff: {sd['before']}  ->  {sd['after']}
- compile result: {record['compile_result']}
- ORACLE VERDICT (authoritative label): {verdict}
- oracle evidence: {_evidence_text(record)}

Explain WHY the verdict is "{verdict}", using ONLY the facts above. Do not invent code, inputs, or outputs not listed.

MANDATORY — your FAITHFUL REASONING and VERIFICATION sections must EACH contain, written out exactly:
{mandatory}{repair}

Output EXACTLY these three sections, each beginning with its header line:

### FAITHFUL REASONING
(step-by-step why the verdict holds, grounded in the structural diff and the oracle evidence)

### VERIFICATION
(re-derive the verdict from the same evidence; confirm your reasoning does not contradict the oracle and invents no code)

### CORRECTED REASONING
(the faithful reasoning with any fixes from verification; if nothing needed fixing, restate it cleanly)
"""


def parse_sections(content: str) -> dict | None:
    matches = list(_HEADER_RE.finditer(content))
    if len(matches) < len(_HEADERS):
        return None
    found = {}
    for i, m in enumerate(matches):
        end = matches[i + 1].start() if i + 1 < len(matches) else len(content)
        found[m.group(1)] = content[m.end() : end].strip()
    if not all(found.get(h) for h in _HEADERS):
        return None
    return {
        "faithful": found["FAITHFUL REASONING"],
        "verification": found["VERIFICATION"],
        "corrected": found["CORRECTED REASONING"],
    }
