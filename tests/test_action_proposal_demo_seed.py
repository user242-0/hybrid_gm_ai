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
