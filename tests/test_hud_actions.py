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