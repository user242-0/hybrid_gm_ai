import copy
import json

import pytest
import yaml

from src.rc_ai import generate_rc_advisory


def _inquiry_bundle():
    return {
        "actor_id": "刑事",
        "emotion": {"R": 127, "G": 127, "B": 255},
        "active_operation": {
            "type": "inquiry",
            "status": "active",
            "phase": "start",
            "mini_goal_id": "mini_goal_choose_first_inquiry_target",
            "mini_goal": "聞き込み先を一件選ぶ",
        },
        "available_actions": {
            "gui": [],
            "hud": [
                {
                    "action_id": "start_inquiry_operation",
                    "action_layer": "HUD",
                    "rc_ai_eligible": True,
                },
                {
                    "action_id": "compare_testimony_time",
                    "action_layer": "HUD",
                    "rc_ai_eligible": True,
                },
                {
                    "action_id": "choose_first_inquiry_target",
                    "action_layer": "HUD",
                    "params": {},
                    "rc_ai_eligible": True,
                },
            ],
            "meta": [
                {
                    "action_id": "switch_character",
                    "action_layer": "META",
                    "rc_ai_eligible": False,
                }
            ],
        },
    }


def _trickster_flee_bundle():
    return {
        "actor_id": "愉快犯",
        "actor_mode": "FLEE",
        "active_operation": None,
        "perceived_world": {
            "actor_id": "愉快犯",
            "discoveries": ["unsafe_route_identified"],
        },
        "available_actions": {
            "gui": [],
            "hud": [
                {
                    "action_id": "mark_avoid_shop",
                    "action_layer": "HUD",
                    "rc_ai_eligible": True,
                },
                {
                    "action_id": "change_escape_route",
                    "action_layer": "HUD",
                    "params": {},
                    "rc_ai_eligible": True,
                },
            ],
            "meta": [],
        },
    }


def test_generate_rc_advisory_selects_first_inquiry_target():
    advisory = generate_rc_advisory(_inquiry_bundle())

    assert advisory == {
        "schema_version": "rc_advisory_v0.1",
        "actor_id": "刑事",
        "interpretation": "聞き込みOperationが進行中で、最初の証言を固める段階にいる。",
        "selected_intent": "advance_inquiry_first_testimony",
        "preferred_action_id": "choose_first_inquiry_target",
        "preferred_action_layer": "HUD",
        "preferred_params": {},
        "rationale": "active inquiry OperationのMiniGoalに直接対応する利用可能候補だから。",
        "confidence": 1.0,
        "auto_execute": False,
    }


def test_generate_rc_advisory_accepts_legacy_first_testimony_mini_goal_id():
    bundle = _inquiry_bundle()
    bundle["active_operation"]["mini_goal_id"] = "mini_goal_first_testimony"

    advisory = generate_rc_advisory(bundle)

    assert advisory["selected_intent"] == "advance_inquiry_first_testimony"
    assert advisory["preferred_action_id"] == "choose_first_inquiry_target"


def test_next_inquiry_mini_goal_has_no_unimplemented_advisory():
    bundle = _inquiry_bundle()
    bundle["active_operation"]["phase"] = "target_selected"
    bundle["active_operation"]["mini_goal_id"] = "mini_goal_take_first_testimony"
    bundle["active_operation"]["mini_goal"] = "最初の証言を取る"

    advisory = generate_rc_advisory(bundle)

    assert advisory["selected_intent"] == "no_safe_action"
    assert advisory["preferred_action_id"] is None


@pytest.mark.parametrize("status", ["completed", "suspended", None])
def test_generate_rc_advisory_requires_active_operation(status):
    bundle = _inquiry_bundle()
    bundle["active_operation"]["status"] = status

    advisory = generate_rc_advisory(bundle)

    assert advisory["selected_intent"] == "no_safe_action"
    assert advisory["preferred_action_id"] is None


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("type", "pursuit"),
        ("mini_goal_id", "mini_goal_other"),
    ],
)
def test_generate_rc_advisory_requires_exact_inquiry_context(field, value):
    bundle = _inquiry_bundle()
    bundle["active_operation"][field] = value

    assert generate_rc_advisory(bundle)["selected_intent"] == "no_safe_action"


