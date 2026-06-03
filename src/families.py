from typing import Literal

ConceptFamily = Literal[
    "CONTROL_FLOW",
    "BOOLEAN_LOGIC",
    "COMPARISON_BOUNDARY",
    "LOOP_STRUCTURE",
    "DATA_FLOW",
    "VARIABLE_SCOPE",
    "FUNCTION_CALL",
    "RETURN_FLOW",
    "EXCEPTION_FLOW",
    "TYPE_ASSUMPTION",
    "MUTABILITY",
    "ALIASING",
    "API_CONTRACT",
]

_KIND_FAMILY = {
    "comparison_operator": "COMPARISON_BOUNDARY",
    "boolean_operator": "BOOLEAN_LOGIC",
    "true": "BOOLEAN_LOGIC",
    "false": "BOOLEAN_LOGIC",
    "return_statement": "RETURN_FLOW",
    "binary_operator": "DATA_FLOW",
}


def family_of(node) -> ConceptFamily:
    kind = node.kind()
    if kind == "call":
        callee = node.children()[0].text() if node.children() else ""
        return "LOOP_STRUCTURE" if callee == "range" else "FUNCTION_CALL"
    return _KIND_FAMILY.get(kind, "DATA_FLOW")
