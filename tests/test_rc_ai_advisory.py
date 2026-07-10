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
            "mini_goal_id": "mini_goal_first_testimony",
            "mini_goal": "最初の証言を取る",
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
