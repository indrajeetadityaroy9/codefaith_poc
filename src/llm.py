from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class LLMConfig:
    base_url: str
    model: str
    api_key: str
    temperature: float
    seed: int
    max_tokens: int = 4096
    concurrency: int = 8
    request_timeout: float = 1800.0

    @classmethod
    def from_env(cls) -> "LLMConfig":
        return cls(
            base_url=os.environ.get("CODEFAITH_BASE_URL", "http://localhost:8000/v1"),
            model=os.environ.get("CODEFAITH_MODEL", "Kaleto/DeepSeek-R1-Distill-Llama-70B-NVFP4"),
            api_key=os.environ.get("CODEFAITH_API_KEY", "EMPTY"),
            temperature=float(os.environ.get("CODEFAITH_TEMPERATURE", "0.6")),
            seed=int(os.environ.get("CODEFAITH_SEED", "0")),
            concurrency=int(os.environ.get("CODEFAITH_CONCURRENCY", "8")),
            request_timeout=float(os.environ.get("CODEFAITH_TIMEOUT", "1800")),
        )


def make_client(cfg: LLMConfig):
    from openai import AsyncOpenAI

    return AsyncOpenAI(base_url=cfg.base_url, api_key=cfg.api_key,
                       timeout=cfg.request_timeout, max_retries=0)


async def chat(client, messages: list[dict], cfg: LLMConfig) -> tuple[str | None, str]:
    resp = await client.chat.completions.create(
        model=cfg.model,
        messages=messages,
        temperature=cfg.temperature,
        top_p=0.95,
        seed=cfg.seed,
        max_tokens=cfg.max_tokens,
    )
    msg = resp.choices[0].message
    return getattr(msg, "reasoning_content", None), msg.content
