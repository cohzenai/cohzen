"""Tests for isolated node runner and debugger."""

from pathlib import Path
from cz.execution.debugger import get_node_input_from_run, run_isolated_node
from cz.execution.models import Execution, Span
from cz.execution.sqlite import SQLiteExecutionStore


def test_isolated_node_direct_run(tmp_path: Path):
    # Create a small standalone test node module
    test_file = tmp_path / "nodes.py"
    test_file.write_text(
        "def custom_node(state: dict) -> dict:\n"
        "    return {'processed': state.get('input_val', '') + '_done'}\n",
        encoding="utf-8",
    )

    res = run_isolated_node(
        node_name="custom_node",
        input_state={"input_val": "sample"},
        project_dir=tmp_path,
        record=False,
    )

    assert res.status == "completed"
    assert res.node_name == "custom_node"
    assert res.output_state == {"processed": "sample_done"}
    assert res.duration_ms >= 0


def test_get_node_input_from_run(tmp_path: Path):
    db_path = tmp_path / "executions.db"
    store = SQLiteExecutionStore(db_path=db_path)

    exec_obj = Execution(id="test_run_1", graph_id="workflow", status="completed")
    store.create_execution(exec_obj)

    span = Span(
        id="sp_test",
        execution_id="test_run_1",
        kind="node",
        name="target_node",
        input={"user_id": "123", "query": "hello"},
    )
    store.create_span(span)

    retrieved_input = get_node_input_from_run("test_run_1", "target_node", db_path=db_path)
    assert retrieved_input == {"user_id": "123", "query": "hello"}


def test_isolated_node_with_model_string_repr_hydration(tmp_path: Path):
    test_file = tmp_path / "models_and_node.py"
    test_file.write_text(
        "from pydantic import BaseModel\n"
        "from typing import TypedDict\n"
        "class UserInfo(BaseModel):\n"
        "    user_id: int\n"
        "    name: str\n"
        "class AppState(TypedDict):\n"
        "    info: UserInfo\n"
        "def check_user(state: AppState) -> dict:\n"
        "    return {'matched': state['info'].user_id == 777 and state['info'].name == 'Alice'}\n",
        encoding="utf-8",
    )

    # Input state where 'info' is stored as a string representation
    input_state = {
        "info": "user_id=777 name='Alice'"
    }

    res = run_isolated_node(
        node_name="check_user",
        input_state=input_state,
        project_dir=tmp_path,
        record=False,
    )

    assert res.status == "completed"
    assert res.output_state == {"matched": True}

