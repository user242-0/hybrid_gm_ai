"""Generate actor-targeted demo proposals for the read-only advisory HUD."""

from __future__ import annotations

import argparse
import json
from copy import deepcopy
from pathlib import Path
from typing import Any

from src.action_proposal.shadow import (
    append_shadow_log,
    default_shadow_log_path,
    validate_and_build_shadow_record,
)

DEMO_RUN_ID = "actor_advisory_demo"

_DEMO_SEEDS = (
    {
        "proposal": {
            "actor_id": "刑事",
            "id": "compare_witness_timestamps",
            "label": "証言時刻を照合する",
            "time_min": 8,
            "requirements": {"location": "警察署_控室"},
            "effects": [{"op": "add", "path": "witness_value", "value": 1}],
            "source": "pack",
            "rationale": "現場証言の時刻を照合すれば、愉快犯の移動経路の矛盾を見つけられる。",
            "modes": ["PURSUE", "WITNESS"],
            "tone_tags": ["neo-noir"],
            "tags": ["investigation"],
        },
        "context": {
            "active_action_ids": {"fix_cam_clock"},
            "known_requirement_keys": {"location"},
            "known_effect_paths": {"witness_value"},
            "safety_limits": {"max_abs_delta": 3},
            "narrative_context": {
                "current_mode": "PURSUE",
                "allowed_modes": {"PURSUE", "FLEE", "FREEZE", "WITNESS"},
                "tone": {"neo-noir"},
                "forbidden_tags": {"world_breaking"},
                "allowed_sources": {"pack"},
                "require_rationale": True,
            },
        },
        "context_summary": {
            "actor_id": "刑事",
            "mode": "PURSUE",
            "location": "警察署_控室",
        },
    },
    {
        "proposal": {
            "actor_id": "愉快犯",
            "id": "plant_false_trace",
            "label": "偽の痕跡を残す",
            "time_min": 10,
            "requirements": {"location": "事件現場_路地裏"},
            "effects": [{"op": "add", "path": "suspicion.value", "value": -1}],
            "source": "pack",
            "rationale": "捜査の焦点をずらすため、現場に矛盾する痕跡を残す。",
            "modes": ["FLEE"],
            "tone_tags": ["neo-noir"],
            "tags": ["deception"],
        },
        "context": {
            "active_action_ids": {"fix_cam_clock"},
            "known_requirement_keys": {"location"},
            "known_effect_paths": {"suspicion.value"},
            "safety_limits": {"max_abs_delta": 3},
            "narrative_context": {
                "current_mode": "FLEE",
                "allowed_modes": {"PURSUE", "FLEE", "FREEZE", "WITNESS"},
                "tone": {"neo-noir"},
                "forbidden_tags": {"world_breaking"},
                "allowed_sources": {"pack"},
                "require_rationale": True,
            },
        },
        "context_summary": {
            "actor_id": "愉快犯",
            "mode": "FLEE",
            "location": "事件現場_路地裏",
        },
    },
)


def build_demo_proposals() -> list[dict[str, Any]]:
    """Return fresh actor-targeted proposal dictionaries."""
    return [deepcopy(seed["proposal"]) for seed in _DEMO_SEEDS]


def build_demo_shadow_records(*, run_id: str = DEMO_RUN_ID) -> list[dict[str, Any]]:
    """Validate the demo proposals through A-F and return PASS shadow records."""
    records = [
        validate_and_build_shadow_record(
            deepcopy(seed["proposal"]),
            context=deepcopy(seed["context"]),
            context_summary=deepcopy(seed["context_summary"]),
            run_id=run_id,
        )
        for seed in _DEMO_SEEDS
    ]

    failed = [
        f"{record.get('proposal_id')}={record.get('overall')}"
        for record in records
        if record.get("accepted") is not True or record.get("overall") != "PASS"
    ]
    if failed:
        raise ValueError(f"demo proposal validation failed: {', '.join(failed)}")
    return records


def _normalize_existing_seed_pass_records(
    path: Path,
    seed_keys: set[tuple[Any, Any]],
) -> set[tuple[Any, Any]]:
    if not path.exists():
        return set()

    existing_keys = set()
    retained_lines = []
    removed_duplicate = False
    for line in path.read_bytes().splitlines(keepends=True):
        stripped = line.strip()
        if not stripped:
            retained_lines.append(line)
            continue

        record = json.loads(stripped)
        key = None
        if (
            isinstance(record, dict)
            and record.get("accepted") is True
            and record.get("overall") == "PASS"
        ):
            candidate_key = (record.get("actor_id"), record.get("proposal_id"))
            if candidate_key in seed_keys:
                key = candidate_key

        if key is not None and key in existing_keys:
            removed_duplicate = True
            continue

        retained_lines.append(line)
        if key is not None:
            existing_keys.add(key)

    if removed_duplicate:
        path.write_bytes(b"".join(retained_lines))
    return existing_keys


def seed_demo_shadow_log(
    path: str | Path | None = None,
    *,
    run_id: str = DEMO_RUN_ID,
) -> tuple[Path, list[dict[str, Any]]]:
    """Append only demo PASS records not already present for the same actor."""
    log_path = Path(path) if path is not None else default_shadow_log_path()
    records = build_demo_shadow_records(run_id=run_id)
    seed_keys = {
        (record.get("actor_id"), record.get("proposal_id"))
        for record in records
    }
    existing_keys = _normalize_existing_seed_pass_records(log_path, seed_keys)
    appended_records = []
    for record in records:
        key = (record.get("actor_id"), record.get("proposal_id"))
        if key in existing_keys:
            continue
        append_shadow_log(log_path, record)
        existing_keys.add(key)
        appended_records.append(record)
    return log_path, appended_records


def _main() -> None:
    parser = argparse.ArgumentParser(
        description="Seed actor-targeted PASS proposals for the read-only advisory HUD.",
    )
    parser.add_argument(
        "--path",
        type=Path,
        help="Shadow JSONL path. Defaults to the configured standard shadow log.",
    )
    parser.add_argument("--run-id", default=DEMO_RUN_ID)
    args = parser.parse_args()

    path, records = seed_demo_shadow_log(args.path, run_id=args.run_id)
    print(
        json.dumps(
            {
                "path": str(path),
                "count": len(records),
                "records": [
                    {
                        "proposal_id": record["proposal_id"],
                        "actor_id": record["actor_id"],
                        "overall": record["overall"],
                    }
                    for record in records
                ],
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    _main()
