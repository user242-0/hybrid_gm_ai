from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple
import random
import yaml
import pathlib


MICRO_RULES: Dict[str, Dict[str, Any]] = {
    "未読の通報を1件だけ確認": {
        "action": "check_tip",
        "time_min": 5,
        "done": lambda world, baseline: world.get("tips_checked", 0)
        >= baseline.get("tips_checked", 0) + 1,
    },
    "本日の酒量を規定以下にする": {
        "action": "limit_drink",
        "time_min": 10,
        "done": lambda world, baseline: world.get("sobriety_days", 0)
        >= baseline.get("sobriety_days", 0) + 1,
    },
    "被害者の名前をノートに1人追記": {
        "action": "log_victim",
        "time_min": 3,
        "done": lambda world, baseline: world.get("victim_names_logged", 0)
        >= baseline.get("victim_names_logged", 0) + 1,
    },
    "現場で青い繊維を1点採取": {
        "action": "collect_fiber",
        "time_min": 15,
        "done": lambda world, baseline: world.get("evidence_score", 0)
        >= baseline.get("evidence_score", 0) + 10,
    },
    "監視カメラの時刻ズレを補正": {
        "action": "fix_cam_clock",
        "time_min": 12,
        "done": lambda world, baseline: world.get("cams_fixed", 0)
        >= baseline.get("cams_fixed", 0) + 1,
    },
    "元相棒に5分だけ電話": {
        "action": "call_partner",
        "time_min": 5,
        "done": lambda world, baseline: world.get("partner_calls", 0)
        >= baseline.get("partner_calls", 0) + 1,
    },
    "裏路地→高架下→駅裏へ移動": {
        "action": "move_low_profile",
        "time_min": 8,
        "done": lambda world, baseline: _current_suspicion(world)
        <= max(0, baseline.get("suspicion_value", _current_suspicion(world)) - 1),
    },
    "顔を見られた店を避ける（タグ付け）": {
        "action": "mark_avoid_shop",
        "time_min": 2,
        "done": lambda world, baseline: world.get("avoid_tags", 0)
        >= baseline.get("avoid_tags", 0) + 1,
    },
    "真実を1項だけ報告書に残す": {
        "action": "file_report",
        "time_min": 7,
        "done": lambda world, baseline: world.get("report_submitted", 0)
        > baseline.get("report_submitted", 0),
    },
}


def _rule_for_micro(text: Optional[str]) -> Optional[Dict[str, Any]]:
    return MICRO_RULES.get(text or "")


def _current_suspicion(world: Dict[str, Any]) -> int:
    suspicion = world.get("suspicion") if isinstance(world, dict) else None
    if isinstance(suspicion, dict):
        value = suspicion.get("value")
        if isinstance(value, (int, float)):
            return int(value)
    return 0


