import json
import sys

from src.action_proposal.advisory_feed import (
    ADVISORY_DISPLAY_ITEM_SCHEMA,
    ADVISORY_FEED_SCHEMA,
    build_advisory_feed,
    build_advisory_feed_from_shadow_log,
    build_advisory_feed_from_shadow_records,
    build_display_item,
    load_jsonl_records,
)


def proposal(**overrides):
    value = {
        "id": "search_dumpster",
        "label": "ゴミ箱を漁る",
        "time_min": 5,
        "requirements": {"location": "alley"},
        "effects": [{"op": "add", "path": "evidence_score", "value": 2}],
        "source": "RO",
        "rationale": "現場に未回収の証拠がある可能性",
        "modes": ["PURSUE"],
        "tone_tags": ["neo-noir"],
        "tags": ["investigation"],
    }
    value.update(overrides)
    return value


def advisory_item(**overrides):
    item = {
        "schema": "action_proposal_advisory.v0.1",
        "stage": "advisory",
        "status": "suggested",
        "proposal_id": "search_dumpster",
        "proposal_label": "ゴミ箱を漁る",
        "source": "RO",
        "rationale": "現場に未回収の証拠がある可能性",
        "display": {
            "title": "表示タイトル",
            "subtitle": "表示サブタイトル",
            "detail": "表示詳細",
        },
        "proposal": proposal(),
        "report": {
            "overall": "PASS",
            "checks": {"A_syntax": "PASS"},
            "reasons": {},
            "reason_codes": {"A_syntax": "pass"},
        },
        "shadow_schema": "action_proposal_shadow.v0.1",
    }
    item.update(overrides)
    return item


def shadow_record(**overrides):
    record = {
        "schema": "action_proposal_shadow.v0.1",
        "stage": "shadow",
        "run_id": "test",
        "source": "RO",
        "proposal_id": "search_dumpster",
        "proposal_label": "ゴミ箱を漁る",
        "accepted": True,
        "overall": "PASS",
        "report": {
            "overall": "PASS",
            "checks": {"A_syntax": "PASS"},
            "reasons": {},
            "reason_codes": {},
        },
        "context_summary": {},
        "proposal": proposal(),
    }
    record.update(overrides)
    return record


def test_build_display_item_builds_from_valid_advisory_item():
    item = build_display_item(advisory_item())

    assert item is not None
    assert item["proposal_id"] == "search_dumpster"
    assert item["status"] == "suggested"


def test_build_display_item_copies_actor_id():
    item = build_display_item(advisory_item(actor_id="Hero"))

    assert item["actor_id"] == "Hero"


def test_build_display_item_returns_none_for_non_advisory_stage():
    assert build_display_item(advisory_item(stage="shadow")) is None


def test_build_display_item_returns_none_for_non_suggested_status():
    assert build_display_item(advisory_item(status="hidden")) is None


def test_display_item_contains_display_schema():
    item = build_display_item(advisory_item())

    assert item["schema"] == ADVISORY_DISPLAY_ITEM_SCHEMA
    assert item["schema"] == "action_proposal_advisory_display_item.v0.1"


def test_display_item_contains_title_subtitle_and_detail():
    item = build_display_item(advisory_item())

    assert item["title"]
    assert item["subtitle"]
    assert item["detail"]


def test_title_prefers_display_title():
    item = build_display_item(advisory_item(display={"title": "優先タイトル"}))

    assert item["title"] == "優先タイトル"


def test_title_uses_proposal_label_when_display_title_missing():
    item = build_display_item(advisory_item(display={}))

    assert item["title"] == "ゴミ箱を漁る"


def test_title_uses_proposal_id_when_label_missing():
    item = build_display_item(advisory_item(display={}, proposal_label=None))

    assert item["title"] == "search_dumpster"


def test_subtitle_falls_back_to_source():
    item = build_display_item(advisory_item(display={}))

    assert item["subtitle"] == "RO proposal"


def test_detail_falls_back_to_rationale():
    item = build_display_item(advisory_item(display={}))

    assert item["detail"] == "現場に未回収の証拠がある可能性"


def test_report_overall_and_reason_codes_copy_from_report():
    item = build_display_item(advisory_item())

    assert item["report_overall"] == "PASS"
    assert item["reason_codes"] == {"A_syntax": "pass"}


