from __future__ import annotations

import copy
from types import SimpleNamespace

import pytest

from director.director import Director, load_yaml
from director.registry import extract_goals_from_pack, load_pack
from src.action_definitions import get_action_specs
from src.actor_operations import get_active_operation
from src.actor_view_state import (
    inject_actor_discovery,
    set_actor_location,
    sync_actor_view_to_legacy,
)
from src.game_command import (
    ActionExecutionResult,
    ActionOutcome,
    GameCommand,
)
from src.game_command_service import GameCommandService
from src.operation_runtime import OperationRuntimeInput
from src.rc_ai import generate_rc_advisory
from src.ui.action_pipeline import ActionPipeline
from src.world_defaults import apply_world_defaults


def _outcome(*, executed: bool = True, actor_id: str = "刑事") -> ActionOutcome:
    return ActionOutcome(
        action_id="choose_first_inquiry_target",
        actor_id=actor_id,
        executed=executed,
        effects_committed=executed,
        source="HUD",
        reason=None if executed else "requirements_failed",
    )


def _execution_result(*, executed: bool = True) -> ActionExecutionResult:
    return ActionExecutionResult(
        outcome=_outcome(executed=executed),
        operation_input=(
            OperationRuntimeInput(
                action_id="choose_first_inquiry_target",
                actor_id="刑事",
                executed=True,
                effects_committed=True,
                source="HUD",
            )
            if executed
            else None
        ),
        post_action_context=object() if executed else None,
    )


class _Pipeline:
    def __init__(self, result: ActionExecutionResult, calls: list):
        self.result = result
        self.calls = calls

    def execute_action(self, *args, **kwargs):
        self.calls.append(("action", args, kwargs))
        return self.result

    def finalize_post_action(self, result):
        assert result is self.result
        self.calls.append(("finalize",))


def _service(
    calls: list,
    *,
    execution_result: ActionExecutionResult | None = None,
    operation_runtime=None,
    memory_projector=None,
    belief_projector=None,
    context_builder=None,
):
    cop = SimpleNamespace(name="刑事")
    game_state = {
        "director_world": {},
        "party": {"刑事": cop},
        "active_char": cop,
    }
    kwargs = {}
    if operation_runtime is not None:
        kwargs["operation_runtime"] = operation_runtime
    if memory_projector is not None:
        kwargs["memory_projector"] = memory_projector
    if belief_projector is not None:
        kwargs["belief_projector"] = belief_projector
    if context_builder is not None:
        kwargs["context_builder"] = context_builder
    service = GameCommandService(
        game_state=game_state,
        pipeline=_Pipeline(execution_result or _execution_result(), calls),
        director=object(),
        **kwargs,
    )
    return service, game_state


def _command() -> GameCommand:
    return GameCommand(
        action_id="choose_first_inquiry_target",
        actor_id="刑事",
        source="HUD",
    )


def test_success_calls_each_stage_once_in_order():
    calls = []
    transition = {"id": "transition"}
    memory = {"id": "memory"}
    belief = {"id": "belief"}

    def operation(*_args):
        calls.append(("operation",))
        return [transition]

    def project_memory(_world, received):
        assert received == transition
        calls.append(("memory",))
        return memory

    def project_belief(_world, received):
        assert received == memory
        calls.append(("belief",))
        return belief

    def build_bundle(actor_id, *_args):
        assert actor_id == "刑事"
        calls.append(("bundle",))
        return {"actor_id": actor_id}

    service, _state = _service(
        calls,
        operation_runtime=operation,
        memory_projector=project_memory,
        belief_projector=project_belief,
        context_builder=build_bundle,
    )

    result = service.execute(_command())

    assert [call[0] for call in calls] == [
        "action",
        "operation",
        "memory",
        "belief",
        "finalize",
        "bundle",
    ]
    assert result.operation_transitions == (transition,)
    assert result.memory_records == (memory,)
    assert result.belief_updates == (belief,)
    assert result.context_bundle == {"actor_id": "刑事"}
    assert result.stage_failures == ()


def test_rejected_action_stops_before_follow_up_stages():
    calls = []
    service, _state = _service(
        calls,
        execution_result=_execution_result(executed=False),
        operation_runtime=lambda *_args: pytest.fail("operation called"),
        memory_projector=lambda *_args: pytest.fail("memory called"),
        belief_projector=lambda *_args: pytest.fail("belief called"),
        context_builder=lambda *_args: pytest.fail("bundle called"),
    )

    result = service.execute(_command())

    assert [call[0] for call in calls] == ["action"]
    assert result.action_outcome.executed is False
    assert result.action_outcome.reason == "requirements_failed"


