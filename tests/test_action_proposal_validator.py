import pytest

from src.action_proposal.validator import ValidationResult, validate_proposal


def valid_proposal():
    return {
        "id": "search_hidden_room",
        "label": "Search the hidden room",
        "time_min": 10,
    }


def test_valid_proposal_has_passing_syntax_check():
    report = validate_proposal(valid_proposal())

    assert report.checks["A_syntax"] == ValidationResult.PASS


@pytest.mark.parametrize("missing_field", ["id", "label", "time_min"])
def test_missing_required_field_rejects_overall(missing_field):
    proposal = valid_proposal()
    proposal.pop(missing_field)

    report = validate_proposal(proposal)

    assert report.overall == ValidationResult.REJECT


@pytest.mark.parametrize("proposal_id", ["SearchRoom", "search-room", "1_search_room"])
def test_non_snake_case_id_rejects_overall(proposal_id):
    proposal = valid_proposal()
    proposal["id"] = proposal_id

    report = validate_proposal(proposal)

    assert report.overall == ValidationResult.REJECT


@pytest.mark.parametrize("time_min", [-1, 1.5, "10"])
def test_negative_or_non_integer_time_min_rejects_overall(time_min):
    proposal = valid_proposal()
    proposal["time_min"] = time_min

    report = validate_proposal(proposal)

    assert report.overall == ValidationResult.REJECT


def test_b_uniqueness_is_unknown_when_active_action_ids_is_none():
    report = validate_proposal(valid_proposal(), active_action_ids=None)

    assert report.checks["B_uniqueness"] == ValidationResult.UNKNOWN
    assert report.reasons["B_uniqueness"] == "active_action_ids not provided"


def test_b_uniqueness_rejects_duplicate_proposal_id():
    proposal = valid_proposal()

    report = validate_proposal(proposal, active_action_ids={"search_hidden_room"})

    assert report.checks["B_uniqueness"] == ValidationResult.REJECT
    assert "search_hidden_room" in report.reasons["B_uniqueness"]


def test_b_uniqueness_passes_when_proposal_id_is_new():
    report = validate_proposal(valid_proposal(), active_action_ids={"open_locked_door"})

    assert report.checks["B_uniqueness"] == ValidationResult.PASS


def test_duplicate_proposal_id_rejects_overall():
    report = validate_proposal(valid_proposal(), active_action_ids={"search_hidden_room"})

    assert report.checks["B_uniqueness"] == ValidationResult.REJECT
    assert report.overall == ValidationResult.REJECT


def test_b_uniqueness_pass_still_leaves_overall_unknown_because_f_is_unknown():
    report = validate_proposal(
        valid_proposal(),
        active_action_ids={"open_locked_door"},
        known_requirement_keys={"location"},
    )

    assert report.checks["B_uniqueness"] == ValidationResult.PASS
    assert report.checks["C_requirements"] == ValidationResult.PASS
    assert report.checks["D_effects"] == ValidationResult.PASS
    assert report.checks["E_safety"] == ValidationResult.PASS
    assert report.checks["F_narrative"] == ValidationResult.UNKNOWN
    assert report.overall == ValidationResult.UNKNOWN


def test_d_effects_passes_when_effects_are_missing():
    report = validate_proposal(valid_proposal())

    assert report.checks["D_effects"] == ValidationResult.PASS


def test_d_effects_passes_when_effects_are_none():
    proposal = valid_proposal()
    proposal["effects"] = None

    report = validate_proposal(proposal)

    assert report.checks["D_effects"] == ValidationResult.PASS


def test_d_effects_passes_when_effects_are_empty_dict():
    proposal = valid_proposal()
    proposal["effects"] = {}

    report = validate_proposal(proposal)

    assert report.checks["D_effects"] == ValidationResult.PASS


def test_d_effects_passes_when_effects_are_empty_list():
    proposal = valid_proposal()
    proposal["effects"] = []

    report = validate_proposal(proposal)

    assert report.checks["D_effects"] == ValidationResult.PASS


