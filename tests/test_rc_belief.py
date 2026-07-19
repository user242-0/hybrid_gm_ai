import copy
import json
import math

import pytest
import yaml

from src.rc_belief import (
    build_rc_belief_from_memory,
    get_actor_beliefs,
    project_memory_to_rc_belief,
    project_pending_rc_beliefs,
    update_actor_belief,
)
from src.world_defaults import apply_world_defaults


ACTOR_ID = "刑事"


def _memory(**overrides):
    source_event_id = overrides.pop(
        "source_event_id",
        (
            "operation_transition:刑事:op_inquiry_刑事:start:target_selected:"
            "mini_goal_choose_first_inquiry_target"
        ),
    )
    actor_id = overrides.pop("actor_id", ACTOR_ID)
    memory = {
        "schema_version": "rc_memory_v0.1",
        "memory_id": f"memory:{actor_id}:{source_event_id}",
        "kind": "operation_progress",
        "memory_key": "first_inquiry_target_selected",
        "actor_id": actor_id,
        "summary": "最初の聞き込み先を選んだ",
        "source_event_id": source_event_id,
    }
    memory.update(overrides)
    return memory


def _belief(**overrides):
    source_memory_ids = overrides.pop(
        "source_memory_ids",
        [_memory()["memory_id"]],
    )
    belief = {
        "schema_version": "rc_belief_v0.1",
        "belief_id": "first_inquiry_target_selected",
        "kind": "operation_state",
        "actor_id": ACTOR_ID,
        "proposition": "最初の聞き込み先は選定済みである",
        "value": True,
        "confidence": 1.0,
        "source_memory_ids": source_memory_ids,
    }
    belief.update(overrides)
    return belief


def test_builder_creates_exact_deterministic_belief_without_mutating_memory():
    memory = _memory()
    before = copy.deepcopy(memory)

    first = build_rc_belief_from_memory(memory)
    second = build_rc_belief_from_memory(memory)

    assert first == _belief()
    assert second == first
    assert memory == before
    assert type(first["value"]) is bool
    assert type(first["confidence"]) is float


def test_builder_belief_is_json_yaml_and_deepcopy_safe():
    belief = build_rc_belief_from_memory(_memory())

    assert json.loads(json.dumps(belief, ensure_ascii=False)) == belief
    assert yaml.safe_load(yaml.safe_dump(belief, allow_unicode=True)) == belief
    assert copy.deepcopy(belief) == belief
    assert belief["proposition"] == "最初の聞き込み先は選定済みである"


@pytest.mark.parametrize("memory", [None, [], "memory", 1])
def test_builder_rejects_non_dict_memory(memory):
    assert build_rc_belief_from_memory(memory) is None


@pytest.mark.parametrize(
    "field",
    [
        "schema_version",
        "memory_id",
        "kind",
        "memory_key",
        "actor_id",
        "summary",
        "source_event_id",
    ],
)
def test_builder_rejects_missing_required_memory_field(field):
    memory = _memory()
    memory.pop(field)

    assert build_rc_belief_from_memory(memory) is None


@pytest.mark.parametrize("invalid", [None, "", "   ", 1, [], {}])
@pytest.mark.parametrize(
    "field",
    [
        "schema_version",
        "memory_id",
        "kind",
        "memory_key",
        "actor_id",
        "summary",
        "source_event_id",
    ],
)
def test_builder_rejects_invalid_required_memory_value(field, invalid):
    assert build_rc_belief_from_memory(
        _memory(**{field: invalid})
    ) is None


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("schema_version", "rc_memory_v0.2"),
        ("kind", "other"),
        ("memory_key", "other"),
        ("actor_id", "愉快犯"),
    ],
)
def test_builder_requires_exact_structured_memory_signature(field, value):
    memory = _memory(**{field: value})
    if field == "actor_id":
        memory["memory_id"] = f"memory:{value}:{memory['source_event_id']}"

    assert build_rc_belief_from_memory(memory) is None


def test_builder_rejects_memory_id_source_event_inconsistency():
    assert build_rc_belief_from_memory(
        _memory(memory_id="memory:刑事:forged")
    ) is None


def test_builder_summary_text_is_not_a_rule_selector():
    memory = _memory(summary="表現を変更した決定的な記憶文")

    belief = build_rc_belief_from_memory(memory)

    assert belief == _belief()


