from __future__ import annotations

import copy

import pytest

import src.operation_runtime as operation_runtime
from src.actor_operations import get_active_operation, set_active_operation
from src.operation_instance import OperationInstance
from src.operation_store import OperationStore
from src.operation_runtime import (
    OperationRuntimeInput,
    OperationStartDirective,
    apply_action_outcome,
)


DETECTIVE_ID = "刑事"
TRICKSTER_ID = "愉快犯"


def _start_directive() -> OperationStartDirective:
    return OperationStartDirective(
        operation_type="inquiry",
        operation_label="聞き込みを始める",
        operation_phase="start",
        operation_mini_goal={
            "id": "mini_goal_choose_first_inquiry_target",
            "label": "聞き込み先を一件選ぶ",
            "status": "active",
        },
    )


def _input(
    action_id: str = "choose_first_inquiry_target",
    *,
    actor_id: str | None = DETECTIVE_ID,
    executed: bool = True,
    effects_committed: bool = True,
    source: str = "HUD",
    directive: OperationStartDirective | None = None,
) -> OperationRuntimeInput:
    return OperationRuntimeInput(
        action_id=action_id,
        actor_id=actor_id,
        executed=executed,
        effects_committed=effects_committed,
        source=source,
        operation_start_directive=directive,
    )


def _active_inquiry_operation(actor_id: str = DETECTIVE_ID) -> dict:
    return {
        "id": f"op_inquiry_{actor_id}",
        "type": "inquiry",
        "label": "聞き込みを始める",
        "status": "active",
        "phase": "start",
        "actor_id": actor_id,
        "target_id": None,
        "parent_microgoal_id": "micro_witness",
        "created_from": "HUD",
        "mini_goal": {
            "id": "mini_goal_choose_first_inquiry_target",
            "label": "聞き込み先を一件選ぶ",
            "status": "active",
        },
        "notes": [],
    }


def test_successful_input_evaluates_progression_once(monkeypatch):
    calls = []
    monkeypatch.setattr(
        operation_runtime,
        "advance_operation_after_action",
        lambda *args: calls.append(args) or {"advanced": False},
    )

    assert apply_action_outcome({}, {}, _input()) == []
    assert calls == [({}, DETECTIVE_ID, "choose_first_inquiry_target")]


def test_start_inquiry_progresses_before_starting_without_transition(monkeypatch):
    world = {
        "actor_micro_goals": {
            DETECTIVE_ID: {"id": "micro_witness"},
        },
        "actor_targets": {DETECTIVE_ID: "目撃者A"},
    }
    game_state = {"current_target": "目撃者B"}
    calls = []
    real_advance = operation_runtime.advance_operation_after_action
    real_start = operation_runtime.start_operation_once

    def advance_spy(*args):
        result = real_advance(*args)
        calls.append(("progress", result["reason"]))
        return result

    def start_spy(*args, **kwargs):
        calls.append(("start", kwargs["operation_type"]))
        return real_start(*args, **kwargs)

    monkeypatch.setattr(
        operation_runtime,
        "advance_operation_after_action",
        advance_spy,
    )
    monkeypatch.setattr(operation_runtime, "start_operation_once", start_spy)

    transitions = apply_action_outcome(
        world,
        game_state,
        _input("start_inquiry_operation", directive=_start_directive()),
    )

    assert transitions == []
    assert calls == [("progress", "no_active_operation"), ("start", "inquiry")]
    operation = get_active_operation(world, DETECTIVE_ID)
    assert operation["phase"] == "start"
    assert operation["target_id"] == "目撃者B"
    assert operation["parent_microgoal_id"] == "micro_witness"
    assert "operation_transition_history" not in world


def test_choose_first_target_returns_one_committed_transition_without_started_event():
    world = {
        "actor_discoveries": {DETECTIVE_ID: ["inquiry_target_chosen"]},
    }
    set_active_operation(world, DETECTIVE_ID, _active_inquiry_operation())

    transitions = apply_action_outcome(world, {}, _input())

    assert len(transitions) == 1
    assert transitions == world["operation_transition_history"]
    assert transitions[0]["kind"] == "operation_transition"
    assert all(event.get("kind") != "operation_started" for event in transitions)
    operation = get_active_operation(world, DETECTIVE_ID)
    assert operation["phase"] == "target_selected"


