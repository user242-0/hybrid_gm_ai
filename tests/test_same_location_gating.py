from types import SimpleNamespace

from src.choice_definitions import get_available_choices
from src.requirements_checker import RequirementsChecker
from src.ui.action_pipeline import ActionPipeline


DIRECT_ACTIONS = {
    "talk",
    "attack",
    "swing_sword",
    "engage_combat",
    "avoid_combat",
    "accept_attack",
}


def _actor(name, *, location=None, is_npc=False, equipped_weapon=None):
    return SimpleNamespace(
        name=name,
        location=location,
        is_npc=is_npc,
        is_rc=True,
        is_active=False,
        faction="player",
        is_tired=False,
        hp=100,
        max_hp=100,
        stamina=100,
        max_stamina=100,
        inventory=[],
        equipped_weapon=equipped_weapon,
        emotion_color=(127, 127, 255),
        attack_power=10,
    )


def _state(actor_location, target_location):
    cop = _actor(
        "刑事",
        location=actor_location,
        equipped_weapon={"name": "鉄の剣", "weapon_type": "sword"},
    )
    trickster = _actor("愉快犯", location=target_location)
    world = {
        "actor_locations": {
            "刑事": actor_location,
            "愉快犯": target_location,
        },
        "clock": "Day1 00:00",
        "emotion": {"R": 127, "G": 127, "B": 127},
    }
    game_state = {
        "current_location": actor_location,
        "current_target": "愉快犯",
        "has_enemy": True,
        "party": {"刑事": cop, "愉快犯": trickster},
        "director_world": world,
        "world": world,
    }
    return cop, trickster, game_state


def _choice_ids(actor, game_state):
    return {choice.action_key for choice in get_available_choices(actor, game_state)}


def test_same_location_requirement_fails_for_remote_actor_target():
    actor, _target, game_state = _state("警察署_控室", "事件現場_路地裏")

    checker = RequirementsChecker(game_state, actor)

    assert checker.check_all({"same_location": True}) is False


def test_same_location_requirement_passes_for_colocated_actor_target():
    actor, _target, game_state = _state("事件現場_路地裏", "事件現場_路地裏")

    checker = RequirementsChecker(game_state, actor)

    assert checker.check_all({"same_location": True}) is True


def test_direct_gui_actions_are_hidden_for_remote_current_target():
    actor, _target, game_state = _state("警察署_控室", "事件現場_路地裏")

    action_ids = _choice_ids(actor, game_state)

    assert DIRECT_ACTIONS.isdisjoint(action_ids)


def test_direct_gui_actions_are_available_for_colocated_current_target():
    actor, _target, game_state = _state("事件現場_路地裏", "事件現場_路地裏")

    action_ids = _choice_ids(actor, game_state)

    assert DIRECT_ACTIONS <= action_ids


def test_action_pipeline_blocks_direct_action_for_remote_explicit_target():
    actor, _target, game_state = _state("警察署_控室", "事件現場_路地裏")
    pipeline = ActionPipeline(game_state=game_state)

    result = pipeline.request_action(
        "attack",
        actor_obj=actor,
        args=["愉快犯"],
        source="GUI",
    )

    assert result is None
