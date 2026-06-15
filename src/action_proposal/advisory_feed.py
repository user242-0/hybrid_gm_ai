"""Display feed adapter for Action Proposal advisory items.

This module only shapes advisory items into HUD-readable display data. It
does not register actions, connect to HUD, or mutate runtime state.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from src.action_proposal.advisory import ADVISORY_SCHEMA, build_advisory_items

ADVISORY_FEED_SCHEMA = "action_proposal_advisory_feed.v0.1"
ADVISORY_DISPLAY_ITEM_SCHEMA = "action_proposal_advisory_display_item.v0.1"
DEFAULT_FEED_LIMIT = 5


def _dict_or_empty(value: Any) -> dict:
    if isinstance(value, dict):
        return value
    return {}


def _first_text(*values: Any, default: str = "") -> str:
    for value in values:
        if isinstance(value, str) and value:
            return value
    return default


def build_display_item(advisory_item: dict) -> dict[str, Any] | None:
    """Build one stable display item from a suggested advisory item."""
    if advisory_item.get("stage") != "advisory":
        return None
    if advisory_item.get("status") != "suggested":
        return None

    display = _dict_or_empty(advisory_item.get("display"))
    proposal = _dict_or_empty(advisory_item.get("proposal"))
    report = _dict_or_empty(advisory_item.get("report"))

    proposal_id = advisory_item.get("proposal_id") or proposal.get("id")
    source = advisory_item.get("source") or proposal.get("source")
    title = _first_text(
        display.get("title"),
        advisory_item.get("proposal_label"),
        proposal_id,
        default="Untitled proposal",
    )
    subtitle = _first_text(
        display.get("subtitle"),
        f"{source} proposal" if source else None,
        default="Action proposal",
    )
    detail = _first_text(
        display.get("detail"),
        advisory_item.get("rationale"),
        proposal.get("rationale"),
        default="",
    )
    reason_codes = report.get("reason_codes")
    if not isinstance(reason_codes, dict):
        reason_codes = {}

    return {
        "schema": ADVISORY_DISPLAY_ITEM_SCHEMA,
        "stage": "advisory",
        "status": "suggested",
        "proposal_id": proposal_id,
        "title": title,
        "subtitle": subtitle,
        "detail": detail,
        "source": source,
        "report_overall": report.get("overall"),
        "reason_codes": reason_codes,
        "proposal": proposal,
        "advisory_schema": advisory_item.get("schema") or ADVISORY_SCHEMA,
    }


def build_advisory_feed(
    advisory_items: list[dict],
    *,
    limit: int | None = DEFAULT_FEED_LIMIT,
    run_id: str | None = None,
) -> dict[str, Any]:
    """Build a display feed from advisory items."""
    display_items = []
    for advisory_item in advisory_items:
        display_item = build_display_item(advisory_item)
        if display_item is not None:
            display_items.append(display_item)

    if isinstance(limit, int):
        display_items = display_items[:limit]

    return {
        "schema": ADVISORY_FEED_SCHEMA,
        "stage": "advisory",
        "run_id": run_id,
        "count": len(display_items),
        "items": display_items,
    }


def build_advisory_feed_from_shadow_records(
    shadow_records: list[dict],
    *,
    limit: int | None = DEFAULT_FEED_LIMIT,
    run_id: str | None = None,
) -> dict[str, Any]:
    """Build a display feed from shadow records via the advisory adapter."""
    advisory_items = build_advisory_items(shadow_records)
    return build_advisory_feed(advisory_items, limit=limit, run_id=run_id)


def load_jsonl_records(path: str | Path) -> list[dict]:
    """Load JSON Lines records from a path, returning an empty list if absent."""
    jsonl_path = Path(path)
    if not jsonl_path.exists():
        return []

    records: list[dict] = []
    with jsonl_path.open("r", encoding="utf-8") as handle:
        for line in handle:
            stripped = line.strip()
            if not stripped:
                continue
            record = json.loads(stripped)
            if isinstance(record, dict):
                records.append(record)
    return records


def build_advisory_feed_from_shadow_log(
    path: str | Path,
    *,
    limit: int | None = DEFAULT_FEED_LIMIT,
    run_id: str | None = None,
) -> dict[str, Any]:
    """Build a display feed from a shadow JSONL log file."""
    shadow_records = load_jsonl_records(path)
    return build_advisory_feed_from_shadow_records(
        shadow_records,
        limit=limit,
        run_id=run_id,
    )


def _demo_context() -> dict[str, Any]:
    return {
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


def _demo() -> None:
    from src.action_proposal.shadow import validate_and_build_shadow_record

    proposal = {
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
    record = validate_and_build_shadow_record(
        proposal,
        context=_demo_context(),
        context_summary={"mode": "PURSUE", "location": "alley"},
        run_id="demo",
    )
    feed = build_advisory_feed_from_shadow_records([record], run_id="demo")
    print(json.dumps(feed, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    _demo()
