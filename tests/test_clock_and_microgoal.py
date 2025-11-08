from __future__ import annotations

from pathlib import Path

from director.director import Director, MICRO_RULES, load_yaml
from src.action_registry import execute_action
from src.simulation_utils import add_minutes, ensure_clock, minutes_to_clock


ROOT = Path(__file__).resolve().parent.parent
PREMISE_DOC = load_yaml(str(ROOT / "data/director/premise.yml")) or {}
PREMISE = PREMISE_DOC.get("premise", {})
GOALS = load_yaml(str(ROOT / "data/director/cop_trickster_goals.yml")) or {}


def test_clock_ticks_and_micro_completion():
    director = Director(premise=PREMISE, goals_dict=GOALS)
    world = director.synthesize_world()
    ensure_clock(world)
    director.mode = "FREEZE"

    micro_text = "未読の通報を1件だけ確認"
    director._micro_cache["FREEZE"] = micro_text
    director._micro_baseline["FREEZE"] = director._capture_micro_baseline(world, "FREEZE")

    action_id, tmin = director.apply_auto_step(world)
    assert action_id == MICRO_RULES[micro_text]["action"]
    assert tmin == MICRO_RULES[micro_text]["time_min"]

    previous_minutes = world["clock_min"]
    execute_action(world, action_id)
    add_minutes(world, tmin)

    assert world["clock_min"] == previous_minutes + tmin
    assert world["clock"] == minutes_to_clock(world["clock_min"])
    assert director.is_micro_goal_done(world)