@pytest.mark.parametrize(
    ("executed", "effects_committed"),
    ((False, True), (True, False)),
)
def test_unsuccessful_input_is_noop(
    monkeypatch,
    executed,
    effects_committed,
):
    calls = []
    monkeypatch.setattr(
        operation_runtime,
        "advance_operation_after_action",
        lambda *args: calls.append(("progress", args)),
    )
    monkeypatch.setattr(
        operation_runtime,
        "start_operation_once",
        lambda *args, **kwargs: calls.append(("start", args, kwargs)),
    )

    result = apply_action_outcome(
        {},
        {},
        _input(executed=executed, effects_committed=effects_committed),
    )

    assert result == []
    assert calls == []


def test_switch_character_skips_progression_but_keeps_start_evaluation(monkeypatch):
    calls = []
    monkeypatch.setattr(
        operation_runtime,
        "advance_operation_after_action",
        lambda *args: calls.append(("progress", args)),
    )
    monkeypatch.setattr(
        operation_runtime,
        "start_operation_once",
        lambda *args, **kwargs: calls.append(("start", args, kwargs)) or {},
    )

    result = apply_action_outcome(
        {},
        {},
        _input("switch_character", directive=_start_directive()),
    )

    assert result == []
    assert [call[0] for call in calls] == ["start"]


def test_progression_exception_still_evaluates_start(monkeypatch, capsys):
    calls = []
    monkeypatch.setattr(
        operation_runtime,
        "advance_operation_after_action",
        lambda *_args: (_ for _ in ()).throw(RuntimeError("progress failed")),
    )
    monkeypatch.setattr(
        operation_runtime,
        "start_operation_once",
        lambda *args, **kwargs: calls.append((args, kwargs)) or {},
    )

    result = apply_action_outcome(
        {},
        {},
        _input("start_inquiry_operation", directive=_start_directive()),
    )

    assert result == []
    assert len(calls) == 1
    assert "[Operation] progression failed: progress failed" in capsys.readouterr().out


def test_record_exception_returns_no_transition_and_still_evaluates_start(
    monkeypatch,
    capsys,
):
    calls = []
    monkeypatch.setattr(
        operation_runtime,
        "advance_operation_after_action",
        lambda *_args: {"advanced": True},
    )
    monkeypatch.setattr(
        operation_runtime,
        "record_operation_transition",
        lambda *_args: (_ for _ in ()).throw(RuntimeError("record failed")),
    )
    monkeypatch.setattr(
        operation_runtime,
        "start_operation_once",
        lambda *args, **kwargs: calls.append((args, kwargs)) or {},
    )

    result = apply_action_outcome(
        {},
        {},
        _input(directive=_start_directive()),
    )

    assert result == []
    assert len(calls) == 1
    assert "[Operation] transition record failed: record failed" in capsys.readouterr().out


def test_start_exception_is_not_suppressed(monkeypatch):
    monkeypatch.setattr(
        operation_runtime,
        "advance_operation_after_action",
        lambda *_args: {"advanced": False},
    )
    monkeypatch.setattr(
        operation_runtime,
        "start_operation_once",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(RuntimeError("start failed")),
    )

    with pytest.raises(RuntimeError, match="start failed"):
        apply_action_outcome(
            {},
            {},
            _input("start_inquiry_operation", directive=_start_directive()),
        )


def test_actor_buckets_do_not_mix():
    world = {
        "actor_discoveries": {
            DETECTIVE_ID: ["inquiry_target_chosen"],
            TRICKSTER_ID: ["inquiry_target_chosen"],
        },
    }
    detective_operation = _active_inquiry_operation(DETECTIVE_ID)
    trickster_operation = _active_inquiry_operation(TRICKSTER_ID)
    set_active_operation(world, DETECTIVE_ID, detective_operation)
    set_active_operation(world, TRICKSTER_ID, trickster_operation)

    transitions = apply_action_outcome(world, {}, _input())

    assert [event["actor_id"] for event in transitions] == [DETECTIVE_ID]
    assert get_active_operation(world, DETECTIVE_ID)["phase"] == "target_selected"
    assert get_active_operation(world, TRICKSTER_ID) == trickster_operation