def test_updater_lazily_creates_root_and_bucket_and_returns_detached_copy():
    world = {"unrelated": {"preserve": True}}
    belief = _belief()

    returned = update_actor_belief(world, belief)

    assert world["actor_beliefs"] == {
        ACTOR_ID: {"first_inquiry_target_selected": belief}
    }
    assert world["unrelated"] == {"preserve": True}
    returned["proposition"] = "changed"
    belief["proposition"] = "source changed"
    assert world["actor_beliefs"][ACTOR_ID][
        "first_inquiry_target_selected"
    ] == _belief()


@pytest.mark.parametrize(
    "belief",
    [
        None,
        {},
        _belief(value=1),
        _belief(confidence=1),
        _belief(confidence=float("inf")),
        _belief(confidence=float("nan")),
        _belief(source_memory_ids=[]),
        _belief(source_memory_ids=["duplicate", "duplicate"]),
    ],
)
def test_updater_rejects_invalid_belief_without_creating_root(belief):
    world = {}

    assert update_actor_belief(world, belief) is None
    assert "actor_beliefs" not in world


@pytest.mark.parametrize(
    "world",
    [
        {"actor_beliefs": []},
        {"actor_beliefs": {ACTOR_ID: None}},
        {"actor_beliefs": {ACTOR_ID: []}},
        {"actor_beliefs": {ACTOR_ID: "invalid"}},
    ],
)
def test_updater_does_not_replace_invalid_existing_root_or_bucket(world):
    before = copy.deepcopy(world)

    assert update_actor_belief(world, _belief()) is None
    assert world == before


def test_updater_is_idempotent_for_same_source_and_return_is_detached():
    world = {}
    first = update_actor_belief(world, _belief())
    before_duplicate = copy.deepcopy(world)

    duplicate = update_actor_belief(world, _belief())

    assert duplicate == first
    assert world == before_duplicate
    duplicate["source_memory_ids"].append("changed")
    assert world == before_duplicate


def test_updater_appends_only_new_sources_in_input_order():
    first_source = _memory()["memory_id"]
    second_source = _memory(
        source_event_id="operation_transition:刑事:instance_2"
    )["memory_id"]
    third_source = _memory(
        source_event_id="operation_transition:刑事:instance_3"
    )["memory_id"]
    world = {}
    update_actor_belief(world, _belief())

    updated = update_actor_belief(
        world,
        _belief(source_memory_ids=[first_source, second_source, third_source]),
    )

    assert updated["source_memory_ids"] == [
        first_source,
        second_source,
        third_source,
    ]
    assert world["actor_beliefs"][ACTOR_ID][
        "first_inquiry_target_selected"
    ]["source_memory_ids"] == updated["source_memory_ids"]


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("schema_version", "rc_belief_v0.2"),
        ("belief_id", "other"),
        ("kind", "other"),
        ("actor_id", "愉快犯"),
        ("proposition", "異なる命題"),
        ("value", False),
        ("confidence", 0.5),
    ],
)
def test_updater_rejects_conflict_without_mutating_world(field, value):
    world = {
        "actor_beliefs": {
            ACTOR_ID: {"first_inquiry_target_selected": _belief(**{field: value})}
        }
    }
    before = copy.deepcopy(world)

    assert update_actor_belief(world, _belief()) is None
    assert world == before


def test_updater_does_not_repair_malformed_existing_belief():
    world = {
        "actor_beliefs": {
            ACTOR_ID: {"first_inquiry_target_selected": {"malformed": True}}
        }
    }
    before = copy.deepcopy(world)

    assert update_actor_belief(world, _belief()) is None
    assert world == before


def test_updater_keeps_actor_buckets_separate():
    trickster_belief = _belief(actor_id="愉快犯")
    world = {}

    update_actor_belief(world, _belief())
    update_actor_belief(world, trickster_belief)

    assert world["actor_beliefs"][ACTOR_ID] == {
        "first_inquiry_target_selected": _belief()
    }
    assert world["actor_beliefs"]["愉快犯"] == {
        "first_inquiry_target_selected": trickster_belief
    }


def test_live_coordinator_builds_and_updates_one_belief():
    world = {}

    projected = project_memory_to_rc_belief(world, _memory())

    assert projected == _belief()
    assert world["actor_beliefs"] == {
        ACTOR_ID: {"first_inquiry_target_selected": _belief()}
    }


