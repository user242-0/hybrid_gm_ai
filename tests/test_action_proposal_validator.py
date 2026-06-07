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


def test_current_b_through_f_checks_are_unknown():
    report = validate_proposal(valid_proposal())

    assert report.checks["B_uniqueness"] == ValidationResult.UNKNOWN
    assert report.checks["C_requirements"] == ValidationResult.UNKNOWN
    assert report.checks["D_effects"] == ValidationResult.UNKNOWN
    assert report.checks["E_safety"] == ValidationResult.UNKNOWN
    assert report.checks["F_narrative"] == ValidationResult.UNKNOWN


def test_valid_proposal_overall_is_unknown_because_b_through_f_are_unknown():
    report = validate_proposal(valid_proposal())

    assert report.checks["A_syntax"] == ValidationResult.PASS
    assert report.overall == ValidationResult.UNKNOWN