def test_same_state_reevaluation_does_not_duplicate_transition():
    world = {
        "actor_discoveries": {DETECTIVE_ID: ["inquiry_target_chosen"]},
    }
    set_active_operation(world, DETECTIVE_ID, _active_inquiry_operation())

    first = apply_action_outcome(world, {}, _input())
    second = apply_action_outcome(world, {}, _input())

    assert len(first) == 1
    assert second == []
    assert world["operation_transition_history"] == first


def test_runtime_has_no_memory_belief_or_ui_dependency():
    forbidden_names = {
        "project_transition_to_rc_memory",
        "project_memory_to_rc_belief",
        "RCContextBundle",
        "HUDCallbacks",
    }
    assert forbidden_names.isdisjoint(vars(operation_runtime))


def test_runtime_call_order_is_progress_record_start(monkeypatch):
    calls = []
    transition = {"kind": "operation_transition", "event_id": "event-1"}
    monkeypatch.setattr(
        operation_runtime,
        "advance_operation_after_action",
        lambda *_args: calls.append("progress") or {"advanced": True},
    )
    monkeypatch.setattr(
        operation_runtime,
        "record_operation_transition",
        lambda *_args: calls.append("record") or transition,
    )
    monkeypatch.setattr(
        operation_runtime,
        "start_operation_once",
        lambda *_args, **_kwargs: calls.append("start") or {},
    )

    result = apply_action_outcome(
        {},
        {},
        _input(directive=_start_directive()),
    )

    assert result == [transition]
    assert calls == ["progress", "record", "start"]


def test_start_metadata_falls_back_to_actor_target():
    world = {
        "actor_targets": {DETECTIVE_ID: "目撃者A"},
        "actor_micro_goals": {DETECTIVE_ID: {"id": "micro_witness"}},
    }

    apply_action_outcome(
        world,
        {"current_target": None},
        _input("start_inquiry_operation", directive=_start_directive()),
    )

    operation = copy.deepcopy(get_active_operation(world, DETECTIVE_ID))
    assert operation["target_id"] == "目撃者A"
    assert operation["parent_microgoal_id"] == "micro_witness"


def test_instance_save_failure_leaves_operation_and_effects_intact(monkeypatch, capsys):
    world = {"actor_discoveries": {DETECTIVE_ID: ["inquiry_target_chosen"]}}
    set_active_operation(world, DETECTIVE_ID, _active_inquiry_operation())
    before = copy.deepcopy(world)

    def fail_export(self):
        raise RuntimeError("instance export failed")

    monkeypatch.setattr(OperationInstance, "to_dict", fail_export)
    assert apply_action_outcome(world, {}, _input()) == []
    assert world == before
    assert "progression failed: instance export failed" in capsys.readouterr().out


def test_record_failure_keeps_real_instance_progression_committed(monkeypatch, capsys):
    world = {"actor_discoveries": {DETECTIVE_ID: ["inquiry_target_chosen"]}}
    set_active_operation(world, DETECTIVE_ID, _active_inquiry_operation())

    def fail_record(*args):
        raise RuntimeError("record failed")

    monkeypatch.setattr(operation_runtime, "record_operation_transition", fail_record)
    assert apply_action_outcome(world, {}, _input()) == []
    assert OperationStore(world).get_active_instance(DETECTIVE_ID).get("phase") == "target_selected"
    assert world["actor_discoveries"][DETECTIVE_ID] == ["inquiry_target_chosen"]
    assert "operation_transition_history" not in world
    assert "transition record failed: record failed" in capsys.readouterr().out


def test_new_instance_start_save_failure_propagates_without_initialization(monkeypatch):
    world = {}

    def fail_export(self):
        raise RuntimeError("start export failed")

    monkeypatch.setattr(OperationInstance, "to_dict", fail_export)
    with pytest.raises(RuntimeError, match="start export failed"):
        apply_action_outcome(world, {}, _input("start_inquiry_operation", directive=_start_directive()))
    assert world == {}
