import json
import sys

import src.action_proposal.shadow as shadow
from src.action_proposal.shadow import (
    SHADOW_LOG_FILENAME,
    append_shadow_log,
    build_shadow_record,
    default_shadow_log_path,
    validate_and_build_shadow_record,
    validate_proposal_shadow,
)


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


def test_default_shadow_log_path_uses_standard_filename():
    assert default_shadow_log_path().name == SHADOW_LOG_FILENAME
    assert default_shadow_log_path().name == "action_proposal_shadow.jsonl"


def test_build_shadow_record_contains_schema_and_stage():
    proposal = pass_proposal()
    result = validate_proposal_shadow(proposal, context=pass_context())

    record = build_shadow_record(proposal, result)

    assert record["schema"] == "action_proposal_shadow.v0.1"
    assert record["stage"] == "shadow"


def test_build_shadow_record_contains_proposal_id_and_label():
    proposal = pass_proposal()
    result = validate_proposal_shadow(proposal, context=pass_context())

    record = build_shadow_record(proposal, result)

    assert record["proposal_id"] == proposal["id"]
    assert record["proposal_label"] == proposal["label"]


def test_build_shadow_record_contains_actor_id_when_proposal_has_actor_id():
    proposal = pass_proposal()
    proposal["actor_id"] = "Hero"
    result = validate_proposal_shadow(proposal, context=pass_context())

    record = build_shadow_record(proposal, result)

    assert record["actor_id"] == "Hero"


def test_build_shadow_record_copies_result_fields():
    proposal = pass_proposal()
    result = {
        "accepted": True,
        "overall": "PASS",
        "report": {"overall": "PASS", "checks": {"syntax": "PASS"}},
    }

    record = build_shadow_record(proposal, result)

    assert record["accepted"] is True
    assert record["overall"] == "PASS"
    assert record["report"] == result["report"]


def test_build_shadow_record_source_argument_overrides_proposal_source():
    proposal = pass_proposal()
    result = validate_proposal_shadow(proposal, context=pass_context())

    record = build_shadow_record(proposal, result, source="human")

    assert record["source"] == "human"


def test_build_shadow_record_uses_proposal_source_without_source_argument():
    proposal = pass_proposal()
    result = validate_proposal_shadow(proposal, context=pass_context())

    record = build_shadow_record(proposal, result)

    assert record["source"] == proposal["source"]


def test_build_shadow_record_defaults_context_summary_to_empty_dict():
    proposal = pass_proposal()
    result = validate_proposal_shadow(proposal, context=pass_context())

    record = build_shadow_record(proposal, result)

    assert record["context_summary"] == {}


def test_build_shadow_record_includes_original_proposal():
    proposal = pass_proposal()
    result = validate_proposal_shadow(proposal, context=pass_context())

    record = build_shadow_record(proposal, result)

    assert record["proposal"] == proposal


def test_validate_and_build_shadow_record_accepts_pass_proposal():
    record = validate_and_build_shadow_record(pass_proposal(), context=pass_context())

    assert record["accepted"] is True
    assert record["overall"] == "PASS"


def test_validate_and_build_shadow_record_rejects_duplicate_proposal():
    record = validate_and_build_shadow_record(
        pass_proposal(),
        context=pass_context(active_action_ids={"search_dumpster"}),
    )

    assert record["accepted"] is False
    assert record["overall"] == "REJECT"


def test_append_shadow_log_default_path_writes_jsonl_record(tmp_path, monkeypatch):
    monkeypatch.setattr(shadow, "default_shadow_log_path", lambda: tmp_path / SHADOW_LOG_FILENAME)
    proposal = pass_proposal()
    result = validate_proposal_shadow(proposal, context=pass_context())
    record = build_shadow_record(proposal, result)
    default_path = shadow.default_shadow_log_path()

    append_shadow_log(default_path, record)

    lines = default_path.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 1
    saved = json.loads(lines[0])
    assert saved["schema"] == "action_proposal_shadow.v0.1"
    assert saved["stage"] == "shadow"
    assert saved["proposal_id"] == "search_dumpster"
    assert saved["overall"] == "PASS"


def test_append_shadow_log_default_path_preserves_japanese_record_label(tmp_path, monkeypatch):
    monkeypatch.setattr(shadow, "default_shadow_log_path", lambda: tmp_path / SHADOW_LOG_FILENAME)
    proposal = pass_proposal()
    proposal["label"] = "ゴミ箱を漁る"
    result = validate_proposal_shadow(proposal, context=pass_context())
    record = build_shadow_record(proposal, result)
    default_path = shadow.default_shadow_log_path()

    append_shadow_log(default_path, record)

    text = default_path.read_text(encoding="utf-8")
    assert "ゴミ箱を漁る" in text
    assert "\\u30b4" not in text
