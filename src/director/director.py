from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple
import random
import yaml
import pathlib

from logic.cond_eval import eval_cond, parse_cond, _get_path as get_path
from logic.emotion_traits import derived_traits


LEGACY_MICRO_RULES: Dict[str, Dict[str, Any]] = {
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

# Backwards compatible alias for legacy imports/tests.
MICRO_RULES = LEGACY_MICRO_RULES


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
    _micro_done_debug_emitted: bool = field(default=False, init=False)
    beat_state: Dict[str, bool] = field(
        default_factory=lambda: {
            "Inciting": False,
            "Rumination": False,
            "Escalation": False,
            "Climax": False,
        }
    )

    def __post_init__(self) -> None:
        modes_from_premise = self.premise.get("modes_enabled") or []
        if isinstance(modes_from_premise, str):
            modes_from_premise = [modes_from_premise]
        elif not isinstance(modes_from_premise, list):
            modes_from_premise = list(modes_from_premise)
        modes_from_yaml = list((self.goals_dict or {}).get("modes", {}).keys())
        available = [m for m in modes_from_premise if m in modes_from_yaml] or modes_from_yaml
        self._available_modes: List[str] = available
        if self._available_modes:
            self.mode = self._available_modes[0]
        else:
            self.mode = "FREEZE"

        modes = (self.goals_dict or {}).get("modes", {})
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
        self._last_day: Optional[int] = None  # 日替わりリセット用

    def _extract_day(self, world: Dict[str, Any]) -> Optional[int]:
        """Extract day number from world clock."""
        clock = world.get("clock") if isinstance(world, dict) else None
        if isinstance(clock, str):
            # Parse "Day1 00:00" format
            try:
                day_part = clock.split()[0]
                return int(day_part.replace("Day", ""))
            except (ValueError, IndexError):
                return None
        if isinstance(clock, dict):
            day = clock.get("day")
            if isinstance(day, (int, float)):
                return int(day)
        return None

    def _check_daily_reset(self, world: Dict[str, Any]) -> None:
        """Reset micro goal history when day changes."""
        current_day = self._extract_day(world)
        if current_day is None:
            return
        if self._last_day is not None and current_day != self._last_day:
            # 日が変わったので履歴をリセット
            for mode in self._recent_micro_ids:
                self._recent_micro_ids[mode] = []
            actor_goals = world.get("actor_micro_goals")
            if isinstance(actor_goals, dict):
                for state in actor_goals.values():
                    if isinstance(state, dict):
                        state["recent_ids"] = {}
            print(f"[Director] daily reset: day {self._last_day} -> {current_day}")
        self._last_day = current_day

    def available_modes(self) -> List[str]:
        """Return the list of modes enabled for the current scenario."""

        return list(self._available_modes)

    def set_mode(self, mode: str) -> bool:
        if mode in self._available_modes or not self._available_modes:
            self.mode = mode
            self.clear_micro_goal(mode)
            return True
        return False

    def get_actor_mode(
        self,
        world: Dict[str, Any],
        actor_id: Optional[str],
        fallback_mode: Optional[str] = None,
    ) -> str:
        """Return an actor's current mode, falling back to Director.mode."""

        actor_modes = world.get("actor_modes") if isinstance(world, dict) else None
        if actor_id and isinstance(actor_modes, dict):
            actor_mode = actor_modes.get(actor_id)
            if isinstance(actor_mode, str) and actor_mode:
                return actor_mode
        return fallback_mode or self.mode

    def set_actor_mode(
        self,
        world: Dict[str, Any],
        actor_id: str,
        mode: str,
    ) -> bool:
        """Persist an actor-specific mode in the Director world."""

        if not isinstance(world, dict) or not actor_id or not isinstance(mode, str) or not mode:
            return False
        if self._available_modes and mode not in self._available_modes:
            return False
        actor_modes = world.setdefault("actor_modes", {})
        if not isinstance(actor_modes, dict):
            return False
        actor_modes[actor_id] = mode
        return True

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
            "flags": dict(
                (self.goals_dict or {}).get("affordances", {}).get("canonical_facts", {})
            ),
            "affordances": {"discoveries": [], "spent_opportunities": set()},
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

    def _is_micro_goal_done_for_text(
        self,
        text: Optional[str],
        world: Dict[str, Any],
        baseline: Dict[str, Any],
        mode: str,
    ) -> bool:
        rule = self._lookup_rule(text, mode)
        if rule:
            done_expr = rule.get("done")
            if isinstance(done_expr, str):
                if not done_expr.strip():
                    return False
                left, _, _ = parse_cond(done_expr)
                if left:
                    current = get_path(world, left)
                    if current is None:
                        return False
                return eval_cond(done_expr, world, prev_world=None)
            if callable(done_expr):
                try:
                    return bool(done_expr(world, baseline))
                except TypeError:
                    return bool(done_expr(world))  # type: ignore[misc]
                except Exception:
                    return False
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

    def _micro_bank(self, mode: str) -> List[Dict[str, Any]]:
        bucket = self.goals_dict.get("modes", {}).get(mode, {})
        raw = bucket.get("micro", [])
        bank: List[Dict[str, Any]] = []
        for item in raw:
            if isinstance(item, str):
                fallback = LEGACY_MICRO_RULES.get(item, {})
                bank.append(
                    {
                        "text": item,
                        "action": fallback.get("action"),
                        "time_min": fallback.get("time_min", 5),
                        "done": fallback.get("done"),
                    }
                )
            elif isinstance(item, dict):
                text = item.get("text")
                if not text:
                    continue
                raw_time = item.get("time_min", 5)
                try:
                    time_min = int(raw_time)
                except (TypeError, ValueError):
                    time_min = 5
                bank.append(
                    {
                        "text": text,
                        "action": item.get("action"),
                        "time_min": time_min,
                        "done": item.get("done"),
                    }
                )
        return bank

    def _lookup_rule(self, text: Optional[str], mode: Optional[str] = None) -> Optional[Dict[str, Any]]:
        if not text:
            return None
        target_mode = mode or self.mode
        for rule in self._micro_bank(target_mode):
            if rule.get("text") == text:
                return rule
        return LEGACY_MICRO_RULES.get(text)

    def get_micro_goal(self, world: Dict[str, Any], reroll: bool = False) -> str:
        self._check_daily_reset(world)  # 日替わりで履歴リセット
        mode = self.mode
        if reroll or not self._micro_cache.get(mode):
            bank = self._micro_bank(mode)
            items = [entry["text"] for entry in bank if entry.get("text")]
            history = self._recent_micro_ids.setdefault(mode, [])
            recent = set(history)
            pool = [item for item in items if self._micro_id(item) not in recent]
            if not pool and items:
                last_id = history[-1] if history else None
                pool = [item for item in items if self._micro_id(item) != last_id]
            primary_pool = pool or items
            all_pool = items or []
            max_attempts = len(all_pool)
            choice = None
            baseline = {}
            attempted: set[str] = set()
            for candidate_pool in (primary_pool, all_pool):
                if choice is not None:
                    break
                remaining = [item for item in candidate_pool if item not in attempted]
                self.rng.shuffle(remaining)
                for candidate in remaining:
                    if len(attempted) >= max_attempts:
                        break
                    attempted.add(candidate)
                    self._micro_cache[mode] = candidate
                    baseline = self._capture_micro_baseline(world, mode)
                    self._micro_baseline[mode] = baseline
                    if candidate and self.is_micro_goal_done(world):
                        continue
                    choice = candidate
                    break
            if choice is None:
                choice = "(MicroGoal なし)"
                baseline = {}
                self._micro_cache[mode] = choice
                self._micro_baseline[mode] = baseline
            else:
                self._micro_cache[mode] = choice
                self._micro_baseline[mode] = baseline

            choice_id = self._micro_id(choice)
            history.append(choice_id)
            if len(history) > self._recent_k:
                del history[0 : len(history) - self._recent_k]

        return self._micro_cache[mode] or "(MicroGoal なし)"

    def get_micro_goal_for_actor(
        self,
        world: Dict[str, Any],
        actor_id: Optional[str],
        reroll: bool = False,
    ) -> str:
        """Return and persist the MicroGoal for one actor.

        Actor-specific state lives in the Director world so it survives save/load.
        Missing actor IDs retain the legacy global MicroGoal behavior.
        """

        if not actor_id or not isinstance(world, dict):
            return self.get_micro_goal(world, reroll=reroll)

        self._check_daily_reset(world)
        mode = self.get_actor_mode(world, actor_id, fallback_mode=self.mode)
        actor_goals = world.setdefault("actor_micro_goals", {})
        if not isinstance(actor_goals, dict):
            actor_goals = {}
            world["actor_micro_goals"] = actor_goals
        state = actor_goals.get(actor_id)
        if not isinstance(state, dict):
            state = {}
            actor_goals[actor_id] = state

        mode_changed = state.get("mode") != mode
        current = state.get("text")
        if reroll or mode_changed or not isinstance(current, str) or not current:
            bank = self._micro_bank(mode)
            items = [entry["text"] for entry in bank if entry.get("text")]
            recent_by_mode = state.setdefault("recent_ids", {})
            if not isinstance(recent_by_mode, dict):
                recent_by_mode = {}
                state["recent_ids"] = recent_by_mode
            history = recent_by_mode.setdefault(mode, [])
            if not isinstance(history, list):
                history = []
                recent_by_mode[mode] = history

            recent = set(history)
            pool = [item for item in items if self._micro_id(item) not in recent]
            if not pool and items:
                last_id = history[-1] if history else None
                pool = [item for item in items if self._micro_id(item) != last_id]

            choice = None
            baseline: Dict[str, Any] = {}
            attempted: set[str] = set()
            for candidate_pool in (pool or items, items):
                if choice is not None:
                    break
                remaining = [item for item in candidate_pool if item not in attempted]
                self.rng.shuffle(remaining)
                for candidate in remaining:
                    attempted.add(candidate)
                    candidate_baseline = self._capture_micro_baseline(world, mode)
                    if self._is_micro_goal_done_for_text(
                        candidate,
                        world,
                        candidate_baseline,
                        mode,
                    ):
                        continue
                    choice = candidate
                    baseline = candidate_baseline
                    break

            if choice is None:
                choice = "(MicroGoal なし)"
                baseline = {}

            state["text"] = choice
            state["mode"] = mode
            state["baseline"] = baseline
            history.append(self._micro_id(choice))
            if len(history) > self._recent_k:
                del history[0 : len(history) - self._recent_k]

        return state.get("text") or "(MicroGoal なし)"

    def clear_micro_goal(self, mode: Optional[str] = None) -> None:
        target = mode or self.mode
        if target not in self._micro_cache:
            self._micro_cache[target] = None
            self._micro_baseline[target] = {}
            return
        self._micro_cache[target] = None
        self._micro_baseline[target] = {}

    def clear_micro_goal_for_actor(
        self,
        world: Dict[str, Any],
        actor_id: Optional[str],
    ) -> None:
        """Clear one actor's current MicroGoal without touching other actors."""

        if not actor_id or not isinstance(world, dict):
            self.clear_micro_goal()
            return
        actor_goals = world.get("actor_micro_goals")
        if not isinstance(actor_goals, dict):
            return
        state = actor_goals.get(actor_id)
        if not isinstance(state, dict):
            return
        state["text"] = None
        state["baseline"] = {}

    def is_micro_goal_done(self, world: Dict[str, Any]) -> bool:
        mode = self.mode
        micro = self._micro_cache.get(mode)
        if not micro or micro == "(MicroGoal なし)":
            return False
        baseline = self._micro_baseline.get(mode, {})
        done = self._is_micro_goal_done_for_text(micro, world, baseline, mode)
        if done:
            self._debug_micro_goal_done(world, baseline, micro, mode)
        return done

    def is_micro_goal_done_for_actor(
        self,
        world: Dict[str, Any],
        actor_id: Optional[str],
    ) -> bool:
        """Return completion state for one actor's persisted MicroGoal."""

        if not actor_id or not isinstance(world, dict):
            return self.is_micro_goal_done(world)
        actor_goals = world.get("actor_micro_goals")
        state = actor_goals.get(actor_id) if isinstance(actor_goals, dict) else None
        if not isinstance(state, dict):
            return False
        micro = state.get("text")
        if not micro or micro == "(MicroGoal なし)":
            return False
        mode = state.get("mode")
        if not isinstance(mode, str) or not mode:
            mode = self.get_actor_mode(world, actor_id, fallback_mode=self.mode)
        baseline = state.get("baseline")
        if not isinstance(baseline, dict):
            baseline = {}
        done = self._is_micro_goal_done_for_text(micro, world, baseline, mode)
        if done:
            self._debug_micro_goal_done(world, baseline, micro, mode)
        return done

    def _debug_micro_goal_done(
        self,
        world: Dict[str, Any],
        baseline: Dict[str, Any],
        micro: str,
        mode: str,
    ) -> None:
        if self._micro_done_debug_emitted:
            return
        rule = self._lookup_rule(micro, mode)
        done_expr = rule.get("done") if rule else None
        related: Dict[str, Any] = {}
        if isinstance(done_expr, str):
            left, _, _ = parse_cond(done_expr)
            if left:
                related[left] = get_path(world, left)
        else:
            if mode == "FREEZE":
                related = {
                    "sobriety_days": world.get("sobriety_days", 0),
                    "victim_names_logged": world.get("victim_names_logged", 0),
                    "tips_checked": world.get("tips_checked", 0),
                }
            elif mode == "PURSUE":
                related = {
                    "evidence_score": world.get("evidence_score", 0),
                    "cams_fixed": world.get("cams_fixed", 0),
                    "partner_calls": world.get("partner_calls", 0),
                }
            elif mode == "FLEE":
                related = {
                    "suspicion.value": _current_suspicion(world),
                    "avoid_tags": world.get("avoid_tags", 0),
                }
            elif mode == "WITNESS":
                related = {"report_submitted": world.get("report_submitted", 0)}
        print(
            "[MICRO_DEBUG] completed micro="
            f"{micro!r} done={done_expr!r} baseline={baseline} related={related}"
        )
        self._micro_done_debug_emitted = True

    def apply_auto_step(self, world: Dict[str, Any]) -> Tuple[Optional[str], int]:
        if not isinstance(world, dict):
            return None, 5
        rule = self._lookup_rule(self._micro_cache.get(self.mode))
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

    def list_actions_for_mode(self, mode: str) -> List[Dict[str, Any]]:
        """Return unique actions available for a mode."""

        seen: set[str] = set()
        actions: List[Dict[str, Any]] = []
        for record in self._micro_bank(mode):
            action_id = record.get("action")
            if not action_id or action_id in seen:
                continue
            seen.add(action_id)
            try:
                time_min = int(record.get("time_min", 5))
            except (TypeError, ValueError):
                time_min = 5
            actions.append(
                {
                    "action": action_id,
                    "time_min": max(0, time_min),
                    "text": record.get("text"),
                }
            )
        return actions

    def list_actions_for_actor(
        self,
        actor_id: Optional[str],
        mode: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Return HUD actions for one mode when that mode is allowed for the actor."""

        current_mode = mode or self.mode
        actors = (self.goals_dict or {}).get("hud_actions", {}).get("actors", {})
        actor_modes = actors.get(actor_id) if actor_id else None
        if isinstance(actor_modes, str):
            actor_modes = [actor_modes]
        if not isinstance(actor_modes, list) or not actor_modes:
            return self.list_actions_for_mode(current_mode)

        if current_mode in actor_modes:
            return self.list_actions_for_mode(current_mode)

        return []

    def affordance_rules(self) -> Dict[str, Any]:
        """Return the affordances section from the pack YAML (goals_dict)."""
        return (self.goals_dict or {}).get("affordances", {})

    def progress_text(self, world: Dict[str, Any]) -> str:
        """Return a compact description of the current micro-goal progress."""

        micro = self._micro_cache.get(self.mode)
        rule = self._lookup_rule(micro, self.mode)
        if rule:
            done_expr = rule.get("done")
            if isinstance(done_expr, str):
                left, op, target = parse_cond(done_expr)
                if left and op and target is not None:
                    current = get_path(world, left)
                    if isinstance(current, (int, float)) and isinstance(target, (int, float)):
                        current_int = int(current)
                        target_int = int(target)
                        if op in (">", ">="):
                            return f"Micro: {micro} ({current_int}/{target_int})"
                        if op in ("<", "<="):
                            return f"Micro: {micro} (≤{target_int} | now {current_int})"
                        if op == "==":
                            return f"Micro: {micro} ({current_int}/{target_int})"
        return f"Micro: {micro or '(なし)'}"

    def recommended_action(self, world: Dict[str, Any]) -> Tuple[Optional[str], int, Optional[str]]:
        """Return (action_id, time_min, label) for the current micro-goal."""

        micro = self._micro_cache.get(self.mode)
        rule = self._lookup_rule(micro, self.mode)
        if rule:
            action_id = rule.get("action")
            if action_id:
                try:
                    time_min = int(rule.get("time_min", 5))
                except (TypeError, ValueError):
                    time_min = 5
                return action_id, max(0, time_min), micro
        return None, 0, micro

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

        try:
            bold, kind, guilt = derived_traits(world)
        except Exception:
            bold = kind = guilt = 0.0

        emo = world.get("emotion", {})
        r = emo.get("R", 127)
        g = emo.get("G", 127)
        b = emo.get("B", 127)

        flags = world.setdefault("flags", {})
        near_miss_fired = flags.get("near_miss_victim_family", False)

        if (
            self.mode == "PURSUE"
            and not near_miss_fired
            and r >= 80
            and b >= 160
        ):
            scene = {
                "id": "near_miss_victim_family",
                "intent": "NearMiss",
                "why_now": "high_bold_and_kind_in_pursue",
                "salience": 0.85,
                "mode": self.mode,
                "emotion_snapshot": {"R": r, "G": g, "B": b},
                "traits": {"boldness": bold, "kindness": kind, "guilt": guilt},
                "clock": world.get("clock", "Day1 00:00"),
                "meta": {"type": "emotion_trigger", "once": True},
            }
            scenes.append(scene)
            flags["near_miss_victim_family"] = True
            print(
                f"[Director] NearMiss scene injected (R={r}, B={b}, "
                f"bold={bold:.2f}, kind={kind:.2f})"
            )

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