def test_generate_rc_advisory_requires_available_eligible_action():
    missing = _inquiry_bundle()
    missing["available_actions"]["hud"] = []
    ineligible = _inquiry_bundle()
    ineligible["available_actions"]["hud"][-1]["rc_ai_eligible"] = False

    assert generate_rc_advisory(missing)["preferred_action_id"] is None
    assert generate_rc_advisory(ineligible)["preferred_action_id"] is None


def test_generate_rc_advisory_does_not_select_meta_action_mislabeled_as_hud():
    bundle = _inquiry_bundle()
    bundle["available_actions"]["hud"][-1]["action_layer"] = "META"

    assert generate_rc_advisory(bundle)["preferred_action_id"] is None


def test_generate_rc_advisory_does_not_use_other_actor_context():
    bundle = _inquiry_bundle()
    bundle["actor_id"] = "愉快犯"

    assert generate_rc_advisory(bundle)["selected_intent"] == "no_safe_action"


@pytest.mark.parametrize("bundle", [None, [], {}, {"actor_id": "刑事"}])
def test_generate_rc_advisory_handles_incomplete_input(bundle):
    advisory = generate_rc_advisory(bundle)

    assert advisory["selected_intent"] == "no_safe_action"
    assert advisory["preferred_action_id"] is None
    assert advisory["auto_execute"] is False


def test_generate_rc_advisory_is_read_only_deterministic_and_serializable():
    bundle = _inquiry_bundle()
    before = copy.deepcopy(bundle)

    first = generate_rc_advisory(bundle)
    second = generate_rc_advisory(bundle)

    assert bundle == before
    assert first == second
    yaml.safe_dump(first, allow_unicode=True, sort_keys=False)
    json.dumps(first, ensure_ascii=False)


def test_inquiry_rule_is_not_overridden_by_rgb():
    low_empathy = _inquiry_bundle()
    low_empathy["emotion"] = {"R": 255, "G": 0, "B": 0}
    high_empathy = _inquiry_bundle()
    high_empathy["emotion"] = {"R": 0, "G": 255, "B": 255}

    assert (
        generate_rc_advisory(low_empathy)["preferred_action_id"]
        == generate_rc_advisory(high_empathy)["preferred_action_id"]
        == "choose_first_inquiry_target"
    )


def test_generate_rc_advisory_selects_trickster_escape_route():
    advisory = generate_rc_advisory(_trickster_flee_bundle())

    assert advisory == {
        "schema_version": "rc_advisory_v0.1",
        "actor_id": "愉快犯",
        "interpretation": "逃走経路に危険を認識しており、安全な経路へ切り替える必要がある。",
        "selected_intent": "avoid_unsafe_escape_route",
        "preferred_action_id": "change_escape_route",
        "preferred_action_layer": "HUD",
        "preferred_params": {},
        "rationale": "逃走経路の危険を認識しており、直接対応する利用可能候補だから。",
        "confidence": 1.0,
        "auto_execute": False,
    }


def test_trickster_reactive_intent_ignores_hud_candidate_order():
    bundle = _trickster_flee_bundle()
    assert bundle["available_actions"]["hud"][0]["action_id"] == "mark_avoid_shop"

    advisory = generate_rc_advisory(bundle)

    assert advisory["preferred_action_id"] == "change_escape_route"


@pytest.mark.parametrize("mode", ["MISLEAD", "PROVOKE", "ESCALATE", None])
def test_trickster_reactive_intent_requires_flee_mode(mode):
    bundle = _trickster_flee_bundle()
    bundle["actor_mode"] = mode

    assert generate_rc_advisory(bundle)["selected_intent"] == "no_safe_action"


@pytest.mark.parametrize("discoveries", [None, {}, "unsafe_route_identified", []])
def test_trickster_reactive_intent_requires_perceived_discovery(discoveries):
    bundle = _trickster_flee_bundle()
    bundle["perceived_world"]["discoveries"] = discoveries

    assert generate_rc_advisory(bundle)["selected_intent"] == "no_safe_action"


