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
        bucket = self.goals_dict.get("modes", {}).get(self.mode, {})
        items = bucket.get("micro", [])
        return self.rng.choice(items) if items else None

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