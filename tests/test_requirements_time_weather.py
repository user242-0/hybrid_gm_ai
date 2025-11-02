from __future__ import annotations

import copy
import pathlib
import sys
from types import ModuleType, SimpleNamespace


ROOT = pathlib.Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def _ensure_stubbed_action_dependencies() -> None:
    if "src.action_definitions" in sys.modules:
        del sys.modules["src.action_definitions"]

    src_pkg = sys.modules.setdefault("src", ModuleType("src"))
    if not hasattr(src_pkg, "__path__"):
        src_pkg.__path__ = [str(ROOT / "src")]

    actions_mod = ModuleType("src.actions")
    for name in [
        "explore_location",
        "move_forward",
        "rest_with_event",
        "perform_attack",
        "swing_sword",
        "engage_combat",
        "avoid_combat",
        "accept_attack",
        "talk_to_statue",
        "talk_to_statue_with_cooldown",
        "generate_card_and_print",
        "npc_speak_and_log",
    ]:
        setattr(actions_mod, name, lambda *_, **__: None)
    actions_mod.__package__ = "src"
    sys.modules.setdefault("src.actions", actions_mod)

    control_mod = ModuleType("src.control_manager")
    control_mod.switch_character_action = lambda *_, **__: None
    control_mod.__package__ = "src"
    sys.modules.setdefault("src.control_manager", control_mod)

    emotion_mod = ModuleType("src.emotion_manager")
    emotion_mod.set_emotion_color_action = lambda *_, **__: None
    emotion_mod.__package__ = "src"
    sys.modules.setdefault("src.emotion_manager", emotion_mod)


_ensure_stubbed_action_dependencies()

from src.action_definitions import actions
from src.requirements_checker import RequirementsChecker


def _make_player(**overrides):
    base = {
        "is_tired": False,
        "hp": 10,
        "max_hp": 10,
        "stamina": 10,
        "max_stamina": 10,
        "inventory": [],
        "equipped_weapon": None,
        "name": "Hero",
    }
    base.update(overrides)
    return SimpleNamespace(**base)


def test_time_requirement_matches_time_of_day():
    player = _make_player()
    game_state = {"time_of_day": "night", "party": {}}

    checker = RequirementsChecker(game_state, player)

    assert checker.check_all({"time": "night"})
    assert not checker.check_all({"time": "morning"})


def test_weather_requirement_matches_world_kind():
    player = _make_player()
    game_state = {
        "time_of_day": "night",
        "party": {},
        "world": {"weather": {"kind": "clear"}},
    }

    checker = RequirementsChecker(game_state, player)

    assert checker.check_all({"weather_is": "clear"})
    assert not checker.check_all({"weather_is": "rain"})


def test_statue_actions_are_gated_by_time_and_weather():
    player = _make_player()
    base_state = {
        "time_of_day": "night",
        "current_location": "祭壇",
        "current_target": "古代の石像",
        "party": {},
        "world": {"weather": {"kind": "clear"}},
    }

    checker = RequirementsChecker(base_state, player)
    assert checker.check_all(actions["石像に話す"]["requirements"])
    assert checker.check_all(actions["石像に話す（クールダウン）"]["requirements"])

    daytime_state = copy.deepcopy(base_state)
    daytime_state["time_of_day"] = "morning"
    daytime_checker = RequirementsChecker(daytime_state, player)
    assert not daytime_checker.check_all(actions["石像に話す"]["requirements"])

    storm_state = copy.deepcopy(base_state)
    storm_state["world"]["weather"]["kind"] = "storm"
    storm_checker = RequirementsChecker(storm_state, player)
    assert not storm_checker.check_all(actions["石像に話す（クールダウン）"]["requirements"])