@pytest.mark.parametrize("perceived_world", [None, [], "invalid"])
def test_trickster_reactive_intent_requires_perceived_world_dict(perceived_world):
    bundle = _trickster_flee_bundle()
    bundle["perceived_world"] = perceived_world

    assert generate_rc_advisory(bundle)["selected_intent"] == "no_safe_action"


def test_trickster_reactive_intent_ignores_non_perceived_discovery_sources():
    bundle = _trickster_flee_bundle()
    bundle["perceived_world"]["discoveries"] = []
    bundle["actor_discoveries"] = {
        "刑事": ["unsafe_route_identified"],
        "愉快犯": ["unsafe_route_identified"],
    }
    bundle["affordances"] = {"discoveries": ["unsafe_route_identified"]}

    assert generate_rc_advisory(bundle)["selected_intent"] == "no_safe_action"


def test_trickster_reactive_intent_accepts_duplicate_discovery():
    bundle = _trickster_flee_bundle()
    bundle["perceived_world"]["discoveries"].append("unsafe_route_identified")

    assert generate_rc_advisory(bundle)["selected_intent"] == "avoid_unsafe_escape_route"


def test_active_operation_blocks_trickster_reactive_fallthrough():
    bundle = _trickster_flee_bundle()
    bundle["active_operation"] = {
        "type": "escape",
        "status": "active",
        "mini_goal_id": "unsupported_escape_goal",
    }

    assert generate_rc_advisory(bundle)["selected_intent"] == "no_safe_action"


@pytest.mark.parametrize("status", ["completed", "suspended", "inactive"])
def test_non_active_operation_allows_trickster_reactive_intent(status):
    bundle = _trickster_flee_bundle()
    bundle["active_operation"] = {"type": "escape", "status": status}

    assert generate_rc_advisory(bundle)["selected_intent"] == "avoid_unsafe_escape_route"


@pytest.mark.parametrize(
    "operation",
    [[], "invalid", {}, {"status": None}, {"status": 1}],
)
def test_malformed_operation_blocks_reactive_intent_safely(operation):
    bundle = _trickster_flee_bundle()
    bundle["active_operation"] = operation

    assert generate_rc_advisory(bundle)["selected_intent"] == "no_safe_action"


def test_trickster_reactive_intent_requires_preferred_action():
    bundle = _trickster_flee_bundle()
    bundle["available_actions"]["hud"] = [bundle["available_actions"]["hud"][0]]

    assert generate_rc_advisory(bundle)["selected_intent"] == "no_safe_action"


@pytest.mark.parametrize("eligible", [False, None])
def test_trickster_reactive_intent_requires_explicit_eligibility(eligible):
    bundle = _trickster_flee_bundle()
    action = bundle["available_actions"]["hud"][1]
    if eligible is None:
        action.pop("rc_ai_eligible")
    else:
        action["rc_ai_eligible"] = eligible

    assert generate_rc_advisory(bundle)["selected_intent"] == "no_safe_action"


@pytest.mark.parametrize("layer", ["GUI", "META", None])
def test_trickster_reactive_intent_requires_hud_layer(layer):
    bundle = _trickster_flee_bundle()
    action = bundle["available_actions"]["hud"][1]
    if layer is None:
        action.pop("action_layer")
    else:
        action["action_layer"] = layer

    assert generate_rc_advisory(bundle)["selected_intent"] == "no_safe_action"


def test_trickster_advisory_is_read_only_deterministic_and_serializable():
    bundle = _trickster_flee_bundle()
    before = copy.deepcopy(bundle)

    first = generate_rc_advisory(bundle)
    second = generate_rc_advisory(bundle)

    assert bundle == before
    assert first == second
    yaml.safe_dump(first, allow_unicode=True, sort_keys=False)
    json.dumps(first, ensure_ascii=False)


def test_detective_active_inquiry_still_wins_after_reactive_rule_added():
    bundle = _inquiry_bundle()
    bundle["actor_mode"] = "FLEE"
    bundle["perceived_world"] = {"discoveries": ["unsafe_route_identified"]}

    advisory = generate_rc_advisory(bundle)

    assert advisory["selected_intent"] == "advance_inquiry_first_testimony"
    assert advisory["preferred_action_id"] == "choose_first_inquiry_target"
