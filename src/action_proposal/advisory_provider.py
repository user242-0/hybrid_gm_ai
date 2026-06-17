"""Read-only advisory feed provider for Action Proposal shadow logs.

This module exposes stable entry points for future HUD reads. It does not
register actions, connect to HUD, or mutate shadow logs.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from src.action_proposal.advisory_feed import build_advisory_feed_from_shadow_log

ADVISORY_PROVIDER_SCHEMA = "action_proposal_advisory_provider.v0.1"
DEFAULT_PROVIDER_LIMIT = 5


def get_default_advisory_feed_path() -> Path:
    """Return the default shadow log path used as advisory feed source."""
    from src.action_proposal.shadow import default_shadow_log_path

    return default_shadow_log_path()


def _provider_info(path: Path) -> dict[str, Any]:
    return {
        "schema": ADVISORY_PROVIDER_SCHEMA,
        "source": "shadow_log",
        "path": str(path),
        "read_only": True,
    }


def _filter_items_by_actor(items: list[dict], actor_id: str | None) -> list[dict]:
    if actor_id is None:
        return items
    return [item for item in items if item.get("actor_id") == actor_id]


def get_advisory_feed(
    *,
    path: str | Path | None = None,
    limit: int | None = DEFAULT_PROVIDER_LIMIT,
    run_id: str | None = None,
    actor_id: str | None = None,
) -> dict[str, Any]:
    """Return a read-only advisory feed from a shadow JSONL log."""
    feed_path = Path(path) if path is not None else get_default_advisory_feed_path()
    feed = build_advisory_feed_from_shadow_log(feed_path, limit=None, run_id=run_id)
    items = _filter_items_by_actor(feed["items"], actor_id)
    if isinstance(limit, int):
        items = items[:limit]
    feed["items"] = items
    feed["count"] = len(items)
    feed["provider"] = _provider_info(feed_path)
    return feed


def get_advisory_display_items(
    *,
    path: str | Path | None = None,
    limit: int | None = DEFAULT_PROVIDER_LIMIT,
    run_id: str | None = None,
    actor_id: str | None = None,
) -> list[dict]:
    """Return only display items for callers that do not need feed metadata."""
    feed = get_advisory_feed(path=path, limit=limit, run_id=run_id, actor_id=actor_id)
    return feed["items"]


def has_advisory_items(
    *,
    path: str | Path | None = None,
    limit: int | None = DEFAULT_PROVIDER_LIMIT,
    run_id: str | None = None,
    actor_id: str | None = None,
) -> bool:
    """Return whether the read-only advisory feed currently has any items."""
    return len(
        get_advisory_display_items(
            path=path,
            limit=limit,
            run_id=run_id,
            actor_id=actor_id,
        )
    ) > 0


def _demo() -> None:
    feed = get_advisory_feed()
    print(json.dumps(feed, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    _demo()
