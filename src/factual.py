from __future__ import annotations

from dataclasses import dataclass, field

from ast_grep_py import SgNode, SgRoot


@dataclass
class Facts:
    sexp: str
    functions: list[str] = field(default_factory=list)
    comparisons: list[dict[str, str]] = field(default_factory=list)
    returns: list[str] = field(default_factory=list)


def parse(source: str) -> SgNode:
    return SgRoot(source, "python").root()


def canonical_sexp(node: SgNode) -> str:
    def walk(n: SgNode) -> str:
        named = [c for c in n.children() if c.is_named()]
        if not named:
            return f"({n.kind()})"
        return f"({n.kind()} {' '.join(walk(c) for c in named)})"

    return walk(node)


def enclosing_function(source: str, point: tuple[int, int]) -> str | None:
    target: str | None = None

    def visit(n: SgNode) -> None:
        nonlocal target
        if n.kind() == "function_definition":
            rng = n.range()
            if (rng.start.line, rng.start.column) <= point < (rng.end.line, rng.end.column):
                target = n.field("name").text()
        for c in n.children():
            visit(c)

    visit(parse(source))
    return target


def extract(source: str) -> Facts:
    root = parse(source)
    facts = Facts(sexp=canonical_sexp(root))

    def visit(n: SgNode) -> None:
        kind = n.kind()
        if kind == "function_definition":
            facts.functions.append(n.field("name").text())
        elif kind == "comparison_operator":
            left, op, right = n.children()
            facts.comparisons.append({"left": left.text(), "op": op.text(), "right": right.text()})
        elif kind == "return_statement":
            facts.returns.append(next(c for c in n.children() if c.is_named()).text())
        for c in n.children():
            visit(c)

    visit(root)
    return facts
