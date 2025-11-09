from director.director import Director, load_yaml


def test_yaml_micro_rules_load_and_done():
    goals = load_yaml("data/director/cop_trickster_goals.yml")
    premise_doc = load_yaml("data/director/premise.yml") or {}
    premise = premise_doc.get("premise", {})
    director = Director(premise=premise, goals_dict=goals)
    world = director.synthesize_world()
    world["evidence_score"] = 0

    director.mode = "PURSUE"
    micro = director.get_micro_goal(world, reroll=True)
    assert isinstance(micro, str)
    assert micro

    action_id, time_min = director.apply_auto_step(world)
    assert isinstance(time_min, int)
    if action_id == "collect_fiber":
        world["evidence_score"] = 10
    assert isinstance(director.is_micro_goal_done(world), bool)