def test_no_committed_transition_skips_memory_and_belief():
    calls = []

    def operation(*_args):
        calls.append(("operation",))
        return []

    service, _state = _service(
        calls,
        operation_runtime=operation,
        memory_projector=lambda *_args: pytest.fail("memory called"),
        belief_projector=lambda *_args: pytest.fail("belief called"),
        context_builder=lambda actor_id, *_args: {"actor_id": actor_id},
    )

    result = service.execute(_command())

    assert [call[0] for call in calls] == [
        "action",
        "operation",
        "finalize",
    ]
    assert result.operation_transitions == ()


def test_memory_failure_skips_its_belief_and_continues():
    calls = []
    transitions = [{"id": "bad"}, {"id": "good"}]

    def project_memory(_world, transition):
        calls.append(("memory", transition["id"]))
        if transition["id"] == "bad":
            raise RuntimeError("memory failed")
        return {"id": "memory-good"}

    def project_belief(_world, memory):
        calls.append(("belief", memory["id"]))
        return {"id": "belief-good"}

    service, _state = _service(
        calls,
        operation_runtime=lambda *_args: transitions,
        memory_projector=project_memory,
        belief_projector=project_belief,
        context_builder=lambda actor_id, *_args: {"actor_id": actor_id},
    )

    result = service.execute(_command())

    assert ("memory", "bad") in calls
    assert ("memory", "good") in calls
    assert ("belief", "memory-good") in calls
    assert result.memory_records == ({"id": "memory-good"},)
    assert result.belief_updates == ({"id": "belief-good"},)
    assert result.stage_failures[0].stage == "memory_projection"
    assert calls[-1][0] == "finalize"


def test_belief_failure_keeps_memory_and_continues_to_bundle():
    calls = []

    def fail_belief(*_args):
        calls.append(("belief",))
        raise RuntimeError("belief failed")

    def build_bundle(actor_id, *_args):
        calls.append(("bundle",))
        return {"actor_id": actor_id}

    service, _state = _service(
        calls,
        operation_runtime=lambda *_args: [{"id": "transition"}],
        memory_projector=lambda *_args: {"id": "memory"},
        belief_projector=fail_belief,
        context_builder=build_bundle,
    )

    result = service.execute(_command())

    assert result.memory_records == ({"id": "memory"},)
    assert result.belief_updates == ()
    assert result.stage_failures[0].stage == "belief_projection"
    assert result.context_bundle == {"actor_id": "刑事"}
    assert [call[0] for call in calls][-3:] == ["belief", "finalize", "bundle"]


def test_bundle_failure_is_reported_after_finalizer():
    calls = []

    def fail_bundle(*_args):
        calls.append(("bundle",))
        raise RuntimeError("bundle failed")

    service, _state = _service(
        calls,
        operation_runtime=lambda *_args: [],
        context_builder=fail_bundle,
    )

    result = service.execute(_command())

    assert result.context_bundle is None
    assert result.stage_failures == (
        result.stage_failures[0],
    )
    assert result.stage_failures[0].stage == "context_bundle"
    assert [call[0] for call in calls][-2:] == ["finalize", "bundle"]


def test_result_snapshots_do_not_reference_authoritative_records():
    calls = []
    service, state = _service(calls)
    world = state["director_world"]
    world["transition"] = {"nested": {"value": 1}}
    world["memory"] = {"nested": {"value": 2}}
    world["belief"] = {"nested": {"value": 3}}
    world["bundle_source"] = {"nested": {"value": 4}}
    service.operation_runtime = lambda *_args: [world["transition"]]
    service.memory_projector = lambda *_args: world["memory"]
    service.belief_projector = lambda *_args: world["belief"]
    service.context_builder = lambda *_args: world["bundle_source"]

    result = service.execute(_command())
    result.operation_transitions[0]["nested"]["value"] = 10
    result.memory_records[0]["nested"]["value"] = 20
    result.belief_updates[0]["nested"]["value"] = 30
    result.context_bundle["nested"]["value"] = 40

    assert world["transition"]["nested"]["value"] == 1
    assert world["memory"]["nested"]["value"] == 2
    assert world["belief"]["nested"]["value"] == 3
    assert world["bundle_source"]["nested"]["value"] == 4


