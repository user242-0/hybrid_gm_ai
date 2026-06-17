"""Shadow adapter for Action Proposal DSL v0.1 validation."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from src.action_proposal.validator import validate_proposal

SHADOW_LOG_FILENAME = "action_proposal_shadow.jsonl"
SHADOW_RECORD_SCHEMA = "action_proposal_shadow.v0.1"


def default_shadow_log_path() -> Path:
    """Return the standard JSONL path for Action Proposal shadow records."""
    from src.utility.config_loader import job_root_from_cfg

    return Path(job_root_from_cfg()) / SHADOW_LOG_FILENAME


def validate_proposal_shadow(
    proposal: dict,
    *,
    context: dict | None = None,
) -> dict[str, Any]:
    """Validate a proposal in shadow mode and return a plain dict result.

    Shadow mode only gates the proposal through the validator. It does not
    register, execute, display, or otherwise connect the proposal to runtime
    systems.
    """
    context = context or {}
    report = validate_proposal(
        proposal,
        active_action_ids=context.get("active_action_ids"),
        known_requirement_keys=context.get("known_requirement_keys"),
        known_effect_paths=context.get("known_effect_paths"),
        safety_limits=context.get("safety_limits"),
        narrative_context=context.get("narrative_context"),
    )
    report_dict = report.to_dict()
    overall = report_dict["overall"]

    return {
        "stage": "shadow",
        "accepted": overall == "PASS",
        "proposal_id": proposal.get("id") if isinstance(proposal, dict) else None,
        "proposal_label": proposal.get("label") if isinstance(proposal, dict) else None,
        "actor_id": proposal.get("actor_id") if isinstance(proposal, dict) else None,
        "overall": overall,
        "report": report_dict,
    }


def build_shadow_record(
    proposal: dict,
    result: dict,
    *,
    context_summary: dict | None = None,
    run_id: str | None = None,
    source: str | None = None,
) -> dict[str, Any]:
    """Build the stable Action Proposal shadow JSONL record schema."""
    return {
        "schema": SHADOW_RECORD_SCHEMA,
        "stage": "shadow",
        "run_id": run_id,
        "source": source if source is not None else proposal.get("source"),
        "proposal_id": proposal.get("id"),
        "proposal_label": proposal.get("label"),
        "actor_id": proposal.get("actor_id"),
        "accepted": result.get("accepted"),
        "overall": result.get("overall"),
        "report": result.get("report"),
        "context_summary": context_summary or {},
        "proposal": proposal,
    }


def validate_and_build_shadow_record(
    proposal: dict,
    *,
    context: dict | None = None,
    context_summary: dict | None = None,
    run_id: str | None = None,
    source: str | None = None,
) -> dict[str, Any]:
    """Validate a proposal in shadow mode and return a stable log record."""
    result = validate_proposal_shadow(proposal, context=context)
    return build_shadow_record(
        proposal,
        result,
        context_summary=context_summary,
        run_id=run_id,
        source=source,
    )


def append_shadow_log(path: str | Path, record: dict) -> None:
    """Append one JSON Lines record for a shadow validation result."""
    log_path = Path(path)
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with log_path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, ensure_ascii=False))
        handle.write("\n")


def _demo() -> None:
    proposal = {
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
    context = {
        "active_action_ids": {"question_witness"},
        "known_requirement_keys": {"location"},
        "known_effect_paths": {"evidence_score"},
        "safety_limits": {"max_abs_delta": 10},
        "narrative_context": {
            "current_mode": "PURSUE",
            "allowed_modes": {"PURSUE", "FLEE", "FREEZE", "WITNESS"},
            "tone": {"neo-noir"},
            "forbidden_tags": {"world_breaking"},
            "allowed_sources": {"RO", "LLM", "pack", "human"},
            "require_rationale": True,
        },
    }
    record = validate_and_build_shadow_record(
        proposal,
        context=context,
        context_summary={"mode": "PURSUE", "location": "alley"},
        run_id="demo",
    )
    print(f"default_shadow_log_path: {default_shadow_log_path()}")
    print(json.dumps(record, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    _demo()
