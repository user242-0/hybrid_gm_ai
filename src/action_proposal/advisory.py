"""Advisory adapter for Action Proposal shadow records.

This module only shapes accepted shadow records into display candidates. It
does not register actions, connect to HUD, or mutate runtime state.
"""

from __future__ import annotations

import json
from typing import Any

from src.action_proposal.shadow import SHADOW_RECORD_SCHEMA, validate_and_build_shadow_record

ADVISORY_SCHEMA = "action_proposal_advisory.v0.1"


def _proposal_from_shadow(shadow_record: dict) -> dict[str, Any]:
    proposal = shadow_record.get("proposal")
    if isinstance(proposal, dict):
        return proposal
    return {}


def build_advisory_item(shadow_record: dict) -> dict[str, Any] | None:
    """Build a display-only advisory item from a passing shadow record."""
    if shadow_record.get("accepted") is not True or shadow_record.get("overall") != "PASS":
        return None

    proposal = _proposal_from_shadow(shadow_record)
    proposal_id = shadow_record.get("proposal_id") or proposal.get("id")
    proposal_label = shadow_record.get("proposal_label") or proposal.get("label")
    actor_id = shadow_record.get("actor_id")
    if actor_id is None:
        actor_id = proposal.get("actor_id")
    source = shadow_record.get("source") or proposal.get("source")
    rationale = proposal.get("rationale") or ""
    subtitle = f"{source} proposal" if source else "Action proposal"

    return {
        "schema": ADVISORY_SCHEMA,
        "stage": "advisory",
        "status": "suggested",
        "proposal_id": proposal_id,
        "proposal_label": proposal_label,
        "actor_id": actor_id,
        "source": source,
        "rationale": rationale,
        "display": {
            "title": proposal_label,
            "subtitle": subtitle,
            "detail": rationale,
        },
        "proposal": proposal,
        "report": shadow_record.get("report") or {},
        "shadow_schema": shadow_record.get("schema") or SHADOW_RECORD_SCHEMA,
    }


def build_advisory_items(shadow_records: list[dict]) -> list[dict[str, Any]]:
    """Return advisory items for passing shadow records only."""
    items: list[dict[str, Any]] = []
    for record in shadow_records:
        item = build_advisory_item(record)
        if item is not None:
            items.append(item)
    return items


def validate_proposal_to_advisory(
    proposal: dict,
    *,
    context: dict | None = None,
    context_summary: dict | None = None,
    run_id: str | None = None,
    source: str | None = None,
) -> dict[str, Any] | None:
    """Validate a proposal in shadow mode and return its advisory item if PASS."""
    shadow_record = validate_and_build_shadow_record(
        proposal,
        context=context,
        context_summary=context_summary,
        run_id=run_id,
        source=source,
    )
    return build_advisory_item(shadow_record)


def _demo() -> None:
    proposal = {
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
    item = validate_proposal_to_advisory(
        proposal,
        context=context,
        context_summary={"mode": "PURSUE", "location": "alley"},
        run_id="demo",
    )
    print(json.dumps(item, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    _demo()
