"""Reversible Operator (RO) – Phase A: advice + reason from player log only."""

import json
import datetime
from pathlib import Path
from collections import Counter
from typing import Dict, List, Optional

from src.utility.config_loader import get_cfg
from src.logger import LOG_PATH_PLAYER

RO_DIARY_PATH = Path("data/logs") / "ro_diary_latest.jsonl"
_DEFAULT_WINDOW = 50


# ---- internal helpers ----

def _ro_cfg() -> dict:
    cfg = get_cfg()
    return cfg.get("ro", {})


def _read_recent_player_log(n: int) -> List[dict]:
    """Return last *n* entries from the player log."""
    if not LOG_PATH_PLAYER.exists():
        return []
    text = LOG_PATH_PLAYER.read_text(encoding="utf-8").strip()
    if not text:
        return []
    entries: List[dict] = []
    for line in text.splitlines()[-n:]:
        try:
            entries.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return entries


def _write_diary(actor_id: str, rec: dict, score: float) -> None:
    """Append one RO diary line to ro_diary_latest.jsonl."""
    entry: Dict[str, object] = {
        "ts": datetime.datetime.now().isoformat(timespec="seconds"),
        "source": "RO",
        "controller_id": f"RO:{actor_id}",
        "actor_id": actor_id,
        "actor_rc_id": actor_id,
        "ro_type": "recommendation",
        "action_id": rec["action_id"],
        "why": rec["why"],
        "score": round(score, 2),
    }
    if rec.get("risk"):
        entry["risk"] = rec["risk"]
    if rec.get("plan_b"):
        entry["plan_b"] = rec["plan_b"]

    RO_DIARY_PATH.parent.mkdir(parents=True, exist_ok=True)
    with RO_DIARY_PATH.open("a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")
        f.flush()


# ---- public API ----

def recommend(
    actor_id: str,
    candidate_action_ids: List[str],
    microgoal_action: Optional[str] = None,
    microgoal_text: Optional[str] = None,
) -> Optional[dict]:
    """Score *candidate_action_ids* against recent player log and return top-1.

    Returns ``None`` when RO is disabled or no candidates are given.
    Result dict keys: ``action_id``, ``why``, and optionally ``risk``, ``plan_b``.
    """
    ro = _ro_cfg()
    if not ro.get("enabled", False):
        return None

    window = ro.get("log_window", _DEFAULT_WINDOW)
    entries = _read_recent_player_log(window)

    if not candidate_action_ids:
        return None

    # --- scoring ---
    recent_actions = [e.get("action_id", "") for e in entries]
    last_3 = recent_actions[-3:] if len(recent_actions) >= 3 else recent_actions
    last_1 = recent_actions[-1:] if recent_actions else []
    freq = Counter(recent_actions)

    scores: Dict[str, float] = {}
    for aid in candidate_action_ids:
        score = 1.0
        # microgoal proximity
        if microgoal_action and aid == microgoal_action:
            score += 2.0
        # anti-spam
        if aid in last_1:
            score -= 2.0
        elif aid in last_3:
            score -= 1.0
        # frequency penalty (diminishing)
        count = freq.get(aid, 0)
        if count > 3:
            score -= 0.5 * min(count - 3, 4)
        scores[aid] = score

    best = max(scores, key=lambda k: scores[k])
    best_score = scores[best]

    # --- build recommendation ---
    reasons: List[str] = []
    if microgoal_action and best == microgoal_action:
        reasons.append(f"マイクロゴール「{microgoal_text or microgoal_action}」に直結")
    if best not in last_3:
        reasons.append("直近で未実行のため新鮮")
    if not reasons:
        reasons.append("スコア最高の候補")
    why = "；".join(reasons)

    risk = None
    if best_score < 0:
        risk = "全候補が連打気味のためスコアが低い"

    plan_b = None
    sorted_actions = sorted(scores.items(), key=lambda x: -x[1])
    if len(sorted_actions) > 1:
        plan_b = sorted_actions[1][0]

    rec: Dict[str, object] = {"action_id": best, "why": why}
    if risk:
        rec["risk"] = risk
    if plan_b:
        rec["plan_b"] = plan_b

    _write_diary(actor_id, rec, best_score)
    return rec
