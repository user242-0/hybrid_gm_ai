from director.director import Director, load_yaml
from director.registry import load_pack, extract_goals_from_pack


def test_actions_list_populates():
    premise = load_yaml("data/director/premise.yml").get("premise", {})
    goals = extract_goals_from_pack(load_pack("cop_trickster"))
    director = Director(premise=premise, goals_dict=goals)
    world = director.synthesize_world()
    director.mode = "PURSUE"

    actions = director.list_actions_for_mode("PURSUE")
    assert isinstance(actions, list)
    assert actions

    recommended = director.recommended_action(world)[0]
    assert recommended is None or isinstance(recommended, str)

    progress = director.progress_text(world)
    assert isinstance(progress, str)
    assert progress.startswith("Micro:")


def test_actor_specific_hud_actions_do_not_mix_cop_and_trickster_actions():
    premise = load_yaml("data/director/premise.yml").get("premise", {})
    goals = extract_goals_from_pack(load_pack("cop_trickster"))
    director = Director(premise=premise, goals_dict=goals)

    cop_actions = {
        record["action"]
        for record in director.list_actions_for_actor("刑事", "PURSUE")
    }
    trickster_actions = {
        record["action"]
        for record in director.list_actions_for_actor("愉快犯", "PURSUE")
    }

    assert {"collect_fiber", "fix_cam_clock", "call_partner"} <= cop_actions
    assert {"move_low_profile", "mark_avoid_shop"} <= trickster_actions
    assert cop_actions.isdisjoint(trickster_actions)


def test_unknown_actor_falls_back_to_current_mode_actions():
    premise = load_yaml("data/director/premise.yml").get("premise", {})
    goals = extract_goals_from_pack(load_pack("cop_trickster"))
    director = Director(premise=premise, goals_dict=goals)

    expected = director.list_actions_for_mode("PURSUE")

    assert director.list_actions_for_actor("Unknown", "PURSUE") == expected