def test_catch_up_projects_memory_only_world_and_is_idempotent():
    world = {"actor_memories": {ACTOR_ID: [_memory()]}}
    memories_before = copy.deepcopy(world["actor_memories"])

    first = project_pending_rc_beliefs(world)
    after_first = copy.deepcopy(world)
    second = project_pending_rc_beliefs(world)

    assert first == [_belief()]
    assert second == []
    assert world == after_first
    assert world["actor_memories"] == memories_before


def test_catch_up_returns_source_reinforcement_as_changed_belief():
    second_memory = _memory(
        source_event_id="operation_transition:刑事:instance_2"
    )
    world = {
        "actor_memories": {ACTOR_ID: [_memory(), second_memory]},
        "actor_beliefs": {
            ACTOR_ID: {"first_inquiry_target_selected": _belief()}
        },
    }

    changed = project_pending_rc_beliefs(world)

    assert len(changed) == 1
    assert changed[0]["source_memory_ids"] == [
        _memory()["memory_id"],
        second_memory["memory_id"],
    ]


def test_catch_up_skips_bad_memories_and_continues_in_bucket_order():
    supported = _memory()
    world = {
        "actor_memories": {
            "broken_actor": "invalid bucket",
            ACTOR_ID: [
                {"malformed": True},
                _memory(memory_key="unsupported"),
                supported,
            ],
        }
    }

    changed = project_pending_rc_beliefs(world)

    assert changed == [_belief()]
    assert world["actor_memories"][ACTOR_ID][-1] is supported


def test_catch_up_rejects_bucket_actor_memory_actor_mismatch():
    world = {"actor_memories": {"愉快犯": [_memory()]}}
    before = copy.deepcopy(world)

    assert project_pending_rc_beliefs(world) == []
    assert world == before


@pytest.mark.parametrize(
    "operation_state",
    [
        None,
        {"phase": "later"},
        {"phase": "completed", "mini_goal": None},
    ],
)
def test_catch_up_does_not_require_current_operation(operation_state):
    world = {
        "actor_memories": {ACTOR_ID: [_memory()]},
        "actor_operations": {
            ACTOR_ID: {"active_operation": operation_state}
        },
    }

    assert project_pending_rc_beliefs(world) == [_belief()]


def test_catch_up_does_not_replace_invalid_belief_root_or_bucket():
    invalid_root = {
        "actor_memories": {ACTOR_ID: [_memory()]},
        "actor_beliefs": [],
    }
    invalid_bucket = {
        "actor_memories": {ACTOR_ID: [_memory()]},
        "actor_beliefs": {ACTOR_ID: []},
    }
    root_before = copy.deepcopy(invalid_root)
    bucket_before = copy.deepcopy(invalid_bucket)

    assert project_pending_rc_beliefs(invalid_root) == []
    assert project_pending_rc_beliefs(invalid_bucket) == []
    assert invalid_root == root_before
    assert invalid_bucket == bucket_before


def test_reader_returns_only_valid_actor_keyed_records_as_deepcopy():
    detective = _belief()
    trickster = _belief(actor_id="愉快犯")
    world = {
        "actor_beliefs": {
            ACTOR_ID: {
                "first_inquiry_target_selected": detective,
                "wrong_key": _belief(),
                "malformed": {"invalid": True},
                "wrong_actor": trickster,
            },
            "愉快犯": {"first_inquiry_target_selected": trickster},
        }
    }
    before = copy.deepcopy(world)

    result = get_actor_beliefs(world, ACTOR_ID)

    assert result == {"first_inquiry_target_selected": detective}
    result["first_inquiry_target_selected"]["value"] = False
    assert world == before


@pytest.mark.parametrize(
    "world",
    [
        None,
        {},
        {"actor_beliefs": []},
        {"actor_beliefs": {ACTOR_ID: []}},
    ],
)
def test_reader_returns_empty_for_missing_or_invalid_state(world):
    assert get_actor_beliefs(world, ACTOR_ID) == {}


def test_belief_survives_serialization_and_world_defaults():
    world = {"actor_memories": {ACTOR_ID: [_memory()]}}
    project_pending_rc_beliefs(world)
    beliefs = world["actor_beliefs"]

    assert json.loads(json.dumps(beliefs, ensure_ascii=False)) == beliefs
    loaded = yaml.safe_load(yaml.safe_dump(beliefs, allow_unicode=True))
    assert loaded == beliefs
    assert copy.deepcopy(beliefs) == beliefs

    merged = apply_world_defaults(
        copy.deepcopy(world),
        {"world_defaults": {"investigation_progress": 0}},
    )
    assert merged["actor_beliefs"] == beliefs
