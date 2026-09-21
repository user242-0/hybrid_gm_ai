"""Architectural checks for Operation ownership, not a Python security sandbox."""

import ast
from pathlib import Path

import pytest

from src import operation_reader
from src.operation_store import OperationStore


SRC = Path(__file__).resolve().parents[1] / "src"
WRITER_IMPORTERS = {
    "src.operation_store": {
        "actor_operations.py", "operation_progression.py",
        "operation_reader.py", "world_defaults.py",
    },
    "src.actor_operations": {"operation_runtime.py"},
    "src.operation_progression": {"operation_runtime.py"},
}


def _boundary_violations(source, path):
    violations = []
    for node in ast.walk(ast.parse(source)):
        # Also catches assigning the key to a variable before indexing. Dynamic
        # string construction/reflection and generic world transport are not
        # proved safe by this intentionally small architecture check.
        if (isinstance(node, ast.Constant) and node.value == "actor_operations"
                and path != "operation_store.py"):
            violations.append((node.lineno, "Operation storage key outside Store"))
        modules = []
        if isinstance(node, ast.Import):
            modules = [alias.name for alias in node.names]
        elif isinstance(node, ast.ImportFrom):
            module = node.module or ""
            if node.level:
                parent = ["src", *Path(path).parts[:-1]]
                module = ".".join(parent[:len(parent) - node.level + 1]
                                  + ([module] if module else []))
            modules = [module, *(f"{module}.{alias.name}" for alias in node.names)]
        for module in modules:
            if module in WRITER_IMPORTERS and path not in WRITER_IMPORTERS[module]:
                violations.append((node.lineno, f"Unexpected writer dependency: {module}"))
    return violations


def test_runtime_source_keeps_storage_key_and_writer_dependencies_in_boundary():
    violations = []
    for path in SRC.rglob("*.py"):
        relative = path.relative_to(SRC).as_posix()
        violations.extend(
            (relative, line, reason)
            for line, reason in _boundary_violations(
                path.read_text(encoding="utf-8-sig"), relative
            )
        )
    assert violations == []


@pytest.mark.parametrize("source", [
    'world["actor_operations"]',
    'world.get("actor_operations")',
    'world.setdefault("actor_operations", {})',
    'key = "actor_operations"; world[key] = {}',
    'from src.operation_store import OperationStore as Writer',
    'from src import operation_store',
    'from ..operation_store import OperationStore',
    'import src.actor_operations as operations',
    'from src.operation_progression import advance_operation_after_action',
])
def test_guard_detects_direct_storage_access_and_writer_imports_in_reader(source):
    assert _boundary_violations(source, "ui/example.py")


def test_reader_api_exposes_no_store_or_write_callable():
    world = {}
    OperationStore(world).set_active_operation("actor", {"notes": [{"text": "saved"}]})
    result = operation_reader.get_active_operation(world, "actor")
    result["notes"][0]["text"] = "local"
    assert operation_reader.get_active_operation(world, "actor")["notes"] == [
        {"text": "saved"}
    ]
    for name in ("OperationStore", "set_active_operation", "clear_active_operation",
                 "ensure_actor_operations", "start_operation_once"):
        assert not hasattr(operation_reader, name)


def test_reader_uses_current_world_after_load_without_retaining_old_store():
    old_world, loaded_world = {}, {}
    OperationStore(old_world).set_active_operation("actor", {"phase": "start"})
    OperationStore(loaded_world).set_active_operation("actor", {"phase": "loaded"})
    assert operation_reader.get_active_operation(old_world, "actor")["phase"] == "start"
    assert operation_reader.get_active_operation(loaded_world, "actor")["phase"] == "loaded"
