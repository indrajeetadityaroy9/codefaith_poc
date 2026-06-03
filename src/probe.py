from __future__ import annotations

import argparse
import ast
import asyncio
import inspect
import json
import pathlib
import re
from collections import Counter

from . import counterfactual, oracle
from .llm import LLMConfig, chat, make_client
from .loader import load_corpus

_CODE_BLOCK = re.compile(r"```(?:python)?\s*(.*?)```", re.DOTALL)
_LIST = re.compile(r"\[[^\[\]]*\]")
_NUM = re.compile(r"-?\d+")


def _extract_literal(text):
    text = _CODE_BLOCK.sub("", text)  # drop code blocks so list-comps aren't mistaken for outputs
    lists = _LIST.findall(text)
    return ast.literal_eval(lists[-1] if lists else _NUM.findall(text)[-1])


def function_under_test(source):
    ns = oracle._load(source)
    return next(name for name, value in ns.items() if inspect.isfunction(value))


def _call(target, probe_input):
    return f"{target}(" + ", ".join(repr(v) for v in probe_input.values()) + ")"


def prediction_prompt(source, call):
    return f"""```python
{source}```

What does `{call}` return? Reply with ONLY the Python literal value."""


def interventions(source):
    """AST counterfactual + oracle = the interventions. Each behavior-changing edit
    yields a discriminating input where the original (reference) and edited program differ."""
    target = function_under_test(source)
    out = []
    for cf in counterfactual.generate(source):
        verdict, evidence = oracle.compare(source, cf.counterfactual, target)
        if verdict == "diverged":
            out.append((target, cf, evidence))
    return out


async def assess(client, source, target, cf, evidence, cfg, sem):
    async with sem:
        probe_input = evidence["input"]
        reference_output = evidence["factual_output"]
        counterfactual_output = evidence["counterfactual_output"]
        call = _call(target, probe_input)
        _, response = await chat(client, [{"role": "user", "content": prediction_prompt(source, call)}], cfg)
        model_prediction = _extract_literal(response)
        if model_prediction == reference_output:
            label = "faithful"           # tracks the reference at the operator-sensitive input
        elif model_prediction == counterfactual_output:
            label = "unfaithful"         # behaved as if the flipped operator were in force
        else:
            label = "inconclusive"
        return {
            "function": target,
            "factual_code": source,
            "operator": cf.operator,
            "family": cf.family,
            "intervention": f"{cf.matched_text} -> {cf.replacement_text}",
            "counterfactual_code": cf.counterfactual,
            "probe_input": probe_input,
            "reference_output": reference_output,
            "counterfactual_output": counterfactual_output,
            "model_prediction": model_prediction,
            "faithfulness_label": label,
            "model": cfg.model,
        }


async def _evaluate_all(sources, cfg):
    client = make_client(cfg)
    sem = asyncio.Semaphore(cfg.concurrency)
    tasks = [
        assess(client, source, target, cf, evidence, cfg, sem)
        for source in sources
        for (target, cf, evidence) in interventions(source)
    ]
    try:
        return await asyncio.gather(*tasks)
    finally:
        await client.close()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("corpus_dir")
    args = ap.parse_args()

    cfg = LLMConfig.from_env()
    sources = list(load_corpus(args.corpus_dir).values())
    rows = asyncio.run(_evaluate_all(sources, cfg))

    out = pathlib.Path("out/faithfulness.jsonl")
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w") as f:
        for row in rows:
            f.write(json.dumps(row, default=repr) + "\n")

    counts = Counter(r["faithfulness_label"] for r in rows)
    print(f"assessed {len(rows)} interventions -> {out}")
    for label in ("faithful", "unfaithful", "inconclusive"):
        if counts[label]:
            print(f"  {label}: {counts[label]}")


if __name__ == "__main__":
    main()