def test_d_effects_dict_unknown_when_known_effect_paths_are_not_provided():
    proposal = valid_proposal()
    proposal["effects"] = {"evidence_score": "+3"}

    report = validate_proposal(proposal, known_effect_paths=None)

    assert report.checks["D_effects"] == ValidationResult.UNKNOWN
    assert report.reasons["D_effects"] == "known_effect_paths not provided"


def test_d_effects_dict_rejects_unknown_path():
    proposal = valid_proposal()
    proposal["effects"] = {"evidence_score": "+3", "unknown_path": True}

    report = validate_proposal(proposal, known_effect_paths={"evidence_score"})

    assert report.checks["D_effects"] == ValidationResult.REJECT
    assert "unknown_path" in report.reasons["D_effects"]


def test_d_effects_dict_passes_when_all_paths_are_known():
    proposal = valid_proposal()
    proposal["effects"] = {"evidence_score": "+3"}

    report = validate_proposal(proposal, known_effect_paths={"evidence_score"})

    assert report.checks["D_effects"] == ValidationResult.PASS


def test_d_effects_list_unknown_when_known_effect_paths_are_not_provided():
    proposal = valid_proposal()
    proposal["effects"] = [{"op": "add", "path": "evidence_score", "value": 3}]

    report = validate_proposal(proposal, known_effect_paths=None)

    assert report.checks["D_effects"] == ValidationResult.UNKNOWN
    assert report.reasons["D_effects"] == "known_effect_paths not provided"


def test_d_effects_list_passes_when_all_paths_are_known():
    proposal = valid_proposal()
    proposal["effects"] = [
        {"op": "add", "path": "evidence_score", "value": 3},
        {"op": "set", "path": "alarm_state", "value": "raised"},
    ]

    report = validate_proposal(
        proposal,
        known_effect_paths={"evidence_score", "alarm_state"},
    )

    assert report.checks["D_effects"] == ValidationResult.PASS


def test_d_effects_list_rejects_unknown_path():
    proposal = valid_proposal()
    proposal["effects"] = [{"op": "add", "path": "unknown_path", "value": 3}]

    report = validate_proposal(proposal, known_effect_paths={"evidence_score"})

    assert report.checks["D_effects"] == ValidationResult.REJECT
    assert "unknown_path" in report.reasons["D_effects"]


def test_d_effects_rejects_non_dict_or_list_effects():
    proposal = valid_proposal()
    proposal["effects"] = "evidence_score +3"

    report = validate_proposal(proposal)

    assert report.checks["D_effects"] == ValidationResult.REJECT
    assert report.reasons["D_effects"] == "effects must be a dict or list"


def test_d_effects_list_rejects_non_dict_item():
    proposal = valid_proposal()
    proposal["effects"] = ["evidence_score"]

    report = validate_proposal(proposal)

    assert report.checks["D_effects"] == ValidationResult.REJECT


def test_d_effects_list_rejects_item_without_op():
    proposal = valid_proposal()
    proposal["effects"] = [{"path": "evidence_score", "value": 3}]

    report = validate_proposal(proposal)

    assert report.checks["D_effects"] == ValidationResult.REJECT


def test_d_effects_list_rejects_item_without_path():
    proposal = valid_proposal()
    proposal["effects"] = [{"op": "add", "value": 3}]

    report = validate_proposal(proposal)

    assert report.checks["D_effects"] == ValidationResult.REJECT


def test_d_effects_list_rejects_unknown_op():
    proposal = valid_proposal()
    proposal["effects"] = [{"op": "remove", "path": "evidence_score", "value": 3}]

    report = validate_proposal(proposal)

    assert report.checks["D_effects"] == ValidationResult.REJECT


@pytest.mark.parametrize("path", ["", 123])
def test_d_effects_list_rejects_empty_or_non_string_path(path):
    proposal = valid_proposal()
    proposal["effects"] = [{"op": "add", "path": path, "value": 3}]

    report = validate_proposal(proposal)

    assert report.checks["D_effects"] == ValidationResult.REJECT


