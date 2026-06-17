import json
import sys

from src.action_proposal.advisory_provider import (
    ADVISORY_PROVIDER_SCHEMA,
    get_advisory_display_items,
    get_advisory_feed,
    get_default_advisory_feed_path,
    has_advisory_items,
)


def proposal(**overrides):
    value = {
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
    value.update(overrides)
    return value


def shadow_record(**overrides):
    record = {
        "schema": "action_proposal_shadow.v0.1",
        "stage": "shadow",
        "run_id": "test",
        "source": "RO",
        "proposal_id": "search_dumpster",
        "proposal_label": "Search the dumpster",
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


def write_jsonl(path, records):
    path.write_text(
        "\n".join(json.dumps(record, ensure_ascii=False) for record in records),
        encoding="utf-8",
    )


def test_get_default_advisory_feed_path_points_to_shadow_jsonl():
    assert get_default_advisory_feed_path().name == "action_proposal_shadow.jsonl"


def test_missing_path_returns_empty_feed_count_and_items(tmp_path):
    path = tmp_path / "missing.jsonl"

    feed = get_advisory_feed(path=path)

    assert feed["count"] == 0
    assert feed["items"] == []


def test_provider_info_contains_schema_read_only_source_and_path(tmp_path):
    path = tmp_path / "missing.jsonl"

    provider = get_advisory_feed(path=path)["provider"]

    assert provider["schema"] == ADVISORY_PROVIDER_SCHEMA
    assert provider["schema"] == "action_proposal_advisory_provider.v0.1"
    assert provider["read_only"] is True
    assert provider["source"] == "shadow_log"
    assert provider["path"] == str(path)


def test_jsonl_with_pass_shadow_record_returns_items(tmp_path):
    path = tmp_path / "shadow.jsonl"
    write_jsonl(path, [shadow_record(proposal_id="pass")])

    feed = get_advisory_feed(path=path)

    assert feed["count"] == 1
    assert feed["items"][0]["proposal_id"] == "pass"


def test_unknown_and_reject_shadow_records_are_not_in_items(tmp_path):
    path = tmp_path / "shadow.jsonl"
    write_jsonl(
        path,
        [
            shadow_record(proposal_id="pass"),
            shadow_record(proposal_id="unknown", accepted=False, overall="UNKNOWN"),
            shadow_record(proposal_id="reject", accepted=False, overall="REJECT"),
        ],
    )

    feed = get_advisory_feed(path=path, limit=None)

    assert feed["count"] == 1
    assert [item["proposal_id"] for item in feed["items"]] == ["pass"]


def test_limit_is_applied(tmp_path):
    path = tmp_path / "shadow.jsonl"
    write_jsonl(
        path,
        [
            shadow_record(proposal_id="one"),
            shadow_record(proposal_id="two"),
        ],
    )

    feed = get_advisory_feed(path=path, limit=1)

    assert feed["count"] == 1
    assert [item["proposal_id"] for item in feed["items"]] == ["one"]


def test_limit_none_returns_all_items(tmp_path):
    path = tmp_path / "shadow.jsonl"
    write_jsonl(
        path,
        [
            shadow_record(proposal_id="one"),
            shadow_record(proposal_id="two"),
        ],
    )

    feed = get_advisory_feed(path=path, limit=None)

    assert feed["count"] == 2
    assert [item["proposal_id"] for item in feed["items"]] == ["one", "two"]


def test_actor_id_filter_returns_only_matching_actor_items(tmp_path):
    path = tmp_path / "shadow.jsonl"
    write_jsonl(
        path,
        [
            shadow_record(proposal_id="hero_one", actor_id="Hero"),
            shadow_record(proposal_id="villain_one", actor_id="Villain"),
            shadow_record(proposal_id="hero_two", actor_id="Hero"),
        ],
    )

    items = get_advisory_display_items(path=path, actor_id="Hero", limit=None)

    assert [item["proposal_id"] for item in items] == ["hero_one", "hero_two"]
    assert {item["actor_id"] for item in items} == {"Hero"}


def test_run_id_is_reflected_in_feed(tmp_path):
    feed = get_advisory_feed(path=tmp_path / "missing.jsonl", run_id="provider-test")

    assert feed["run_id"] == "provider-test"


def test_get_advisory_display_items_returns_items_list(tmp_path):
    path = tmp_path / "shadow.jsonl"
    write_jsonl(path, [shadow_record(proposal_id="pass")])

    items = get_advisory_display_items(path=path)

    assert isinstance(items, list)
    assert items[0]["proposal_id"] == "pass"


def test_has_advisory_items_true_when_items_exist(tmp_path):
    path = tmp_path / "shadow.jsonl"
    write_jsonl(path, [shadow_record(proposal_id="pass")])

    assert has_advisory_items(path=path) is True


def test_has_advisory_items_false_when_items_do_not_exist(tmp_path):
    assert has_advisory_items(path=tmp_path / "missing.jsonl") is False


def test_japanese_title_and_detail_are_preserved(tmp_path):
    path = tmp_path / "shadow.jsonl"
    write_jsonl(
        path,
        [
            shadow_record(
                proposal_id="jp",
                proposal_label="路地裏を調べる",
                proposal=proposal(
                    id="jp",
                    label="路地裏を調べる",
                    rationale="現場に未回収の証拠がある可能性",
                ),
            )
        ],
    )

    item = get_advisory_feed(path=path)["items"][0]

    assert item["title"] == "路地裏を調べる"
    assert item["detail"] == "現場に未回収の証拠がある可能性"


def test_provider_does_not_rewrite_log_file(tmp_path):
    path = tmp_path / "shadow.jsonl"
    write_jsonl(path, [shadow_record(proposal_id="pass")])
    before = path.read_bytes()

    get_advisory_feed(path=path)

    assert path.read_bytes() == before


def test_advisory_provider_does_not_import_runtime_systems(tmp_path):
    forbidden_modules = [
        "src.action_registry",
        "src.ui.action_pipeline",
        "src.ui.hud_callbacks",
        "src.director.director",
    ]
    for module in forbidden_modules:
        sys.modules.pop(module, None)

    get_advisory_feed(path=tmp_path / "missing.jsonl")

    for module in forbidden_modules:
        assert module not in sys.modules
