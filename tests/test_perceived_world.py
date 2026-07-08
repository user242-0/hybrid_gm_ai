import copy

from src.perceived_world import (
    build_perceived_world,
    format_perceived_world_summary,
)


def _location_graph():
    return {
        "警察署_控室": {
            "exits": [
                {"to": "事件現場_路地裏", "allowed_actors": ["刑事"], "time_min": 15},
                {"to": "酒場", "allowed_actors": ["刑事"], "time_min": 10},
                {"to": "駅裏", "allowed_actors": ["愉快犯"], "time_min": 20},
            ],
        },
        "酒場": {
            "exits": [
                {"to": "警察署_控室", "allowed_actors": ["刑事"], "time_min": 10},
                {"to": "事件現場_路地裏", "allowed_actors": ["刑事"], "time_min": 15},
            ],
        },
        "駅裏": {
            "exits": [
                {"to": "高架下", "allowed_actors": ["愉快犯"], "time_min": 6},
                {"to": "警察署_控室", "allowed_actors": ["刑事"], "time_min": 20},
            ],
        },
    }


def _active_inquiry_operation():
    return {
        "id": "op_inquiry_刑事",
        "type": "inquiry",
        "label": "聞き込みを始める",
        "status": "active",
        "phase": "start",
        "actor_id": "刑事",
        "mini_goal": {
            "id": "mini_goal_first_testimony",
            "label": "最初の証言を取る",
            "status": "active",
        },
        "notes": [],
    }


def _world():
    return {
        "locations": {"default": "拠点_安アパート"},
        "actor_locations": {
            "刑事": "酒場",
            "愉快犯": "駅裏",
        },
        "actor_modes": {
            "刑事": "WITNESS",
            "愉快犯": "FLEE",
        },
        "actor_discoveries": {
            "刑事": ["camera_skew_noticed"],
            "愉快犯": ["unsafe_route_identified"],
        },
        "actor_operations": {
            "刑事": {"active_operation": _active_inquiry_operation()},
        },
        "location_graph": _location_graph(),
    }


def test_build_perceived_world_for_detective():
    perceived = build_perceived_world("刑事", _world())

    assert perceived["actor_id"] == "刑事"
    assert perceived["location"] == "酒場"
    assert perceived["actor_mode"] == "WITNESS"
    assert "camera_skew_noticed" in perceived["discoveries"]
    assert isinstance(perceived["visible_routes"], list)
    assert any("監視カメラ" in text for text in perceived["interpretations"])


def test_build_perceived_world_for_trickster():
    perceived = build_perceived_world("愉快犯", _world())

    assert perceived["actor_id"] == "愉快犯"
    assert perceived["location"] == "駅裏"
    assert perceived["actor_mode"] == "FLEE"
    assert "unsafe_route_identified" in perceived["discoveries"]
    assert any("逃走経路に危険" in text for text in perceived["interpretations"])


def test_perceived_world_interpretations_are_actor_specific():
    world = _world()

    detective = build_perceived_world("刑事", world)
    trickster = build_perceived_world("愉快犯", world)

    assert detective["interpretations"] != trickster["interpretations"]
    assert any(
        "証言" in text or "監視カメラ" in text or "聞き込み" in text
        for text in detective["interpretations"]
    )
    assert any(
        "逃走" in text or "危険" in text or "撹乱" in text or "注意を逸らす" in text
        for text in trickster["interpretations"]
    )


def test_perceived_world_visible_routes_respect_location_graph():
    world = _world()
    world["actor_locations"]["刑事"] = "警察署_控室"
    world["actor_locations"]["愉快犯"] = "警察署_控室"

    detective = build_perceived_world("刑事", world)
    trickster = build_perceived_world("愉快犯", world)

    assert "酒場" in detective["visible_routes"]
    assert "事件現場_路地裏" in detective["visible_routes"]
    assert "駅裏" not in detective["visible_routes"]
    assert trickster["visible_routes"] == ["駅裏"]


def test_perceived_world_includes_active_operation_summary():
    perceived = build_perceived_world("刑事", _world())

    assert perceived["active_operation"]["type"] == "inquiry"
    assert perceived["active_operation"]["label"] == "聞き込みを始める"
    assert perceived["active_operation"]["status"] == "active"
    assert perceived["active_operation"]["phase"] == "start"
    assert perceived["active_operation"]["mini_goal"] == "最初の証言を取る"
    assert any("聞き込みを進め" in text for text in perceived["interpretations"])


def test_perceived_world_is_not_persisted():
    world = _world()
    before = copy.deepcopy(world)

    build_perceived_world("刑事", world)

    assert world == before
    assert "perceived_world" not in world
    assert "perceived_worlds" not in world


def test_hud_debug_displays_perceived_world_summary():
    perceived = build_perceived_world("刑事", _world())

    summary = format_perceived_world_summary(perceived)

    assert "Perceived(刑事)" in summary
    assert "酒場 / WITNESS" in summary
    assert "解釈:" in summary
    assert "監視カメラ" in summary
    assert 1 <= len(summary.splitlines()) <= 3
