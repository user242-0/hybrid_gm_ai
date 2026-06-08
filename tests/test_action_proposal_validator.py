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


def test_b_uniqueness_pass_still_leaves_overall_unknown_because_d_through_f_are_unknown():
    report = validate_proposal(
        valid_proposal(),
        active_action_ids={"open_locked_door"},
        known_requirement_keys={"location"},
    )

    assert report.checks["B_uniqueness"] == ValidationResult.PASS
    assert report.checks["C_requirements"] == ValidationResult.PASS
    assert report.checks["D_effects"] == ValidationResult.UNKNOWN
    assert report.checks["E_safety"] == ValidationResult.UNKNOWN
    assert report.checks["F_narrative"] == ValidationResult.UNKNOWN
    assert report.overall == ValidationResult.UNKNOWN


def test_current_d_through_f_checks_are_unknown():
    report = validate_proposal(valid_proposal())

    assert report.checks["D_effects"] == ValidationResult.UNKNOWN
    assert report.checks["E_safety"] == ValidationResult.UNKNOWN
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


def test_a_b_c_pass_still_leaves_overall_unknown_because_d_through_f_are_unknown():
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
    assert report.checks["D_effects"] == ValidationResult.UNKNOWN
    assert report.checks["E_safety"] == ValidationResult.UNKNOWN
    assert report.checks["F_narrative"] == ValidationResult.UNKNOWN
    assert report.overall == ValidationResult.UNKNOWN
