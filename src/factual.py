from __future__ import annotations

from ast_grep_py import SgNode, SgRoot


def parse(source: str) -> SgNode:
    return SgRoot(source, "python").root()


def enclosing_function(source: str, point: tuple[int, int]) -> SgNode | None:
    target: SgNode | None = None

    def visit(n: SgNode) -> None:
        nonlocal target
        if n.kind() == "function_definition":
            rng = n.range()
            if (rng.start.line, rng.start.column) <= point < (rng.end.line, rng.end.column):
                target = n
        for c in n.children():
            visit(c)

    visit(parse(source))
    return target
