from __future__ import annotations

import argparse
import asyncio
import json
import os
import pathlib
from collections import Counter

from . import traces, validate
from .llm import LLMConfig, chat, make_client


def subset(records: list[dict], n: int) -> list[dict]:
    buckets: dict[str, list] = {}
    for r in records:
        buckets.setdefault(r["label"], []).append(r)
    queues = list(buckets.values())
    picked: list[dict] = []
    while len(picked) < n and any(queues):
        for q in queues:
            if q and len(picked) < n:
                picked.append(q.pop(0))
    return picked


def make_task(record: dict) -> str:
    return (
        f"You are given a Python function and a single {record['family']} edit to it. Decide whether "
        f"the edit changes the function's behavior, and justify your answer using the structural diff "
        f"and the execution evidence."
    )


async def _generate(client, record, task, cfg, repair=None):
    messages = [{"role": "user", "content": traces.build_user_prompt(record, task, repair)}]
    return await chat(client, messages, cfg)


async def process(client, record: dict, cfg: LLMConfig, verifier: bool, sem: asyncio.Semaphore):
    async with sem:
        task = make_task(record)
        reasoning, content = await _generate(client, record, task, cfg)
        sections = traces.parse_sections(content)
        fails = ["parse_failed"] if sections is None else validate.validate(record, sections)

        if fails:
            reasoning, content = await _generate(client, record, task, cfg, repair=fails)
            sections = traces.parse_sections(content)
            fails = ["parse_failed"] if sections is None else validate.validate(record, sections)

        if fails:
            return None, {"id": record["id"], "failures": fails, "sections": sections, "reasoning_content": reasoning}

        if verifier:
            ok, reason = await validate.self_verify(client, record, sections, cfg)
            if not ok:
                return None, {"id": record["id"], "failures": [f"self_verify_rejected: {reason}"], "sections": sections}

        row = dict(record)
        row["task"] = task
        row["faithful_reasoning_trace"] = sections["faithful"]
        row["verification_trace"] = sections["verification"]
        row["corrected_reasoning_trace"] = sections["corrected"]
        row["reasoning_content"] = reasoning
        row["trace_model"] = cfg.model
        return row, None


async def _run(records, cfg, verifier):
    client = make_client(cfg)
    sem = asyncio.Semaphore(cfg.concurrency)
    try:
        return await asyncio.gather(
            *(process(client, r, cfg, verifier, sem) for r in records),
            return_exceptions=True,
        )
    finally:
        await client.close()


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("ground_truth")
    ap.add_argument("--limit", type=int, default=0, help="process at most N records (0=use CODEFAITH_LIMIT), class-balanced")
    args = ap.parse_args()

    verifier = os.environ.get("CODEFAITH_VERIFIER", "1") == "1"
    cfg = LLMConfig.from_env()

    records = [json.loads(line) for line in open(args.ground_truth)]
    limit = args.limit or int(os.environ.get("CODEFAITH_LIMIT", "3"))
    if limit:
        records = subset(records, limit)

    results = asyncio.run(_run(records, cfg, verifier))
    accepted, rejected = [], []
    for record, res in zip(records, results):
        if isinstance(res, Exception):
            rejected.append({"id": record["id"], "failures": [f"error: {type(res).__name__}: {res}"]})
        else:
            row, rej = res
            (accepted if row is not None else rejected).append(row if row is not None else rej)

    out = pathlib.Path("out/benchmark.jsonl")
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w") as f:
        for row in accepted:
            f.write(json.dumps(row, default=repr) + "\n")
    rej_path = pathlib.Path("out/rejected.jsonl")
    if rejected:
        with rej_path.open("w") as f:
            for rej in rejected:
                f.write(json.dumps(rej, default=repr) + "\n")
    elif rej_path.exists():
        rej_path.unlink()

    print(f"benchmark: {len(accepted)}/{len(results)} accepted -> {out}  (rejected {len(rejected)})  concurrency={cfg.concurrency}")
    if rejected:
        print("rejections:", dict(Counter(f for r in rejected for f in r["failures"])))


if __name__ == "__main__":
    main()
