import copy
import json

import pytest
import yaml

from src.rc_memory import (
    build_rc_memory_from_transition,
    get_recent_actor_memories,
    project_pending_rc_memories,
    project_transition_to_rc_memory,
    record_actor_memory,
)
from src.world_defaults import apply_world_defaults


ACTOR_ID = "刑事"


def _transition_event(**overrides):
    event = {
        "schema_version": "operation_transition_v0.1",
        "kind": "operation_transition",
        "event_id": (
            "operation_transition:刑事:op_inquiry_刑事:start:target_selected:"
            "mini_goal_choose_first_inquiry_target"
        ),
        "actor_id": ACTOR_ID,
        "operation_id": "op_inquiry_刑事",
        "operation_type": "inquiry",
        "from_phase": "start",
        "to_phase": "target_selected",
        "completed_mini_goal_id": "mini_goal_choose_first_inquiry_target",
        "next_mini_goal_id": "mini_goal_take_first_testimony",
        "trigger_action_id": "choose_first_inquiry_target",
        "world_condition": "inquiry_target_chosen",
    }
    event.update(overrides)
    if "operation_id" in overrides and "event_id" not in overrides:
        event["event_id"] = (
            f"operation_transition:{event['actor_id']}:{event['operation_id']}:"
            f"{event['from_phase']}:{event['to_phase']}:"
            f"{event['completed_mini_goal_id']}"
        )
    return event


def _expected_memory(**overrides):
    source_event_id = overrides.pop(
        "source_event_id",
        _transition_event()["event_id"],
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


def test_builder_creates_exact_memory_without_mutating_source_event():
    event = _transition_event()
    before = copy.deepcopy(event)

    first = build_rc_memory_from_transition(event)
    second = build_rc_memory_from_transition(event)

    assert first == _expected_memory()
    assert second == first
    assert event == before


def test_builder_memory_is_json_yaml_and_deepcopy_safe():
    memory = build_rc_memory_from_transition(_transition_event())

    assert json.loads(json.dumps(memory, ensure_ascii=False)) == memory
    assert yaml.safe_load(yaml.safe_dump(memory, allow_unicode=True)) == memory
    assert copy.deepcopy(memory) == memory
    assert "刑事" in memory["memory_id"]


@pytest.mark.parametrize("event", [None, [], "event", 1])
def test_builder_rejects_non_dict_event(event):
    assert build_rc_memory_from_transition(event) is None


@pytest.mark.parametrize(
    "field",
    [
        "schema_version",
        "kind",
        "event_id",
        "actor_id",
        "operation_id",
        "operation_type",
        "from_phase",
        "to_phase",
        "completed_mini_goal_id",
        "next_mini_goal_id",
        "trigger_action_id",
        "world_condition",
    ],
)
def test_builder_rejects_missing_required_transition_field(field):
    event = _transition_event()
    event.pop(field)

    assert build_rc_memory_from_transition(event) is None


@pytest.mark.parametrize("invalid", [None, "", "   ", 1, [], {}])
def test_builder_rejects_invalid_required_transition_value(invalid):
    assert build_rc_memory_from_transition(
        _transition_event(operation_id=invalid, event_id="invalid")
    ) is None


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("schema_version", "operation_transition_v0.2"),
        ("kind", "other"),
        ("actor_id", "愉快犯"),
        ("operation_type", "other"),
        ("from_phase", "other"),
        ("to_phase", "other"),
        ("completed_mini_goal_id", "other"),
        ("next_mini_goal_id", "other"),
        ("trigger_action_id", "other"),
        ("world_condition", "other"),
    ],
)
def test_builder_requires_exact_structured_rule_signature(field, value):
    event = _transition_event(**{field: value})
    if field in {
        "actor_id",
        "from_phase",
        "to_phase",
        "completed_mini_goal_id",
    }:
        event["event_id"] = ":".join(
            (
                "operation_transition",
                event["actor_id"],
                event["operation_id"],
                event["from_phase"],
                event["to_phase"],
                event["completed_mini_goal_id"],
            )
        )

    assert build_rc_memory_from_transition(event) is None


def test_builder_uses_event_id_only_for_consistency_and_source_reference():
    event = _transition_event(operation_id="op_inquiry_刑事_instance_2")

    memory = build_rc_memory_from_transition(event)

    assert memory["source_event_id"] == event["event_id"]
    assert memory["memory_id"] == f"memory:刑事:{event['event_id']}"


def test_builder_rejects_inconsistent_event_id():
    assert build_rc_memory_from_transition(
        _transition_event(event_id="operation_transition:forged")
    ) is None


def test_recorder_lazily_creates_actor_bucket_and_returns_detached_copy():
    world = {"unrelated": {"preserve": True}}
    memory = _expected_memory()

    returned = record_actor_memory(world, memory)

    assert world["actor_memories"] == {ACTOR_ID: [memory]}
    assert world["unrelated"] == {"preserve": True}
    returned["summary"] = "changed"
    memory["summary"] = "source changed"
    assert world["actor_memories"][ACTOR_ID][0] == _expected_memory()


