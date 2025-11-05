import random
from pathlib import Path

import pytest

from director.director import Director, load_yaml


ROOT = Path(__file__).resolve().parent.parent
PREMISE_DOC = load_yaml(str(ROOT / "data/director/premise.yml")) or {}
PREMISE = PREMISE_DOC.get("premise", {})
GOALS = load_yaml(str(ROOT / "data/director/cop_trickster_goals.yml")) or {}


@pytest.fixture()
def director() -> Director:
    rng = random.Random(999)
    return Director(premise=PREMISE, goals_dict=GOALS, rng=rng)


def test_reroll_avoids_immediate_duplicates(director: Director):
    world = director.synthesize_world()
    for mode, bucket in GOALS.get("modes", {}).items():
        micro_items = bucket.get("micro", [])
        unique_items = {item for item in micro_items}
        if len(unique_items) <= 1:
            continue
        director.mode = mode
        last_goal = None
        for _ in range(10):
            goal = director.get_micro_goal(world, reroll=True)
            if last_goal is not None:
                assert goal != last_goal, f"mode={mode} should not repeat consecutively"
            last_goal = goal


def test_history_rolls_back_in_after_recent_window(director: Director):
    director.mode = "FREEZE"
    world = director.synthesize_world()
    seen = []
    for _ in range(6):
        seen.append(director.get_micro_goal(world, reroll=True))

    assert len(seen) >= 4
    # The first three should all be unique (enough variety in sample data).
    assert len(set(seen[:3])) == len(seen[:3])
    # A later selection can repeat one from the first three once the recent window is full.
    assert any(goal == seen[0] for goal in seen[3:])
