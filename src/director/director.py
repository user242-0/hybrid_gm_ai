from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
import random
import yaml
import pathlib


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

    def synthesize_world(self) -> Dict[str, Any]:
        """最小の初期ワールド。数値は演出・分岐用（難度は弄らない）。"""
        self.rng.seed(self.premise.get("seed", 0))
        return {
            "clock": "Day1 08:00",
            "harm": {"value": 0, "threshold_warn": 20},
            "entropy": {"value": 4, "threshold_warn": 10},
            "suspicion": {"value": 3, "max": 10},
            "case_heat": {"value": 2, "max": 10},
            "reload_epoch": 0,
            "unlocks": set(),
            "rumors": [],
            "echoes": [],
        }

    def next_goal(self, world: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        bucket = self.goals_dict.get("modes", {}).get(self.mode, {})
        items = bucket.get("goals", [])
        return self.rng.choice(items) if items else None

    def next_micro_goal(self, world: Dict[str, Any]) -> Optional[str]:
        """Backwards compatible helper that always re-rolls."""
        return self.get_micro_goal(world, reroll=True)

    def get_micro_goal(self, world: Dict[str, Any], reroll: bool = False) -> str:
        mode = self.mode
        if reroll or not self._micro_cache.get(mode):
            bucket = self.goals_dict.get("modes", {}).get(mode, {})
            items = bucket.get("micro", [])
            choice = self.rng.choice(items) if items else "(MicroGoal なし)"
            self._micro_cache[mode] = choice
            self._micro_baseline[mode] = self._capture_micro_baseline(world, mode)
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
        baseline = self._micro_baseline.get(mode, {})
        if mode == "FREEZE":
            if world.get("sobriety_days", 0) >= baseline.get("sobriety_days", 0) + 1:
                return True
            if world.get("victim_names_logged", 0) > baseline.get("victim_names_logged", 0):
                return True
            return False
        if mode == "PURSUE":
            return world.get("evidence_score", 0) >= baseline.get("evidence_score", 0) + 10
        if mode == "FLEE":
            suspicion = world.get("suspicion", {}) if isinstance(world, dict) else {}
            current = suspicion.get("value", 0)
            start = baseline.get("suspicion_value", current)
            target = max(0, start - 1)
            return current <= target
        if mode == "WITNESS":
            return world.get("report_submitted", 0) > baseline.get("report_submitted", 0)
        return False

    def apply_auto_step(self, world: Dict[str, Any]) -> None:
        if not isinstance(world, dict):
            return
        if self.mode == "FREEZE":
            entropy = world.setdefault("entropy", {})
            value = max(0, int(entropy.get("value", 0)) - 1)
            entropy["value"] = value
            world["sobriety_days"] = world.get("sobriety_days", 0) + 1
        elif self.mode == "PURSUE":
            case_heat = world.setdefault("case_heat", {})
            max_value = case_heat.get("max", 0)
            new_value = min(max_value, int(case_heat.get("value", 0)) + 1)
            case_heat["value"] = new_value
            world["evidence_score"] = world.get("evidence_score", 0) + 10
        elif self.mode == "FLEE":
            suspicion = world.setdefault("suspicion", {})
            value = max(0, int(suspicion.get("value", 0)) - 1)
            suspicion["value"] = value
        elif self.mode == "WITNESS":
            world["report_submitted"] = world.get("report_submitted", 0) + 1

    def _capture_micro_baseline(self, world: Dict[str, Any], mode: str) -> Dict[str, Any]:
        if not isinstance(world, dict):
            return {}
        if mode == "FREEZE":
            return {
                "sobriety_days": world.get("sobriety_days", 0),
                "victim_names_logged": world.get("victim_names_logged", 0),
            }
        if mode == "PURSUE":
            return {"evidence_score": world.get("evidence_score", 0)}
        if mode == "FLEE":
            suspicion = world.get("suspicion", {})
            if isinstance(suspicion, dict):
                return {"suspicion_value": suspicion.get("value")}
            return {"suspicion_value": 0}
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