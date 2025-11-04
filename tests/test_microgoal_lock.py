import random
from pathlib import Path

from director.director import Director, load_yaml


ROOT = Path(__file__).resolve().parent.parent
PREMISE_DOC = load_yaml(str(ROOT / "data/director/premise.yml")) or {}
PREMISE = PREMISE_DOC.get("premise", {})
GOALS = load_yaml(str(ROOT / "data/director/cop_trickster_goals.yml")) or {}


def make_director(seed: int = 321) -> Director:
    rng = random.Random(seed)
    return Director(premise=PREMISE, goals_dict=GOALS, rng=rng)


def test_micro_goal_locks_until_reroll():
    director = make_director()
    world = director.synthesize_world()
    director.mode = "FREEZE"

    first = director.get_micro_goal(world, reroll=False)
    second = director.get_micro_goal(world, reroll=False)
    assert first == second

    rerolled = director.get_micro_goal(world, reroll=True)
    assert isinstance(rerolled, str)


def test_clear_micro_goal_resets_progress_baseline():
    director = make_director()
    world = director.synthesize_world()
    director.mode = "FREEZE"

    director.get_micro_goal(world, reroll=False)
    director.apply_auto_step(world)
    assert director.is_micro_goal_done(world)

    director.clear_micro_goal()
    director.get_micro_goal(world, reroll=False)
    assert not director.is_micro_goal_done(world)