@dataclass
class Director:
    premise: Dict[str, Any]
    goals_dict: Dict[str, Any]
    rng: random.Random = field(default_factory=random.Random)
    mode: str = "FREEZE"
    beat_state: Dict[str, bool] = field(
        default_factory=lambda: {
            "Inciting": False,
            "Rumination": False,
            "Escalation": False,
            "Climax": False,
        }
    )

    def __post_init__(self) -> None:
        modes = self.goals_dict.get("modes", {})
        self._micro_cache: Dict[str, Optional[str]] = {key: None for key in modes.keys()}
        for fallback in ("FREEZE", "FLEE", "PURSUE", "WITNESS"):
            self._micro_cache.setdefault(fallback, None)
        self._micro_baseline: Dict[str, Dict[str, Any]] = {
            key: {} for key in self._micro_cache.keys()
        }
        self._recent_micro_ids: Dict[str, List[str]] = {
            key: [] for key in self._micro_cache.keys()
        }
        self._recent_k: int = 3

    def synthesize_world(self) -> Dict[str, Any]:
        """最小の初期ワールド。数値は演出・分岐用（難度は弄らない）。"""
        self.rng.seed(self.premise.get("seed", 0))
        return {
            "clock_min": 0,
            "clock": "Day1 00:00",
            "harm": {"value": 0, "threshold_warn": 20},
            "entropy": {"value": 4, "threshold_warn": 10},
            "suspicion": {"value": 3, "max": 10},
            "case_heat": {"value": 2, "max": 10},
            "reload_epoch": 0,
            "unlocks": set(),
            "rumors": [],
            "echoes": [],
            "tips_checked": 0,
            "sobriety_days": 0,
            "victim_names_logged": 0,
            "evidence_score": 0,
            "cams_fixed": 0,
            "partner_calls": 0,
            "avoid_tags": 0,
            "report_submitted": 0,
        }

    def next_goal(self, world: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        bucket = self.goals_dict.get("modes", {}).get(self.mode, {})
        items = bucket.get("goals", [])
        return self.rng.choice(items) if items else None

    def next_micro_goal(self, world: Dict[str, Any]) -> Optional[str]:
        """Backwards compatible helper that always re-rolls."""
        return self.get_micro_goal(world, reroll=True)

    def _micro_id(self, value: str) -> str:
        import hashlib

        return hashlib.md5(value.encode("utf-8")).hexdigest()[:8]

    def get_micro_goal(self, world: Dict[str, Any], reroll: bool = False) -> str:
        mode = self.mode
        if reroll or not self._micro_cache.get(mode):
            bucket = self.goals_dict.get("modes", {}).get(mode, {})
            items = bucket.get("micro", [])
            history = self._recent_micro_ids.setdefault(mode, [])
            recent = set(history)
            pool = [item for item in items if self._micro_id(item) not in recent]
            if not pool and items:
                last_id = history[-1] if history else None
                pool = [item for item in items if self._micro_id(item) != last_id]
            pool = pool or items
            choice = self.rng.choice(pool) if pool else "(MicroGoal なし)"            
            self._micro_cache[mode] = choice
            self._micro_baseline[mode] = self._capture_micro_baseline(world, mode)

            choice_id = self._micro_id(choice)
            history.append(choice_id)
            if len(history) > self._recent_k:
                del history[0 : len(history) - self._recent_k]


        return self._micro_cache[mode] or "(MicroGoal なし)"

    def clear_micro_goal(self, mode: Optional[str] = None) -> None:
        target = mode or self.mode
        if target not in self._micro_cache:
            self._micro_cache[target] = None
            self._micro_baseline[target] = {}
            return
        self._micro_cache[target] = None
        self._micro_baseline[target] = {}

    def is_micro_goal_done(self, world: Dict[str, Any]) -> bool:
        mode = self.mode
        rule = _rule_for_micro(self._micro_cache.get(mode))
        baseline = self._micro_baseline.get(mode, {})
        if rule:
            done_callable = rule.get("done")
            if callable(done_callable):
                try:
                    return bool(done_callable(world, baseline))
                except TypeError:
                    return bool(done_callable(world))  # type: ignore[misc]
                except Exception:
                    return False
        if mode == "FREEZE":
            if world.get("sobriety_days", 0) >= baseline.get("sobriety_days", 0) + 1:
                return True
            if world.get("victim_names_logged", 0) > baseline.get("victim_names_logged", 0):
                return True
            if world.get("tips_checked", 0) > baseline.get("tips_checked", 0):
                return True
            return False
        if mode == "PURSUE":
            if world.get("evidence_score", 0) >= baseline.get("evidence_score", 0) + 10:
                return True
            if world.get("cams_fixed", 0) > baseline.get("cams_fixed", 0):
                return True
            if world.get("partner_calls", 0) > baseline.get("partner_calls", 0):
                return True
            return False
        if mode == "FLEE":
            current = _current_suspicion(world)
            start = baseline.get("suspicion_value", current)
            target = max(0, start - 1)
            if current <= target:
                return True
            if world.get("avoid_tags", 0) > baseline.get("avoid_tags", 0):
                return True
            return False
        if mode == "WITNESS":
            return world.get("report_submitted", 0) > baseline.get("report_submitted", 0)
        return False

    def apply_auto_step(self, world: Dict[str, Any]) -> Tuple[Optional[str], int]:
        if not isinstance(world, dict):
            return None, 5
        rule = _rule_for_micro(self._micro_cache.get(self.mode))
        if rule:
            action = rule.get("action")
            try:
                time_min = int(rule.get("time_min", 5))
            except (TypeError, ValueError):
                time_min = 5
            if time_min < 0:
                time_min = 0
            return action, time_min
        fallback: Dict[str, Tuple[Optional[str], int]] = {
            "FREEZE": ("limit_drink", 5),
            "PURSUE": ("collect_fiber", 10),
            "FLEE": ("move_low_profile", 5),
            "WITNESS": ("file_report", 5),
        }
        return fallback.get(self.mode, (None, 5))

    def _capture_micro_baseline(self, world: Dict[str, Any], mode: str) -> Dict[str, Any]:
        if not isinstance(world, dict):
            return {}
        if mode == "FREEZE":
            return {
                "sobriety_days": world.get("sobriety_days", 0),
                "victim_names_logged": world.get("victim_names_logged", 0),
                "tips_checked": world.get("tips_checked", 0),
            }
        if mode == "PURSUE":
            return {
                "evidence_score": world.get("evidence_score", 0),
                "cams_fixed": world.get("cams_fixed", 0),
                "partner_calls": world.get("partner_calls", 0),
            }
        if mode == "FLEE":
            suspicion = world.get("suspicion", {})
            if isinstance(suspicion, dict):
                value = suspicion.get("value")
                base = int(value) if isinstance(value, (int, float)) else 0
            else:
                base = 0
            return {
                "suspicion_value": base,
                "avoid_tags": world.get("avoid_tags", 0),
            }
        if mode == "WITNESS":
            return {"report_submitted": world.get("report_submitted", 0)}
        return {}

    def tick(self, world: Dict[str, Any]) -> List[Dict[str, Any]]:
        """進行監督：演出/分岐の注入のみ。worldは破壊的に更新可。"""
        scenes: List[Dict[str, Any]] = []
        harm = world.get("harm", {})
        harm_value = harm.get("value", 0)
        harm_threshold = harm.get("threshold_warn")
        if (
            harm_threshold is not None
            and harm_value >= harm_threshold
            and not self.beat_state.get("Escalation")
        ):
            scenes.append(
                self.inject_scene(
                    intent="Escalation",
                    why_now="harm_threshold_crossed",
                    salience=0.8,
                )
            )
            self.beat_state["Escalation"] = True

        if self.mode == "FREEZE" and not self.beat_state.get("Rumination"):
            scenes.append(
                self.inject_scene(
                    intent="Rumination",
                    why_now="prolonged_freeze",
                    salience=0.6,
                )
            )
            self.beat_state["Rumination"] = True

        sobriety_days = world.get("sobriety_days", 0)
        if sobriety_days >= 3:
            world.setdefault("unlocks", set()).add("SwitchToPURSUE")

        return scenes

    def inject_scene(self, intent: str, why_now: str, salience: float) -> Dict[str, Any]:
        scene = {"intent": intent, "why_now": why_now, "salience": salience}
        return scene


def load_yaml(path: str) -> dict:
    target = pathlib.Path(path)
    if not target.is_absolute():
        # Allow relative paths from caller's working directory
        target = pathlib.Path.cwd() / target
    with target.open("r", encoding="utf-8") as handle:
        return yaml.safe_load(handle)