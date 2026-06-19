from director.registry import load_pack

from src.action_definitions import get_action_specs
from src.action_registry import execute_action
from src.world_defaults import apply_world_defaults


def test_pack_world_defaults_merge():
    pack = load_pack("cop_trickster")
    world = {"sobriety_days": 99, "harm": {"value": 5, "threshold_warn": 99}}
    merged = apply_world_defaults(world, pack)
    defaults = pack["world_defaults"]
    assert merged["sobriety_days"] == defaults["sobriety_days"]
    assert merged["harm"]["threshold_warn"] == defaults["harm"]["threshold_warn"]


def test_execute_action_applies_effects():
    world = {"sobriety_days": 0, "evidence_score": 0, "entropy": {"value": 0}}
    execute_action(world, "limit_drink")
    assert world["sobriety_days"] == 1
    assert world["entropy"]["value"] == 0
    execute_action(world, "collect_fiber")
    assert world["evidence_score"] == 10


def test_trickster_basic_actions_have_specs_and_apply_safe_effects():
    pack = load_pack("cop_trickster")
    specs = get_action_specs(pack)
    action_ids = {
        "hide_evidence",
        "plant_false_trace",
        "avoid_witness",
        "change_hideout",
        "observe_next_target",
    }

    assert action_ids <= specs.keys()

    world = apply_world_defaults({}, pack)
    execute_action(world, "hide_evidence")
    execute_action(world, "plant_false_trace")
    execute_action(world, "avoid_witness")
    execute_action(world, "change_hideout")
    execute_action(world, "observe_next_target")

    assert world["suspicion"]["value"] == 2
    assert world["false_traces"] == 1
    assert world["witnesses_avoided"] == 1
    assert world["hideout_changes"] == 1
    assert world["target_observations"] == 1
