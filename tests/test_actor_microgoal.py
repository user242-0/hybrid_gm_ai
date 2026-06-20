from __future__ import annotations

import random

from director.director import Director, load_yaml
from director.registry import extract_goals_from_pack, load_pack
from src.world_defaults import apply_world_defaults


def make_director(seed: int = 49) -> Director:
    premise = load_yaml("data/director/premise.yml").get("premise", {})
    goals = extract_goals_from_pack(load_pack("cop_trickster"))
    return Director(premise=premise, goals_dict=goals, rng=random.Random(seed))


def micro_texts(director: Director, mode: str) -> set[str]:
    return {
        entry["text"]
        for entry in director.goals_dict["modes"][mode]["micro"]
    }


def test_actor_micro_goals_are_stored_independently_by_actor_id():
    director = make_director()
    world = apply_world_defaults(
        director.synthesize_world(),
        load_pack("cop_trickster"),
    )

    cop_micro = director.get_micro_goal_for_actor(world, "刑事")
    trickster_micro = director.get_micro_goal_for_actor(world, "愉快犯")

    assert cop_micro in micro_texts(director, "FREEZE")
    assert trickster_micro in micro_texts(director, "FLEE")
    assert world["actor_micro_goals"]["刑事"]["text"] == cop_micro
    assert world["actor_micro_goals"]["愉快犯"]["text"] == trickster_micro

    director.clear_micro_goal_for_actor(world, "愉快犯")

    assert world["actor_micro_goals"]["刑事"]["text"] == cop_micro
    assert world["actor_micro_goals"]["愉快犯"]["text"] is None


def test_actor_micro_goal_uses_actor_mode_and_recomputes_when_mode_changes():
    director = make_director()
    world = apply_world_defaults(
        director.synthesize_world(),
        load_pack("cop_trickster"),
    )

    freeze_micro = director.get_micro_goal_for_actor(world, "刑事")
    assert freeze_micro in micro_texts(director, "FREEZE")

    assert director.set_actor_mode(world, "刑事", "PURSUE")
    pursue_micro = director.get_micro_goal_for_actor(world, "刑事")

    assert pursue_micro in micro_texts(director, "PURSUE")
    assert world["actor_micro_goals"]["刑事"]["mode"] == "PURSUE"


def test_actor_micro_goal_falls_back_to_director_mode_without_actor_mode():
    director = make_director()
    director.mode = "PURSUE"
    world = director.synthesize_world()

    micro = director.get_micro_goal_for_actor(world, "刑事")

    assert micro in micro_texts(director, "PURSUE")
    assert world["actor_micro_goals"]["刑事"]["mode"] == "PURSUE"


def test_missing_actor_id_keeps_legacy_global_micro_goal_path():
    director = make_director()
    director.mode = "FREEZE"
    world = director.synthesize_world()

    actor_api_micro = director.get_micro_goal_for_actor(world, None)
    legacy_micro = director.get_micro_goal(world)

    assert actor_api_micro == legacy_micro
    assert "actor_micro_goals" not in world
