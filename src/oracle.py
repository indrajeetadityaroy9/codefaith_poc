from __future__ import annotations

import inspect
import itertools


class _Attr:
    def __init__(self, value: bool):
        self._value = value

    def __getattr__(self, name: str) -> bool:
        return self._value

    def __repr__(self) -> str:
        return f"Attr({self._value})"


ALL_TRUE = _Attr(True)
ALL_FALSE = _Attr(False)
POOL = [0, 1, -1, 18, 100, True, False, [1, 2, 3], ALL_TRUE, ALL_FALSE]

_POSITIONAL = (inspect.Parameter.POSITIONAL_ONLY, inspect.Parameter.POSITIONAL_OR_KEYWORD)


def _run(fn, args: tuple) -> tuple[str, object]:
    try:
        return ("ok", fn(*args))
    except Exception as exc:
        return ("err", type(exc).__name__)


def _load(source: str) -> dict:
    ns: dict = {}
    exec(compile(source, "<oracle>", "exec"), ns)
    return ns


def compare(factual_src: str, counterfactual_src: str, func_name: str) -> tuple[str, str | None]:
    fn_f = _load(factual_src)[func_name]
    fn_c = _load(counterfactual_src)[func_name]
    arity = sum(1 for p in inspect.signature(fn_f).parameters.values() if p.kind in _POSITIONAL)

    clean = 0
    for args in itertools.product(POOL, repeat=arity):
        out_f = _run(fn_f, args)
        out_c = _run(fn_c, args)
        if out_f != out_c:
            return "diverged", repr(args)
        if out_f[0] == "ok" and out_c[0] == "ok":
            clean += 1
    return ("equivalent" if clean else "indeterminate"), None
