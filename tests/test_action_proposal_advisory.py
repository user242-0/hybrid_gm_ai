import sys

from src.action_proposal.advisory import (
    ADVISORY_SCHEMA,
    build_advisory_item,
    build_advisory_items,
    validate_proposal_to_advisory,
)


def pass_proposal():
    return {
        "id": "search_dumpster",
        "label": "Search the dumpster",
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


def pass_shadow_record(**overrides):
    proposal = pass_proposal()
    record = {
        "schema": "action_proposal_shadow.v0.1",
        "stage": "shadow",
        "run_id": "test",
        "source": "shadow_source",
        "proposal_id": "shadow_id",
        "proposal_label": "Shadow label",
        "accepted": True,
        "overall": "PASS",
        "report": {"overall": "PASS", "checks": {"A_syntax": "PASS"}},
        "context_summary": {},
        "proposal": proposal,
    }
    record.update(overrides)
    return record


def test_pass_shadow_record_builds_advisory_item():
    item = build_advisory_item(pass_shadow_record())

    assert item is not None
    assert item["proposal_id"] == "shadow_id"


def test_reject_shadow_record_returns_none():
    item = build_advisory_item(pass_shadow_record(accepted=False, overall="REJECT"))

    assert item is None


def test_unknown_shadow_record_returns_none():
    item = build_advisory_item(pass_shadow_record(accepted=False, overall="UNKNOWN"))

    assert item is None


def test_advisory_item_contains_schema_stage_and_status():
    item = build_advisory_item(pass_shadow_record())

    assert item["schema"] == ADVISORY_SCHEMA
    assert item["schema"] == "action_proposal_advisory.v0.1"
    assert item["stage"] == "advisory"
    assert item["status"] == "suggested"


def test_proposal_id_and_label_copy_from_shadow_record():
    item = build_advisory_item(pass_shadow_record(proposal_id="from_shadow", proposal_label="From shadow"))

    assert item["proposal_id"] == "from_shadow"
    assert item["proposal_label"] == "From shadow"


def test_proposal_id_and_label_fall_back_to_proposal():
    item = build_advisory_item(pass_shadow_record(proposal_id=None, proposal_label=None))

    assert item["proposal_id"] == "search_dumpster"
    assert item["proposal_label"] == "Search the dumpster"


def test_source_prefers_shadow_record():
    item = build_advisory_item(pass_shadow_record(source="shadow_source"))

    assert item["source"] == "shadow_source"


def test_source_falls_back_to_proposal_source():
    item = build_advisory_item(pass_shadow_record(source=None))

    assert item["source"] == "RO"


def test_rationale_comes_from_proposal():
    item = build_advisory_item(pass_shadow_record())

    assert item["rationale"] == "Evidence may have been discarded nearby."


def test_display_uses_label_source_and_rationale():
    item = build_advisory_item(pass_shadow_record())

    assert item["display"]["title"] == "Shadow label"
    assert "shadow_source" in item["display"]["subtitle"]
    assert "Evidence may have been discarded nearby." in item["display"]["detail"]


def test_proposal_and_report_are_included():
    record = pass_shadow_record()
    item = build_advisory_item(record)

    assert item["proposal"] == record["proposal"]
    assert item["report"] == record["report"]


def test_missing_proposal_defaults_to_empty_dict():
    item = build_advisory_item(pass_shadow_record(proposal=None))

    assert item["proposal"] == {}


def test_build_advisory_items_filters_none_and_keeps_pass_records():
    records = [
        pass_shadow_record(proposal_id="one"),
        pass_shadow_record(proposal_id="reject", accepted=False, overall="REJECT"),
        pass_shadow_record(proposal_id="unknown", accepted=False, overall="UNKNOWN"),
        pass_shadow_record(proposal_id="two"),
    ]

    items = build_advisory_items(records)

    assert [item["proposal_id"] for item in items] == ["one", "two"]


def test_validate_proposal_to_advisory_returns_item_for_pass_proposal():
    item = validate_proposal_to_advisory(pass_proposal(), context=pass_context())

    assert item is not None
    assert item["schema"] == ADVISORY_SCHEMA
    assert item["proposal_id"] == "search_dumpster"


def test_validate_proposal_to_advisory_returns_none_for_reject_proposal():
    item = validate_proposal_to_advisory(
        pass_proposal(),
        context=pass_context(active_action_ids={"search_dumpster"}),
    )

    assert item is None


def test_validate_proposal_to_advisory_returns_none_for_unknown_proposal():
    item = validate_proposal_to_advisory(
        pass_proposal(),
        context=pass_context(narrative_context=None),
    )

    assert item is None


def test_validate_proposal_to_advisory_passes_source_to_shadow_record():
    item = validate_proposal_to_advisory(pass_proposal(), context=pass_context(), source="human")

    assert item["source"] == "human"
    assert item["display"]["subtitle"] == "human proposal"


def test_advisory_adapter_does_not_import_runtime_systems():
    forbidden_modules = [
        "src.action_registry",
        "src.ui.action_pipeline",
        "src.ui.hud_callbacks",
        "src.director.director",
    ]
    for module in forbidden_modules:
        sys.modules.pop(module, None)

    validate_proposal_to_advisory(pass_proposal(), context=pass_context())

    for module in forbidden_modules:
        assert module not in sys.modules