def test_bundle_targets_active_actor_after_switch():
    calls = []
    cop = SimpleNamespace(name="刑事")
    trickster = SimpleNamespace(name="愉快犯")
    state = {
        "director_world": {},
        "party": {"刑事": cop, "愉快犯": trickster},
        "active_char": cop,
    }
    execution = ActionExecutionResult(
        outcome=ActionOutcome(
            action_id="switch_character",
            actor_id="刑事",
            executed=True,
            effects_committed=True,
            source="GUI",
            value=trickster,
        ),
        operation_input=None,
        post_action_context=object(),
    )
    pipeline = _Pipeline(execution, calls)

    def finalize(result):
        assert result is execution
        calls.append(("finalize",))
        state["active_char"] = trickster

    pipeline.finalize_post_action = finalize

    def bundle(actor_id, *_args):
        calls.append(("bundle", actor_id))
        return {"actor_id": actor_id}

    service = GameCommandService(
        game_state=state,
        pipeline=pipeline,
        operation_runtime=lambda *_args: pytest.fail("operation called"),
        context_builder=bundle,
    )

    result = service.execute(
        GameCommand(action_id="switch_character", actor_id="刑事", source="GUI")
    )

    assert result.context_bundle == {"actor_id": "愉快犯"}
    assert calls[-1] == ("bundle", "愉快犯")


def test_actor_id_none_resolves_current_active_actor():
    calls = []
    service, state = _service(
        calls,
        operation_runtime=lambda *_args: [],
        context_builder=lambda actor_id, *_args: {"actor_id": actor_id},
    )

    service.execute(GameCommand(action_id="check_tip", actor_id=None))

    action_call = calls[0]
    assert action_call[2]["actor_obj"] is state["active_char"]
    assert action_call[2]["actor_id"] is None


def test_unknown_explicit_actor_is_rejected_without_active_actor_fallback():
    calls = []
    service, _state = _service(calls)

    result = service.execute(
        GameCommand(action_id="check_tip", actor_id="unknown", source="GUI")
    )

    assert calls == []
    assert result.action_outcome.executed is False
    assert result.action_outcome.reason == "actor_not_found"


def test_game_command_service_has_no_ui_dependency():
    import src.game_command_service as module

    names = set(module.__dict__)
    assert "HUDCallbacks" not in names
    assert "tkinter" not in names


def _real_actor(name: str, *, location: str, is_active: bool):
    return SimpleNamespace(
        name=name,
        location=location,
        is_npc=not is_active,
        is_rc=True,
        is_active=is_active,
        faction="player",
        is_tired=False,
        hp=100,
        max_hp=100,
        stamina=100,
        max_stamina=100,
        inventory=[],
        equipped_weapon=None,
        emotion_color=(127, 127, 255),
    )


def _real_service(monkeypatch):
    pack = load_pack("cop_trickster")
    premise = load_yaml("data/director/premise.yml").get("premise", {})
    director = Director(
        premise=premise,
        goals_dict=extract_goals_from_pack(pack),
    )
    world = apply_world_defaults(director.synthesize_world(), pack)
    cop = _real_actor(
        "刑事",
        location=world["actor_locations"]["刑事"],
        is_active=True,
    )
    trickster = _real_actor(
        "愉快犯",
        location=world["actor_locations"]["愉快犯"],
        is_active=False,
    )
    game_state = {
        "director_world": world,
        "world": world,
        "party": {"刑事": cop, "愉快犯": trickster},
        "active_char": cop,
        "current_target": "愉快犯",
        "actor_targets": {"刑事": "愉快犯", "愉快犯": "刑事"},
        "current_location": cop.location,
        "emotions_by_actor": {
            "刑事": {"R": 127, "G": 127, "B": 255},
            "愉快犯": {"R": 127, "G": 127, "B": 255},
        },
        "hud_cache_rev": 0,
    }
    world["actor_targets"] = dict(game_state["actor_targets"])
    get_action_specs(pack)
    pipeline = ActionPipeline(game_state=game_state, director=director)
    monkeypatch.setattr(pipeline, "_record_action_log", lambda **_kwargs: None)
    monkeypatch.setattr(pipeline, "_emit_scene_graph", lambda *_args, **_kwargs: None)
    return (
        pack,
        director,
        world,
        game_state,
        pipeline,
        GameCommandService(game_state=game_state, pipeline=pipeline, director=director),
    )


