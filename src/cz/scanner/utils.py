"""AST utility helper functions shared across frameworks, LLMs, and tool scanners."""

from __future__ import annotations

import ast
from typing import Dict, List, Optional


def ast_to_str(node: ast.AST | None) -> str:
    """Safely convert an AST expression node to a human-readable string representation."""
    if node is None:
        return ""
    if isinstance(node, ast.Constant):
        return str(node.value)
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        value_str = ast_to_str(node.value)
        return f"{value_str}.{node.attr}" if value_str else node.attr
    if isinstance(node, ast.Call):
        func_name = ast_to_str(node.func)
        args_strs = [ast_to_str(arg) for arg in node.args]
        for kw in node.keywords:
            if kw.arg:
                args_strs.append(f"{kw.arg}={ast_to_str(kw.value)}")
        return f"{func_name}({', '.join(args_strs)})"
    if isinstance(node, ast.List):
        return "[" + ", ".join(ast_to_str(el) for el in node.elts) + "]"
    if isinstance(node, ast.Tuple):
        return "(" + ", ".join(ast_to_str(el) for el in node.elts) + ")"
    if isinstance(node, ast.Dict):
        pairs = []
        for k, v in zip(node.keys, node.values):
            k_str = ast_to_str(k)
            v_str = ast_to_str(v)
            pairs.append(f"{k_str}: {v_str}")
        return "{" + ", ".join(pairs) + "}"
    if isinstance(node, ast.BinOp) and isinstance(node.op, ast.BitOr):
        return f"{ast_to_str(node.left)} | {ast_to_str(node.right)}"
    try:
        return ast.unparse(node)
    except Exception:
        return str(type(node).__name__)


def extract_list_of_strings(node: ast.AST | None) -> List[str]:
    """Extract a list of string literals or identifiers from an AST List/Tuple."""
    if not node:
        return []
    if isinstance(node, (ast.List, ast.Tuple)):
        return [ast_to_str(el).strip("'\"") for el in node.elts]
    return [ast_to_str(node).strip("'\"")]


def extract_dict_mapping(node: ast.AST | None) -> Dict[str, str]:
    """Extract a mapping from an AST Dict node."""
    if not isinstance(node, ast.Dict):
        return {}
    mapping: Dict[str, str] = {}
    for k, v in zip(node.keys, node.values):
        k_str = ast_to_str(k).strip("'\"")
        v_str = ast_to_str(v).strip("'\"")
        mapping[k_str] = v_str
    return mapping


def get_decorator_names(decorator_list: List[ast.AST]) -> List[str]:
    """Extract decorator base names (e.g. 'tool', 'traceable', 'observe')."""
    names: List[str] = []
    for d in decorator_list:
        if isinstance(d, ast.Name):
            names.append(d.id)
        elif isinstance(d, ast.Attribute):
            names.append(d.attr)
        elif isinstance(d, ast.Call):
            if isinstance(d.func, ast.Name):
                names.append(d.func.id)
            elif isinstance(d.func, ast.Attribute):
                names.append(d.func.attr)
    return names
