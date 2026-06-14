import pytest

from src.action_proposal.validator import CHECK_ORDER, ValidationResult, validate_proposal


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


def fully_known_report(proposal, safety_limits=None, narrative_context=None):
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
        narrative_context=narrative_context,
    )


def base_narrative_context(**overrides):
    context = {
        "current_mode": "PURSUE",
        "allowed_modes": {"FREEZE", "FLEE", "PURSUE", "WITNESS"},
        "tone": {"neo-noir", "slow_burn"},
        "forbidden_tags": {"world_breaking", "comedy_gag"},
        "allowed_sources": {"RO", "LLM", "pack", "human"},
        "require_rationale": False,
    }
    context.update(overrides)
    return context


def fully_known_narrative_report(proposal=None, narrative_context=None):
    return fully_known_report(
        proposal or valid_proposal(),
        safety_limits={},
        narrative_context=base_narrative_context() if narrative_context is None else narrative_context,
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


def test_f_narrative_unknown_when_context_is_none():
    report = fully_known_report(valid_proposal(), safety_limits={}, narrative_context=None)

    assert report.checks["F_narrative"] == ValidationResult.UNKNOWN
    assert report.reasons["F_narrative"] == "narrative_context not provided"


def test_f_narrative_unknown_when_context_is_not_dict():
    report = fully_known_report(valid_proposal(), safety_limits={}, narrative_context=["not", "a", "dict"])

    assert report.checks["F_narrative"] == ValidationResult.UNKNOWN
    assert report.reasons["F_narrative"] == "narrative_context must be a dict"


def test_f_narrative_rejects_source_outside_allowed_sources():
    proposal = valid_proposal()
    proposal["source"] = "rogue"

    report = fully_known_narrative_report(proposal)

    assert report.checks["F_narrative"] == ValidationResult.REJECT


def test_f_narrative_passes_source_inside_allowed_sources():
    proposal = valid_proposal()
    proposal["source"] = "RO"

    report = fully_known_narrative_report(proposal)

    assert report.checks["F_narrative"] == ValidationResult.PASS


def test_f_narrative_rejects_missing_required_rationale():
    report = fully_known_narrative_report(
        valid_proposal(),
        narrative_context=base_narrative_context(require_rationale=True),
    )

    assert report.checks["F_narrative"] == ValidationResult.REJECT


def test_f_narrative_rejects_empty_required_rationale():
    proposal = valid_proposal()
    proposal["rationale"] = "   "

    report = fully_known_narrative_report(
        proposal,
        narrative_context=base_narrative_context(require_rationale=True),
    )

    assert report.checks["F_narrative"] == ValidationResult.REJECT


def test_f_narrative_passes_non_empty_required_rationale():
    proposal = valid_proposal()
    proposal["rationale"] = "Evidence may still be hidden on site."

    report = fully_known_narrative_report(
        proposal,
        narrative_context=base_narrative_context(require_rationale=True),
    )

    assert report.checks["F_narrative"] == ValidationResult.PASS


def test_f_narrative_rejects_modes_that_are_not_collection():
    proposal = valid_proposal()
    proposal["modes"] = "PURSUE"

    report = fully_known_narrative_report(proposal)

    assert report.checks["F_narrative"] == ValidationResult.REJECT


def test_f_narrative_rejects_when_current_mode_is_not_in_modes():
    proposal = valid_proposal()
    proposal["modes"] = ["FLEE"]

    report = fully_known_narrative_report(proposal)

    assert report.checks["F_narrative"] == ValidationResult.REJECT


def test_f_narrative_passes_when_current_mode_is_in_modes():
    proposal = valid_proposal()
    proposal["modes"] = ["PURSUE"]

    report = fully_known_narrative_report(proposal)

    assert report.checks["F_narrative"] == ValidationResult.PASS


def test_f_narrative_rejects_modes_outside_allowed_modes():
    proposal = valid_proposal()
    proposal["modes"] = ["PURSUE", "TIME_TRAVEL"]

    report = fully_known_narrative_report(proposal)

    assert report.checks["F_narrative"] == ValidationResult.REJECT


def test_f_narrative_rejects_tone_tags_that_are_not_collection():
    proposal = valid_proposal()
    proposal["tone_tags"] = "neo-noir"

    report = fully_known_narrative_report(proposal)

    assert report.checks["F_narrative"] == ValidationResult.REJECT


def test_f_narrative_unknown_when_tone_tags_do_not_overlap_context_tone():
    proposal = valid_proposal()
    proposal["tone_tags"] = ["high_fantasy"]

    report = fully_known_narrative_report(proposal)

    assert report.checks["F_narrative"] == ValidationResult.UNKNOWN


def test_f_narrative_passes_when_tone_tags_overlap_context_tone():
    proposal = valid_proposal()
    proposal["tone_tags"] = ["neo-noir"]

    report = fully_known_narrative_report(proposal)

    assert report.checks["F_narrative"] == ValidationResult.PASS


def test_f_narrative_rejects_tags_that_are_not_collection():
    proposal = valid_proposal()
    proposal["tags"] = "investigation"

    report = fully_known_narrative_report(proposal)

    assert report.checks["F_narrative"] == ValidationResult.REJECT


def test_f_narrative_rejects_forbidden_tags():
    proposal = valid_proposal()
    proposal["tags"] = ["investigation", "world_breaking"]

    report = fully_known_narrative_report(proposal)

    assert report.checks["F_narrative"] == ValidationResult.REJECT


def test_f_narrative_passes_when_tags_do_not_include_forbidden_tags():
    proposal = valid_proposal()
    proposal["tags"] = ["investigation"]

    report = fully_known_narrative_report(proposal)

    assert report.checks["F_narrative"] == ValidationResult.PASS


def test_f_narrative_reject_makes_overall_reject():
    proposal = valid_proposal()
    proposal["source"] = "rogue"

    report = fully_known_narrative_report(proposal)

    assert report.checks["A_syntax"] == ValidationResult.PASS
    assert report.checks["B_uniqueness"] == ValidationResult.PASS
    assert report.checks["C_requirements"] == ValidationResult.PASS
    assert report.checks["D_effects"] == ValidationResult.PASS
    assert report.checks["E_safety"] == ValidationResult.PASS
    assert report.checks["F_narrative"] == ValidationResult.REJECT
    assert report.overall == ValidationResult.REJECT


def test_a_b_c_d_e_f_all_pass_make_overall_pass():
    proposal = valid_proposal()
    proposal.update(
        {
            "requirements": {"location": "room", "flag": True},
            "effects": [{"op": "add", "path": "evidence_score", "value": 3}],
            "source": "RO",
            "rationale": "Evidence may still be hidden on site.",
            "modes": ["PURSUE"],
            "tone_tags": ["neo-noir"],
            "tags": ["investigation"],
        }
    )

    report = fully_known_report(
        proposal,
        safety_limits={"max_abs_delta": 10},
        narrative_context=base_narrative_context(require_rationale=True),
    )

    assert report.checks["A_syntax"] == ValidationResult.PASS
    assert report.checks["B_uniqueness"] == ValidationResult.PASS
    assert report.checks["C_requirements"] == ValidationResult.PASS
    assert report.checks["D_effects"] == ValidationResult.PASS
    assert report.checks["E_safety"] == ValidationResult.PASS
    assert report.checks["F_narrative"] == ValidationResult.PASS
    assert report.overall == ValidationResult.PASS


def test_contract_checks_always_include_all_six_checks():
    report = validate_proposal(valid_proposal())

    assert set(report.checks) == set(CHECK_ORDER)


def test_contract_check_key_order_matches_check_order():
    report = validate_proposal(valid_proposal())

    assert tuple(report.checks) == CHECK_ORDER


def test_contract_overall_reject_when_any_check_rejects():
    proposal = valid_proposal()
    proposal["id"] = "InvalidId"

    report = validate_proposal(proposal)

    assert report.overall == ValidationResult.REJECT


def test_contract_overall_pass_when_all_checks_pass():
    report = fully_known_narrative_report()

    assert set(report.checks.values()) == {ValidationResult.PASS}
    assert report.overall == ValidationResult.PASS


def test_contract_overall_unknown_when_pass_and_unknown_without_reject():
    report = validate_proposal(valid_proposal())

    assert ValidationResult.PASS in report.checks.values()
    assert ValidationResult.UNKNOWN in report.checks.values()
    assert ValidationResult.REJECT not in report.checks.values()
    assert report.overall == ValidationResult.UNKNOWN


def test_contract_reject_reason_has_reason_code():
    report = validate_proposal(valid_proposal(), active_action_ids={"search_hidden_room"})

    assert report.checks["B_uniqueness"] == ValidationResult.REJECT
    assert report.reasons["B_uniqueness"]
    assert report.reason_codes["B_uniqueness"] == "duplicate_action_id"


def test_contract_unknown_reason_has_reason_code():
    report = validate_proposal(valid_proposal(), active_action_ids=None)

    assert report.checks["B_uniqueness"] == ValidationResult.UNKNOWN
    assert report.reasons["B_uniqueness"]
    assert report.reason_codes["B_uniqueness"] == "active_action_ids_not_provided"


def test_contract_pass_checks_do_not_have_reasons_or_reason_codes():
    report = fully_known_narrative_report()

    for check_id, result in report.checks.items():
        if result == ValidationResult.PASS:
            assert check_id not in report.reasons
            assert check_id not in report.reason_codes


def test_contract_to_dict_returns_plain_dict():
    report_dict = validate_proposal(valid_proposal()).to_dict()

    assert type(report_dict) is dict
    assert type(report_dict["checks"]) is dict
    assert type(report_dict["reasons"]) is dict
    assert type(report_dict["reason_codes"]) is dict


def test_contract_to_dict_overall_is_string():
    report_dict = validate_proposal(valid_proposal()).to_dict()

    assert isinstance(report_dict["overall"], str)


def test_contract_to_dict_check_values_are_strings():
    report_dict = validate_proposal(valid_proposal()).to_dict()

    assert all(isinstance(value, str) for value in report_dict["checks"].values())


def test_contract_to_dict_contains_public_report_keys():
    report_dict = validate_proposal(valid_proposal()).to_dict()

    assert {"overall", "checks", "reasons", "reason_codes"} <= set(report_dict)


def test_contract_minimal_validate_proposal_call_still_works():
    report = validate_proposal(valid_proposal())

    assert report.checks["A_syntax"] == ValidationResult.PASS


def test_contract_all_pass_input_has_pass_overall_in_report_and_dict():
    report = fully_known_narrative_report()

    assert report.overall == ValidationResult.PASS
    assert report.to_dict()["overall"] == "PASS"
