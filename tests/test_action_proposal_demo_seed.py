import json
import sys

from src.action_proposal.advisory_provider import get_advisory_display_items
from src.action_proposal.demo_seed import (
    build_demo_proposals,
    build_demo_shadow_records,
    seed_demo_shadow_log,
)


def test_demo_seed_builds_actor_targeted_proposals():
    proposals = build_demo_proposals()

    assert {proposal["actor_id"] for proposal in proposals} == {"刑事", "愉快犯"}
    assert {proposal["id"] for proposal in proposals} == {
        "compare_witness_timestamps",
        "plant_false_trace",
    }
    assert "fix_cam_clock" not in {proposal["id"] for proposal in proposals}


def test_demo_proposals_pass_all_a_to_f_checks():
    records = build_demo_shadow_records(run_id="test-demo")

    assert len(records) == 2
    assert all(record["accepted"] is True for record in records)
    assert all(record["overall"] == "PASS" for record in records)
    assert all(
        set(record["report"]["checks"]) == {
            "A_syntax",
            "B_uniqueness",
            "C_requirements",
            "D_effects",
            "E_safety",
            "F_narrative",
        }
        for record in records
    )
    assert all(set(record["report"]["checks"].values()) == {"PASS"} for record in records)


def test_seed_writes_multiple_actor_records_to_shadow_log(tmp_path):
    path = tmp_path / "action_proposal_shadow.jsonl"

    saved_path, records = seed_demo_shadow_log(path, run_id="test-demo")

    saved = [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    assert saved_path == path
    assert len(records) == 2
    assert {record["actor_id"] for record in saved} == {"刑事", "愉快犯"}
    assert all(record["overall"] == "PASS" for record in saved)


def test_seed_is_idempotent_for_actor_and_proposal_id(tmp_path):
    path = tmp_path / "action_proposal_shadow.jsonl"

    _, first_records = seed_demo_shadow_log(path, run_id="first-demo")
    _, second_records = seed_demo_shadow_log(path, run_id="second-demo")

    saved = [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    assert len(first_records) == 2
    assert second_records == []
    assert [
        (record["actor_id"], record["proposal_id"])
        for record in saved
    ] == [
        ("刑事", "compare_witness_timestamps"),
        ("愉快犯", "plant_false_trace"),
    ]


def test_seed_normalizes_existing_duplicates_and_preserves_other_records(tmp_path):
    path = tmp_path / "action_proposal_shadow.jsonl"
    detective, trickster = build_demo_shadow_records(run_id="existing-demo")
    other_record = {
        "schema": "action_proposal_shadow.v0.1",
        "stage": "shadow",
        "run_id": "other",
        "actor_id": "刑事",
        "proposal_id": "inspect_alibi",
        "accepted": True,
        "overall": "PASS",
    }
    existing_records = [
        detective,
        other_record,
        detective,
        trickster,
        trickster,
    ]
    path.write_text(
        "".join(
            f"{json.dumps(record, ensure_ascii=False)}\n"
            for record in existing_records
        ),
        encoding="utf-8",
    )

    _, appended_records = seed_demo_shadow_log(path, run_id="normalize-demo")

    saved = [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    assert appended_records == []
    assert sum(
        record.get("actor_id") == "刑事"
        and record.get("proposal_id") == "compare_witness_timestamps"
        and record.get("accepted") is True
        and record.get("overall") == "PASS"
        for record in saved
    ) == 1
    assert sum(
        record.get("actor_id") == "愉快犯"
        and record.get("proposal_id") == "plant_false_trace"
        and record.get("accepted") is True
        and record.get("overall") == "PASS"
        for record in saved
    ) == 1
    assert other_record in saved
    assert len(saved) == 3


def test_provider_filters_seeded_items_by_actor_id(tmp_path):
    path = tmp_path / "action_proposal_shadow.jsonl"
    seed_demo_shadow_log(path, run_id="test-demo")

    detective_items = get_advisory_display_items(
        path=path,
        actor_id="刑事",
        limit=None,
    )
    trickster_items = get_advisory_display_items(
        path=path,
        actor_id="愉快犯",
        limit=None,
    )

    assert [item["proposal_id"] for item in detective_items] == [
        "compare_witness_timestamps"
    ]
    assert [item["title"] for item in detective_items] == ["証言時刻を照合する"]
    assert [item["proposal_id"] for item in trickster_items] == ["plant_false_trace"]
    assert [item["title"] for item in trickster_items] == ["偽の痕跡を残す"]


def test_demo_seed_does_not_import_runtime_action_systems(tmp_path):
    forbidden_modules = ["src.action_registry", "src.ui.action_pipeline"]
    for module in forbidden_modules:
        sys.modules.pop(module, None)

    seed_demo_shadow_log(tmp_path / "shadow.jsonl")

    for module in forbidden_modules:
        assert module not in sys.modules
