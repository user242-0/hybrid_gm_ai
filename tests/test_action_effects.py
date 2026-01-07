from director.registry import load_pack

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