def test_d_effects_reject_makes_overall_reject():
    proposal = valid_proposal()
    proposal["effects"] = {"unknown_path": True}

    report = validate_proposal(
        proposal,
        active_action_ids={"open_locked_door"},
        known_requirement_keys={"location"},
        known_effect_paths={"evidence_score"},
    )

    assert report.checks["A_syntax"] == ValidationResult.PASS
    assert report.checks["B_uniqueness"] == ValidationResult.PASS
    assert report.checks["C_requirements"] == ValidationResult.PASS
    assert report.checks["D_effects"] == ValidationResult.REJECT
    assert report.overall == ValidationResult.REJECT


def test_a_b_c_d_pass_still_leaves_overall_unknown_because_e_and_f_are_unknown():
    proposal = valid_proposal()
    proposal["requirements"] = {"location": "room"}
    proposal["effects"] = {"evidence_score": "+3"}

    report = validate_proposal(
        proposal,
        active_action_ids={"open_locked_door"},
        known_requirement_keys={"location"},
        known_effect_paths={"evidence_score"},
    )

    assert report.checks["A_syntax"] == ValidationResult.PASS
    assert report.checks["B_uniqueness"] == ValidationResult.PASS
    assert report.checks["C_requirements"] == ValidationResult.PASS
    assert report.checks["D_effects"] == ValidationResult.PASS
    assert report.checks["E_safety"] == ValidationResult.UNKNOWN
    assert report.checks["F_narrative"] == ValidationResult.UNKNOWN
    assert report.overall == ValidationResult.UNKNOWN


def test_empty_effects_make_e_pass_and_f_remains_unknown():
    report = validate_proposal(valid_proposal())

    assert report.checks["D_effects"] == ValidationResult.PASS
    assert report.checks["E_safety"] == ValidationResult.PASS
    assert report.checks["F_narrative"] == ValidationResult.UNKNOWN


def test_valid_proposal_overall_is_unknown_because_b_through_f_are_unknown():
    report = validate_proposal(valid_proposal())

    assert report.checks["A_syntax"] == ValidationResult.PASS
    assert report.overall == ValidationResult.UNKNOWN


def test_c_requirements_passes_when_requirements_are_missing():
    report = validate_proposal(valid_proposal())

    assert report.checks["C_requirements"] == ValidationResult.PASS


def test_c_requirements_passes_when_requirements_are_none():
    proposal = valid_proposal()
    proposal["requirements"] = None

    report = validate_proposal(proposal)

    assert report.checks["C_requirements"] == ValidationResult.PASS


def test_c_requirements_passes_when_requirements_are_empty_dict():
    proposal = valid_proposal()
    proposal["requirements"] = {}

    report = validate_proposal(proposal)

    assert report.checks["C_requirements"] == ValidationResult.PASS


def test_c_requirements_rejects_non_dict_requirements():
    proposal = valid_proposal()
    proposal["requirements"] = ["location"]

    report = validate_proposal(proposal)

    assert report.checks["C_requirements"] == ValidationResult.REJECT
    assert report.reasons["C_requirements"] == "requirements must be a dict"


def test_c_requirements_unknown_when_known_requirement_keys_are_not_provided():
    proposal = valid_proposal()
    proposal["requirements"] = {"location": "事件現場_路地裏"}

    report = validate_proposal(proposal, known_requirement_keys=None)

    assert report.checks["C_requirements"] == ValidationResult.UNKNOWN
    assert report.reasons["C_requirements"] == "known_requirement_keys not provided"


def test_c_requirements_rejects_unknown_requirement_key():
    proposal = valid_proposal()
    proposal["requirements"] = {"location": "事件現場_路地裏", "unknown_key": True}

    report = validate_proposal(proposal, known_requirement_keys={"location"})

    assert report.checks["C_requirements"] == ValidationResult.REJECT
    assert "unknown_key" in report.reasons["C_requirements"]


def test_c_requirements_passes_when_all_requirement_keys_are_known():
    proposal = valid_proposal()
    proposal["requirements"] = {"location": "事件現場_路地裏", "flag": True}

    report = validate_proposal(proposal, known_requirement_keys={"location", "flag"})

    assert report.checks["C_requirements"] == ValidationResult.PASS


