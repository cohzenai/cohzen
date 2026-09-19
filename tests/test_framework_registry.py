"""Unit tests for FrameworkRegistry and custom framework extension."""

import ast
from typing import List
import pytest

from cz.scanner.models import GraphInfo
from cz.detectors.base import BaseFrameworkScanner
from cz.detectors.registry import FrameworkRegistry


class MockCustomFrameworkScanner:
    def __init__(self):
        self.framework_name = "mock_agentic"
        self.detected = []

    def reset(self, file_path: str):
        self.detected = []

    def visit_assign(self, targets: List[ast.AST], value: ast.AST, lineno: int):
        if isinstance(value, ast.Call) and getattr(value.func, "id", "") == "CustomAgent":
            self.detected.append(
                GraphInfo(
                    framework=self.framework_name,
                    graph_var="custom_agent_instance",
                    graph_class="CustomAgent",
                    file_path="mock.py",
                    line_number=lineno,
                )
            )

    def visit_call(self, call: ast.Call, lineno: int):
        pass

    def visit_return(self, node: ast.Return):
        pass

    def get_graphs(self) -> List[GraphInfo]:
        return self.detected


def test_framework_registry_extension():
    registry = FrameworkRegistry()
    assert any(s.framework_name == "langgraph" for s in registry.get_all())

    # Register custom framework
    mock_scanner = MockCustomFrameworkScanner()
    registry.register(mock_scanner)
    assert len(registry.get_all()) == 2

    # Verify visit_assign reaches custom scanner
    tree = ast.parse("agent = CustomAgent()")
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign):
            for s in registry.get_all():
                s.visit_assign(node.targets, node.value, node.lineno)

    graphs = mock_scanner.get_graphs()
    assert len(graphs) == 1
    assert graphs[0].framework == "mock_agentic"