def test_action_only_boundary_does_not_call_operation_runtime(monkeypatch):
    _pack, director, world, game_state, pipeline, _service = _real_service(monkeypatch)
    director.set_actor_mode(world, "刑事", "PURSUE")
    inject_actor_discovery(world, "刑事", "camera_skew_noticed")
    monkeypatch.setitem(
        pipeline.execute_action.__globals__,
        "apply_action_outcome",
        lambda *_args: pytest.fail("operation runtime called"),
    )

    execution = pipeline.execute_action(
        "start_inquiry_operation",
        actor_obj=game_state["party"]["刑事"],
        actor_id="刑事",
        source="HUD",
    )

    assert execution.outcome.executed is True
    assert execution.outcome.effects_committed is True
    assert execution.operation_input.operation_start_directive.operation_type == "inquiry"
    assert get_active_operation(world, "刑事") is None


def test_real_golden_path_runs_through_service_and_returns_fresh_bundle(monkeypatch):
    _pack, director, world, _state, _pipeline, service = _real_service(monkeypatch)
    director.set_actor_mode(world, "刑事", "WITNESS")
    inject_actor_discovery(world, "刑事", "camera_skew_noticed")

    started = service.execute(
        GameCommand(
            action_id="start_inquiry_operation",
            actor_id="刑事",
            source="HUD",
        )
    )
    advanced = service.execute(
        GameCommand(
            action_id="choose_first_inquiry_target",
            actor_id="刑事",
            source="HUD",
        )
    )

    assert started.action_outcome.executed is True
    assert started.operation_transitions == ()
    operation = get_active_operation(world, "刑事")
    assert operation["phase"] == "target_selected"
    assert len(advanced.operation_transitions) == 1
    assert len(advanced.memory_records) == 1
    assert len(advanced.belief_updates) == 1
    assert advanced.context_bundle["actor_id"] == "刑事"
    assert advanced.context_bundle["active_operation"]["phase"] == "target_selected"
    assert len(advanced.context_bundle["recent_memory"]) == 1
    assert "first_inquiry_target_selected" in advanced.context_bundle["beliefs"]
    assert generate_rc_advisory(advanced.context_bundle)["selected_intent"] == "no_safe_action"
    assert "愉快犯" not in world.get("actor_memories", {})
    assert "愉快犯" not in world.get("actor_beliefs", {})


def test_real_switch_returns_legacy_value_and_bundles_new_active_actor(monkeypatch):
    _pack, _director, _world, state, _pipeline, service = _real_service(monkeypatch)
    previous_actor = state["active_char"]

    result = service.execute(
        GameCommand(
            action_id="switch_character",
            actor_id="刑事",
            args=("愉快犯",),
            source="GUI",
        )
    )

    assert result.action_outcome.value is previous_actor
    assert state["active_char"].name == "愉快犯"
    assert result.context_bundle["actor_id"] == "愉快犯"


def test_real_move_keeps_special_lifecycle_and_skips_operation(monkeypatch):
    _pack, _director, world, state, pipeline, _service = _real_service(monkeypatch)
    set_actor_location(world, "刑事", "警察署_控室")
    state["party"]["刑事"].location = "警察署_控室"
    sync_actor_view_to_legacy(world, state, "刑事")
    clock_before = copy.deepcopy(world.get("clock"))
    microgoals_before = copy.deepcopy(world.get("actor_micro_goals"))
    affordances_before = copy.deepcopy(world.get("affordances"))
    service = GameCommandService(
        game_state=state,
        pipeline=pipeline,
        director=_director,
        operation_runtime=lambda *_args: pytest.fail("operation called"),
        memory_projector=lambda *_args: pytest.fail("memory called"),
        belief_projector=lambda *_args: pytest.fail("belief called"),
    )

    result = service.execute(
        GameCommand(
            action_id="move_to_location",
            actor_id="刑事",
            args=("酒場",),
            source="GUI",
        )
    )

    assert result.action_outcome.executed is True
    assert result.operation_transitions == ()
    assert result.memory_records == ()
    assert result.belief_updates == ()
    assert world["actor_locations"]["刑事"] == "酒場"
    assert world.get("clock") == clock_before
    assert world.get("actor_micro_goals") == microgoals_before
    assert world.get("affordances") == affordances_before