def test_c_requirements_reject_makes_overall_reject():
    proposal = valid_proposal()
    proposal["requirements"] = {"unknown_key": True}

    report = validate_proposal(
        proposal,
        active_action_ids={"open_locked_door"},
        known_requirement_keys={"location"},
    )

    assert report.checks["A_syntax"] == ValidationResult.PASS
    assert report.checks["B_uniqueness"] == ValidationResult.PASS
    assert report.checks["C_requirements"] == ValidationResult.REJECT
    assert report.overall == ValidationResult.REJECT


def test_a_b_c_pass_still_leaves_overall_unknown_because_f_is_unknown():
    proposal = valid_proposal()
    proposal["requirements"] = {"location": "事件現場_路地裏"}

    report = validate_proposal(
        proposal,
        active_action_ids={"open_locked_door"},
        known_requirement_keys={"location"},
    )

    assert report.checks["A_syntax"] == ValidationResult.PASS
    assert report.checks["B_uniqueness"] == ValidationResult.PASS
    assert report.checks["C_requirements"] == ValidationResult.PASS
    assert report.checks["D_effects"] == ValidationResult.PASS
    assert report.checks["E_safety"] == ValidationResult.PASS
    assert report.checks["F_narrative"] == ValidationResult.UNKNOWN
    assert report.overall == ValidationResult.UNKNOWN


def fully_known_report(proposal, safety_limits=None):
    return validate_proposal(
        proposal,
        active_action_ids={"open_locked_door"},
        known_requirement_keys={"location", "flag"},
        known_effect_paths={
            "alarm_state",
            "death_count",
            "evidence_score",
            "harm.value",
            "suspicion.value",
        },
        safety_limits=safety_limits,
    )


def test_e_safety_passes_when_effects_are_missing():
    report = fully_known_report(valid_proposal(), safety_limits={})

    assert report.checks["E_safety"] == ValidationResult.PASS


def test_e_safety_passes_when_effects_are_none():
    proposal = valid_proposal()
    proposal["effects"] = None

    report = fully_known_report(proposal, safety_limits={})

    assert report.checks["E_safety"] == ValidationResult.PASS


def test_e_safety_passes_when_effects_are_empty_dict():
    proposal = valid_proposal()
    proposal["effects"] = {}

    report = fully_known_report(proposal, safety_limits={})

    assert report.checks["E_safety"] == ValidationResult.PASS


def test_e_safety_passes_when_effects_are_empty_list():
    proposal = valid_proposal()
    proposal["effects"] = []

    report = fully_known_report(proposal, safety_limits={})

    assert report.checks["E_safety"] == ValidationResult.PASS


def test_e_safety_unknown_for_non_empty_effects_without_safety_limits():
    proposal = valid_proposal()
    proposal["effects"] = {"evidence_score": "+3"}

    report = fully_known_report(proposal, safety_limits=None)

    assert report.checks["E_safety"] == ValidationResult.UNKNOWN
    assert report.reasons["E_safety"] == "safety_limits not provided"


def test_e_safety_unknown_when_safety_limits_is_not_a_dict():
    proposal = valid_proposal()
    proposal["effects"] = {"evidence_score": "+3"}

    report = fully_known_report(proposal, safety_limits=["not", "a", "dict"])

    assert report.checks["E_safety"] == ValidationResult.UNKNOWN
    assert report.reasons["E_safety"] == "safety_limits must be a dict"


def test_e_safety_rejects_forbidden_path_in_dict_effects():
    proposal = valid_proposal()
    proposal["effects"] = {"harm.value": "+1"}

    report = fully_known_report(proposal, safety_limits={"forbidden_effect_paths": {"harm.value"}})

    assert report.checks["E_safety"] == ValidationResult.REJECT
    assert "harm.value" in report.reasons["E_safety"]


def test_e_safety_rejects_forbidden_path_in_list_effects():
    proposal = valid_proposal()
    proposal["effects"] = [{"op": "add", "path": "death_count", "value": 1}]

    report = fully_known_report(proposal, safety_limits={"forbidden_effect_paths": {"death_count"}})

    assert report.checks["E_safety"] == ValidationResult.REJECT
    assert "death_count" in report.reasons["E_safety"]


