# codefaith — POC

Turn Python files into a labeled dataset of "what does this small code edit actually do," then have an AI write — and double-check — a plain-English explanation of each label.

It runs in two stages. **The AI never decides the label; it only explains it.**

## Stage 1 — find the truth (no AI)

1. Read a folder of `.py` files.
2. Make one tiny edit at a time, e.g. change `age >= 18` to `age < 18`. Each edit is tagged with a **concept family** read straight from the code's syntax tree via ast-grep (comparison, boolean logic, return, loop, function call, …).
3. Keep only edits that still compile.
4. Run the original and the edited function on a fixed set of test inputs and compare the outputs. This sets the **label**:
   - `diverged` — the outputs differ, so the edit changed behavior. We also save the exact input and both outputs as proof.
   - `equivalent` — the outputs match on every test input.
   - `indeterminate` — we can't tell, because the function uses randomness, time, or I/O, so the test can't be trusted.
5. Write everything to `out/ground_truth.jsonl`. The syntax tree plus the test run are the **only** things that set the label.

Run it: `uv run python -m src.run samples`

## Stage 2 — explain, then verify (AI)

A local reasoning model (DeepSeek-R1-Distill-Llama-70B, served with vLLM in Docker) reads each labeled record and writes **three short traces**:

1. **Faithful reasoning** — why the label is what it is, using only the given facts (the edit, the concept family, the test evidence).
2. **Verification** — the model checks its own explanation: does it match the label, does it cite the proof, did it make anything up?
3. **Corrected reasoning** — the explanation again, with anything the check caught fixed.

Each trace must pass two gates, or it is thrown out (to `out/rejected.jsonl`):

- **Automatic checks** — it must name the concept family, mention the before/after of the edit, and quote the test evidence, and it must not contradict the label or invent code.
- **Self-check** — the model is asked once more whether its explanation is faithful.

The label is copied straight from Stage 1, so the model can only explain a record or get rejected — it can never change the label. Accepted records are written to `out/benchmark.jsonl`, each carrying its three traces.

Run it (model served via Docker, GPU):

```
docker compose up -d vllm        # serve the model
docker compose run --rm tracegen # generate + verify traces
```

Or point at any OpenAI-compatible endpoint and run on the host:

```
uv run --extra llm python -m src.tracegen out/ground_truth.jsonl
```
