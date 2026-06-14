import json
import sys

from src.action_proposal.shadow import append_shadow_log, validate_proposal_shadow


def pass_proposal():
    return {
        "id": "search_dumpster",
        "label": "ゴミ箱を漁る",
        "time_min": 5,
        "requirements": {"location": "alley"},
        "effects": [{"op": "add", "path": "evidence_score", "value": 2}],
        "source": "RO",
        "rationale": "Evidence may have been discarded nearby.",
        "modes": ["PURSUE"],
        "tone_tags": ["neo-noir"],
        "tags": ["investigation"],
    }


def pass_context(**overrides):
    context = {
        "active_action_ids": {"question_witness"},
        "known_requirement_keys": {"location"},
        "known_effect_paths": {"evidence_score"},
        "safety_limits": {"max_abs_delta": 10},
        "narrative_context": {
            "current_mode": "PURSUE",
            "allowed_modes": {"PURSUE", "FLEE", "FREEZE", "WITNESS"},
            "tone": {"neo-noir", "slow_burn"},
            "forbidden_tags": {"world_breaking", "comedy_gag"},
            "allowed_sources": {"RO", "LLM", "pack", "human"},
            "require_rationale": True,
        },
    }
    context.update(overrides)
    return context


def test_all_checks_pass_accepts_shadow_proposal():
    result = validate_proposal_shadow(pass_proposal(), context=pass_context())

    assert result["accepted"] is True
    assert set(result["report"]["checks"].values()) == {"PASS"}


def test_pass_overall_is_pass():
    result = validate_proposal_shadow(pass_proposal(), context=pass_context())

    assert result["overall"] == "PASS"


def test_reject_sets_accepted_false_for_duplicate_id():
    result = validate_proposal_shadow(
        pass_proposal(),
        context=pass_context(active_action_ids={"search_dumpster"}),
    )

    assert result["overall"] == "REJECT"
    assert result["accepted"] is False


def test_unknown_sets_accepted_false_when_narrative_context_missing():
    result = validate_proposal_shadow(
        pass_proposal(),
        context=pass_context(narrative_context=None),
    )

    assert result["overall"] == "UNKNOWN"
    assert result["accepted"] is False


def test_result_contains_shadow_stage():
    result = validate_proposal_shadow(pass_proposal(), context=pass_context())

    assert result["stage"] == "shadow"


def test_result_contains_proposal_id_and_label():
    result = validate_proposal_shadow(pass_proposal(), context=pass_context())

    assert result["proposal_id"] == "search_dumpster"
    assert result["proposal_label"] == "ゴミ箱を漁る"


def test_result_contains_report():
    result = validate_proposal_shadow(pass_proposal(), context=pass_context())

    assert "report" in result
    assert {"overall", "checks", "reasons", "reason_codes"} <= set(result["report"])


def test_report_check_values_are_strings():
    result = validate_proposal_shadow(pass_proposal(), context=pass_context())

    assert all(isinstance(value, str) for value in result["report"]["checks"].values())


def test_append_shadow_log_writes_one_jsonl_record(tmp_path):
    path = tmp_path / "shadow" / "records.jsonl"
    record = validate_proposal_shadow(pass_proposal(), context=pass_context())

    append_shadow_log(path, record)

    lines = path.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 1
    assert json.loads(lines[0])["proposal_id"] == "search_dumpster"


def test_append_shadow_log_preserves_japanese_label(tmp_path):
    path = tmp_path / "records.jsonl"
    record = validate_proposal_shadow(pass_proposal(), context=pass_context())

    append_shadow_log(path, record)

    text = path.read_text(encoding="utf-8")
    assert "ゴミ箱を漁る" in text
    assert "\\u30b4" not in text


def test_shadow_adapter_does_not_import_runtime_registration_systems():
    sys.modules.pop("src.action_registry", None)
    sys.modules.pop("src.ui.action_pipeline", None)

    validate_proposal_shadow(pass_proposal(), context=pass_context())

    assert "src.action_registry" not in sys.modules
    assert "src.ui.action_pipeline" not in sys.modules