def test_e_safety_passes_dict_add_string_within_global_delta_limit():
    proposal = valid_proposal()
    proposal["effects"] = {"evidence_score": "+3"}

    report = fully_known_report(proposal, safety_limits={"max_abs_delta": 10})

    assert report.checks["E_safety"] == ValidationResult.PASS


def test_e_safety_rejects_dict_add_string_over_global_delta_limit():
    proposal = valid_proposal()
    proposal["effects"] = {"evidence_score": "+99"}

    report = fully_known_report(proposal, safety_limits={"max_abs_delta": 10})

    assert report.checks["E_safety"] == ValidationResult.REJECT
    assert "evidence_score" in report.reasons["E_safety"]


def test_e_safety_passes_list_add_within_global_delta_limit():
    proposal = valid_proposal()
    proposal["effects"] = [{"op": "add", "path": "evidence_score", "value": 3}]

    report = fully_known_report(proposal, safety_limits={"max_abs_delta": 10})

    assert report.checks["E_safety"] == ValidationResult.PASS


def test_e_safety_rejects_list_add_over_global_delta_limit():
    proposal = valid_proposal()
    proposal["effects"] = [{"op": "add", "path": "evidence_score", "value": 99}]

    report = fully_known_report(proposal, safety_limits={"max_abs_delta": 10})

    assert report.checks["E_safety"] == ValidationResult.REJECT
    assert "evidence_score" in report.reasons["E_safety"]


def test_e_safety_path_specific_delta_limit_overrides_global_limit():
    proposal = valid_proposal()
    proposal["effects"] = [{"op": "add", "path": "suspicion.value", "value": 4}]

    report = fully_known_report(
        proposal,
        safety_limits={
            "max_abs_delta": 10,
            "max_abs_delta_by_path": {"suspicion.value": 3},
        },
    )

    assert report.checks["E_safety"] == ValidationResult.REJECT
    assert "suspicion.value" in report.reasons["E_safety"]


def test_e_safety_does_not_apply_delta_limit_to_set_op():
    proposal = valid_proposal()
    proposal["effects"] = [{"op": "set", "path": "evidence_score", "value": 99}]

    report = fully_known_report(proposal, safety_limits={"max_abs_delta": 10})

    assert report.checks["E_safety"] == ValidationResult.PASS


def test_e_safety_unknown_when_add_value_is_not_numeric():
    proposal = valid_proposal()
    proposal["effects"] = [{"op": "add", "path": "evidence_score", "value": "many"}]

    report = fully_known_report(proposal, safety_limits={"max_abs_delta": 10})

    assert report.checks["E_safety"] == ValidationResult.UNKNOWN
    assert "not numeric" in report.reasons["E_safety"]


def test_e_safety_reject_makes_overall_reject():
    proposal = valid_proposal()
    proposal["effects"] = [{"op": "add", "path": "evidence_score", "value": 99}]

    report = fully_known_report(proposal, safety_limits={"max_abs_delta": 10})

    assert report.checks["A_syntax"] == ValidationResult.PASS
    assert report.checks["B_uniqueness"] == ValidationResult.PASS
    assert report.checks["C_requirements"] == ValidationResult.PASS
    assert report.checks["D_effects"] == ValidationResult.PASS
    assert report.checks["E_safety"] == ValidationResult.REJECT
    assert report.overall == ValidationResult.REJECT


def test_a_b_c_d_e_pass_still_leaves_overall_unknown_because_f_is_unknown():
    proposal = valid_proposal()
    proposal["requirements"] = {"location": "room"}
    proposal["effects"] = [{"op": "add", "path": "evidence_score", "value": 3}]

    report = fully_known_report(proposal, safety_limits={"max_abs_delta": 10})

    assert report.checks["A_syntax"] == ValidationResult.PASS
    assert report.checks["B_uniqueness"] == ValidationResult.PASS
    assert report.checks["C_requirements"] == ValidationResult.PASS
    assert report.checks["D_effects"] == ValidationResult.PASS
    assert report.checks["E_safety"] == ValidationResult.PASS
    assert report.checks["F_narrative"] == ValidationResult.UNKNOWN
    assert report.overall == ValidationResult.UNKNOWN