@pytest.mark.parametrize(
    "world",
    [
        {"actor_memories": []},
        {"actor_memories": {ACTOR_ID: None}},
        {"actor_memories": {ACTOR_ID: {}}},
        {"actor_memories": {ACTOR_ID: "invalid"}},
    ],
)
def test_recorder_does_not_replace_invalid_existing_root_or_bucket(world):
    before = copy.deepcopy(world)

    assert record_actor_memory(world, _expected_memory()) is None
    assert world == before


def test_recorder_invalid_memory_does_not_create_actor_memories_root():
    world = {}

    assert record_actor_memory(world, {"invalid": True}) is None
    assert "actor_memories" not in world


def test_recorder_is_idempotent_per_source_event_and_actor():
    world = {}
    first = record_actor_memory(world, _expected_memory())
    before_duplicate = copy.deepcopy(world)

    duplicate = record_actor_memory(world, _expected_memory(summary="other text"))

    assert duplicate == first
    assert world == before_duplicate
    assert len(world["actor_memories"][ACTOR_ID]) == 1
    duplicate["summary"] = "changed"
    assert world["actor_memories"][ACTOR_ID][0] == first


def test_live_projector_builds_and_records_one_memory():
    world = {}

    projected = project_transition_to_rc_memory(world, _transition_event())

    assert projected == _expected_memory()
    assert world["actor_memories"][ACTOR_ID] == [_expected_memory()]


def test_catch_up_projects_missing_supported_events_in_history_order():
    first_event = _transition_event(operation_id="op_inquiry_刑事_1")
    second_event = _transition_event(operation_id="op_inquiry_刑事_2")
    existing_memory = build_rc_memory_from_transition(first_event)
    world = {
        "operation_transition_history": [
            {"malformed": True},
            first_event,
            _transition_event(actor_id="愉快犯", event_id="invalid"),
            second_event,
        ],
        "actor_memories": {ACTOR_ID: [existing_memory]},
    }
    history_before = copy.deepcopy(world["operation_transition_history"])

    added = project_pending_rc_memories(world)

    expected_second = build_rc_memory_from_transition(second_event)
    assert added == [expected_second]
    assert world["actor_memories"][ACTOR_ID] == [existing_memory, expected_second]
    assert world["operation_transition_history"] == history_before


def test_catch_up_is_idempotent_and_invalid_history_does_not_mutate_world():
    world = {"operation_transition_history": [_transition_event()]}

    first = project_pending_rc_memories(world)
    after_first = copy.deepcopy(world)
    second = project_pending_rc_memories(world)

    assert first == [_expected_memory()]
    assert second == []
    assert world == after_first

    invalid = {"operation_transition_history": {"not": "a list"}}
    before = copy.deepcopy(invalid)
    assert project_pending_rc_memories(invalid) == []
    assert invalid == before


def test_recent_reader_returns_last_five_full_records_oldest_to_newest():
    memories = []
    for index in range(7):
        event = _transition_event(operation_id=f"op_inquiry_刑事_{index}")
        memories.append(build_rc_memory_from_transition(event))
    world = {"actor_memories": {ACTOR_ID: memories}}

    recent = get_recent_actor_memories(world, ACTOR_ID)

    assert recent == memories[2:]
    assert all(set(item) == set(_expected_memory()) for item in recent)


def test_recent_reader_is_actor_scoped_read_only_and_tolerates_invalid_state():
    detective_memory = _expected_memory()
    trickster_memory = _expected_memory(
        actor_id="愉快犯",
        source_event_id="operation_transition:trickster",
    )
    world = {
        "actor_memories": {
            ACTOR_ID: [{"invalid": True}, detective_memory],
            "愉快犯": [trickster_memory],
        }
    }
    before = copy.deepcopy(world)

    recent = get_recent_actor_memories(world, ACTOR_ID)

    assert recent == [detective_memory]
    recent[0]["summary"] = "changed"
    assert world == before
    assert get_recent_actor_memories(world, "unknown") == []
    assert get_recent_actor_memories(None, ACTOR_ID) == []
    assert get_recent_actor_memories(world, ACTOR_ID, limit=0) == []


def test_memory_survives_yaml_roundtrip_and_world_defaults():
    world = {"operation_transition_history": [_transition_event()]}
    project_pending_rc_memories(world)

    loaded = yaml.safe_load(yaml.safe_dump(world, allow_unicode=True))
    merged = apply_world_defaults(
        loaded,
        {"world_defaults": {"investigation_progress": 0}},
    )

    assert merged["actor_memories"] == world["actor_memories"]
    assert json.loads(
        json.dumps(merged["actor_memories"], ensure_ascii=False)
    ) == world["actor_memories"]
