"""Lossless conversion and isolation contracts before runtime integration."""

from copy import deepcopy
from dataclasses import FrozenInstanceError
import json

import pytest
import yaml

from src.actor_operations import start_operation_once
from src.operation_instance import OperationInstance


def _record():
    return {
        "id": "op_inquiry_刑事", "type": "inquiry", "actor_id": "刑事",
        "label": "聞き込み", "status": "active", "phase": "start",
        "target_id": None, "parent_microgoal_id": None, "created_from": "HUD",
        "mini_goal": {"id": "first", "status": "active", "extra": [1]},
        "notes": [{"text": "keep"}],
        "metadata": {"nested": [{"values": [1]}]},
    }


@pytest.mark.parametrize("record", [
    _record(), {}, {"notes": []}, {"phase": None},
    {"phase": "", "mini_goal": None},
    {"id": 7, "status": False, "mini_goal": ["legacy"], "notes": None},
])
def test_roundtrip_preserves_missing_null_malformed_and_unknown_fields(record):
    before = deepcopy(record)
    instance = OperationInstance.from_dict(record)
    assert instance.to_dict() == before
    assert record == before
    assert set(instance.to_dict()) == set(before)


@pytest.mark.parametrize("construct", [OperationInstance, OperationInstance.from_dict])
def test_construction_detaches_input_at_every_depth(construct):
    source = _record()
    expected = deepcopy(source)
    instance = construct(source)
    source["mini_goal"]["extra"].append(2)
    source["notes"][0]["text"] = "changed"
    source["metadata"]["nested"][0]["values"].clear()
    source["phase"] = "changed"
    assert instance.to_dict() == expected


def test_exports_and_field_reads_cannot_mutate_instance_or_each_other():
    instance = OperationInstance.from_dict(_record())
    first, second = instance.to_dict(), instance.to_dict()
    first["mini_goal"]["extra"].append(2)
    first["notes"][0]["text"] = "changed"
    first["metadata"]["nested"][0]["values"].clear()
    instance.get("mini_goal")["extra"].clear()
    instance.get("notes")[0]["text"] = "field mutation"
    instance.get("metadata")["nested"].clear()
    assert second == _record()
    assert instance.to_dict() == _record()


def test_missing_and_null_are_distinct_and_read_does_not_add_fields():
    instance = OperationInstance.from_dict({"phase": None})
    default = {"values": []}
    assert instance.get("phase", "fallback") is None
    assert instance.get("status", "fallback") == "fallback"
    instance.get("missing", default)["values"].append(1)
    assert default == {"values": []}
    assert instance.to_dict() == {"phase": None}


def test_changes_replace_nested_fields_and_preserve_other_data_independently():
    original = OperationInstance.from_dict(_record())
    mini_goal = {"id": "next", "extra": []}
    updated = original.with_changes(phase="next", mini_goal=mini_goal)
    mini_goal["extra"].append("input mutation")
    expected = _record()
    expected.update(phase="next", mini_goal={"id": "next", "extra": []})
    exported = updated.to_dict()
    assert exported == expected
    exported["notes"][0]["text"] = "output mutation"
    exported["metadata"]["nested"].clear()
    assert updated.to_dict() == expected
    assert original.to_dict() == _record()
    assert original.with_changes() is not original


def test_changes_can_explicitly_set_null_without_filling_missing_fields():
    original = OperationInstance.from_dict({"phase": "start"})
    assert original.with_changes(phase=None).to_dict() == {"phase": None}
    assert original.to_dict() == {"phase": "start"}


@pytest.mark.parametrize("record", [None, [], "invalid", 1])
def test_non_dict_is_rejected_without_implicit_empty_operation(record):
    with pytest.raises(TypeError, match="dict record"):
        OperationInstance.from_dict(record)


def test_instance_disallows_field_reassignment():
    instance = OperationInstance.from_dict(_record())
    with pytest.raises(FrozenInstanceError):
        instance._record = {}


def test_existing_start_record_roundtrips_without_writing_world():
    world = {}
    record = start_operation_once(
        world, "刑事", operation_type="inquiry", label="聞き込み",
        phase="start", mini_goal={"id": "first", "status": "active"},
    )
    before = deepcopy(world)
    instance = OperationInstance.from_dict(record)
    assert instance.to_dict() == record
    instance.with_changes(phase="next").to_dict()
    assert world == before


def test_existing_json_and_yaml_format_survives_conversion():
    record = _record()
    instance = OperationInstance.from_dict(record)
    for loaded in (
        json.loads(json.dumps(instance.to_dict(), ensure_ascii=False)),
        yaml.safe_load(yaml.safe_dump(instance.to_dict(), allow_unicode=True)),
    ):
        assert OperationInstance.from_dict(loaded).to_dict() == record
