import random
from pathlib import Path

from director.director import Director, load_yaml


ROOT = Path(__file__).resolve().parent.parent
PREMISE_DOC = load_yaml(str(ROOT / "data/director/premise.yml")) or {}
PREMISE = PREMISE_DOC.get("premise", {})
GOALS = load_yaml(str(ROOT / "data/director/cop_trickster_goals.yml")) or {}


def make_director(seed: int = 123) -> Director:
    rng = random.Random(seed)
    return Director(premise=PREMISE, goals_dict=GOALS, rng=rng)


def test_next_micro_goal_non_none_in_freeze_mode():
    director = make_director()
    world = director.synthesize_world()
    director.mode = "FREEZE"
    micro = director.next_micro_goal(world)
    assert micro is not None
    assert isinstance(micro, str)


def test_sobriety_unlocks_switch_to_pursue():
    director = make_director()
    world = director.synthesize_world()
    world["sobriety_days"] = 3
    director.tick(world)
    assert "SwitchToPURSUE" in world["unlocks"]


def test_escalation_scene_only_once_when_harm_exceeds_threshold():
    director = make_director()
    world = director.synthesize_world()
    harm = world["harm"]
    harm["value"] = harm["threshold_warn"]

    scenes = director.tick(world)
    escalation_scenes = [s for s in scenes if s.get("intent") == "Escalation"]
    assert escalation_scenes, "Escalation scene should trigger when harm crosses threshold"

    scenes_again = director.tick(world)
    assert not any(s.get("intent") == "Escalation" for s in scenes_again), "Escalation should not trigger twice"


def test_synthesize_world_is_deterministic_with_same_seed():
    director_a = make_director(seed=999)
    director_b = make_director(seed=999)
    world_a = director_a.synthesize_world()
    world_b = director_b.synthesize_world()
    assert world_a == world_b


def test_yaml_keys_present():
    assert PREMISE, "premise.yml should define a premise block"
    required_premise_keys = {"title", "seed", "roles", "modes_enabled", "tone"}
    assert required_premise_keys.issubset(PREMISE.keys())
    assert {"protagonist", "antagonist"}.issubset(PREMISE["roles"].keys())

    beats = PREMISE_DOC.get("beats", {})
    assert "skeleton" in beats
    assert beats["skeleton"], "beats.skeleton should list story beats"

    assert "modes" in GOALS
    modes = GOALS["modes"]
    for mode in PREMISE.get("modes_enabled", []):
        assert mode in modes, f"mode {mode} missing in goals document"
        entry = modes[mode]
        assert "goals" in entry
        assert "micro" in entry
        assert isinstance(entry["goals"], list)
        assert isinstance(entry["micro"], list)