def test_build_advisory_feed_contains_feed_schema():
    feed = build_advisory_feed([advisory_item()])

    assert feed["schema"] == ADVISORY_FEED_SCHEMA
    assert feed["schema"] == "action_proposal_advisory_feed.v0.1"


def test_build_advisory_feed_returns_count_and_items():
    feed = build_advisory_feed([advisory_item(proposal_id="one"), advisory_item(proposal_id="two")])

    assert feed["count"] == 2
    assert [item["proposal_id"] for item in feed["items"]] == ["one", "two"]


def test_build_advisory_feed_filters_none_display_items():
    feed = build_advisory_feed(
        [
            advisory_item(proposal_id="one"),
            advisory_item(proposal_id="skip", status="hidden"),
            advisory_item(proposal_id="two"),
        ]
    )

    assert feed["count"] == 2
    assert [item["proposal_id"] for item in feed["items"]] == ["one", "two"]


def test_build_advisory_feed_applies_limit():
    feed = build_advisory_feed(
        [advisory_item(proposal_id="one"), advisory_item(proposal_id="two")],
        limit=1,
    )

    assert feed["count"] == 1
    assert [item["proposal_id"] for item in feed["items"]] == ["one"]


def test_build_advisory_feed_limit_none_returns_all_items():
    feed = build_advisory_feed(
        [advisory_item(proposal_id="one"), advisory_item(proposal_id="two")],
        limit=None,
    )

    assert feed["count"] == 2
    assert [item["proposal_id"] for item in feed["items"]] == ["one", "two"]


def test_build_advisory_feed_from_shadow_records_includes_pass_records_only():
    feed = build_advisory_feed_from_shadow_records(
        [
            shadow_record(proposal_id="pass_one"),
            shadow_record(proposal_id="pass_two"),
        ],
        limit=None,
    )

    assert feed["count"] == 2
    assert [item["proposal_id"] for item in feed["items"]] == ["pass_one", "pass_two"]


def test_unknown_and_reject_shadow_records_are_not_in_feed():
    feed = build_advisory_feed_from_shadow_records(
        [
            shadow_record(proposal_id="pass"),
            shadow_record(proposal_id="unknown", accepted=False, overall="UNKNOWN"),
            shadow_record(proposal_id="reject", accepted=False, overall="REJECT"),
        ],
        limit=None,
    )

    assert feed["count"] == 1
    assert [item["proposal_id"] for item in feed["items"]] == ["pass"]


def test_load_jsonl_records_returns_empty_list_for_missing_file(tmp_path):
    assert load_jsonl_records(tmp_path / "missing.jsonl") == []


def test_load_jsonl_records_ignores_blank_lines(tmp_path):
    path = tmp_path / "records.jsonl"
    path.write_text('\n{"proposal_id": "one"}\n\n{"proposal_id": "two"}\n', encoding="utf-8")

    records = load_jsonl_records(path)

    assert [record["proposal_id"] for record in records] == ["one", "two"]


def test_build_advisory_feed_from_shadow_log_builds_feed_from_jsonl(tmp_path):
    path = tmp_path / "shadow.jsonl"
    records = [
        shadow_record(proposal_id="pass"),
        shadow_record(proposal_id="reject", accepted=False, overall="REJECT"),
    ]
    path.write_text(
        "\n".join(json.dumps(record, ensure_ascii=False) for record in records),
        encoding="utf-8",
    )

    feed = build_advisory_feed_from_shadow_log(path, limit=None, run_id="jsonl-test")

    assert feed["run_id"] == "jsonl-test"
    assert feed["count"] == 1
    assert feed["items"][0]["proposal_id"] == "pass"


def test_japanese_title_and_detail_are_preserved():
    item = build_display_item(
        advisory_item(
            display={
                "title": "ゴミ箱を漁る",
                "detail": "現場に未回収の証拠がある可能性",
            }
        )
    )

    assert item["title"] == "ゴミ箱を漁る"
    assert item["detail"] == "現場に未回収の証拠がある可能性"


def test_advisory_feed_adapter_does_not_import_runtime_systems():
    forbidden_modules = [
        "src.action_registry",
        "src.ui.action_pipeline",
        "src.ui.hud_callbacks",
        "src.director.director",
    ]
    for module in forbidden_modules:
        sys.modules.pop(module, None)

    build_advisory_feed_from_shadow_records([shadow_record()])

    for module in forbidden_modules:
        assert module not in sys.modules
