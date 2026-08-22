from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Iterable, Optional
from pathlib import Path

from src import action_registry
from src.action_definitions import actions as legacy_actions, get_action_spec
from src.game_command import ActionExecutionResult, ActionOutcome
from src.operation_runtime import (
    OperationRuntimeInput,
    OperationStartDirective,
    apply_action_outcome,
)
from src.rc_belief import project_memory_to_rc_belief
from src.rc_memory import project_transition_to_rc_memory
from src.location_graph import MOVE_ACTION_ID, move_to_location
from src.requirements_checker import RequirementsChecker
from src.simulation_utils import add_minutes, ensure_clock
from src.world import world_tick
from src.logger import log_action
from src.utility.config_loader import get_cfg, job_root_from_cfg
from datalab.registry.action_registry import normalize_action
from datalab.registry.scene_resolver import resolve
from datalab.emitters.scene_graph_emitter import emit_scene_graph
from datalab.emitters.emotion_emitter import emit_emotion_eval, summarize_why_now
from schemas.scene_graph import ObjectSpec, Pose


@dataclass(frozen=True)
class ActionExecutionOutcome:
    """Opt-in execution result that leaves the legacy return contract intact."""

    action_id: str
    executed: bool
    reason: str | None = None
    value: Any | None = None


@dataclass(frozen=True)
class _PostActionContext:
    """Opaque execution details consumed only by the compatibility finalizer."""

    action_id: str
    actor_id: str | None
    actor_obj: Any | None
    args: tuple[Any, ...]
    spec: Any
    world: dict | None
    source: str
    time_min_override: int | None
    clock_before: dict | None
    emotion_before: dict | None
    is_move: bool = False


def _action_result(
    action_id: str,
    *,
    return_outcome: bool,
    executed: bool,
    reason: str | None = None,
    value: Any | None = None,
) -> Any | ActionExecutionOutcome | None:
    if return_outcome:
        return ActionExecutionOutcome(
            action_id=action_id,
            executed=executed,
            reason=reason,
            value=value,
        )
    return value


@dataclass
class ActionPipeline:
    game_state: dict
    director: Any | None = None
    emit_director_scenes: Callable[[list[dict]], None] | None = None
    ui_refresh: Callable[[], None] | None = None
    hud_set_clock: Callable[[str], None] | None = None
    hud_set_microgoal: Callable[[str | None], None] | None = None
    advance_time: Callable[[int], None] | None = None

    def _resolve_world(self) -> dict | None:
        director_world = self.game_state.get("director_world")
        if isinstance(director_world, dict):
            return director_world
        world = self.game_state.get("world")
        if isinstance(world, dict):
            return world
        return None

    def _resolve_actor_id(self, actor_obj: Any | None) -> str | None:
        actor_name = getattr(actor_obj, "name", None)
        if isinstance(actor_name, str) and actor_name:
            return actor_name
        active = self.game_state.get("active_char")
        active_name = getattr(active, "name", None)
        if isinstance(active_name, str) and active_name:
            return active_name
        return None

    def _operation_start_directive_from_spec(
        self,
        spec: Any | None,
    ) -> OperationStartDirective | None:
        if spec is None or not getattr(spec, "starts_operation", False):
            return None
        return OperationStartDirective(
            operation_type=getattr(spec, "operation_type", None),
            operation_label=(
                getattr(spec, "operation_label", None)
                or getattr(spec, "label", None)
            ),
            operation_phase=getattr(spec, "operation_phase", None),
            operation_mini_goal=getattr(spec, "operation_mini_goal", None),
        )

    def _advance_time(self, world: dict | None, minutes: int) -> None:
        if minutes <= 0:
            return
        if self.advance_time is not None:
            self.advance_time(minutes)
            return
        if world is None:
            return
        if world.get("t_min") is not None or isinstance(world.get("clock"), dict):
            if self.game_state.get("world") is world:
                world_tick(self.game_state, dt=minutes)
            else:
                temp_state = {"world": world, "time_of_day": self.game_state.get("time_of_day")}
                world_tick(temp_state, dt=minutes)
                if "time_of_day" in temp_state:
                    self.game_state["time_of_day"] = temp_state["time_of_day"]
        else:
            ensure_clock(world)
            add_minutes(world, minutes)

    def _normalize_clock(self, clock: Any) -> dict:
        """Convert clock to dict format: {"day": int, "hour": int, "minute": int}"""
        if isinstance(clock, dict):
            day = clock.get("day")
            hour = clock.get("hour")
            minute = clock.get("minute")
            if day is not None and hour is not None and minute is not None:
                return {"day": int(day), "hour": int(hour), "minute": int(minute)}
        elif isinstance(clock, str):
            # Parse "Day1 00:00" format
            try:
                day_part, time_part = clock.split(maxsplit=1)
                day = int(day_part.replace("Day", ""))
                hour_str, minute_str = time_part.split(":", maxsplit=1)
                hour = int(hour_str)
                minute = int(minute_str)
                return {"day": max(day, 1), "hour": max(hour, 0), "minute": max(minute, 0)}
            except (ValueError, AttributeError):
                pass
        # Fallback to default
        return {"day": 1, "hour": 0, "minute": 0}

    def _emotion_snapshot(self, world: dict | None, actor_id: str | None) -> dict:
        emotions_by_actor = self.game_state.get("emotions_by_actor", {})
        if isinstance(emotions_by_actor, dict) and actor_id:
            actor_emotion = emotions_by_actor.get(actor_id)
            if isinstance(actor_emotion, dict):
                return actor_emotion.copy()
        if isinstance(world, dict) and isinstance(world.get("emotion"), dict):
            return world.get("emotion", {}).copy()
        return {}

    def _record_action_log(
        self,
        *,
        source: str,
        actor_id: str | None,
        action_id: str,
        args: list,
        time_min: int,
        clock_before: dict | None,
        emotion_before: dict | None,
        microgoal: str | None,
    ) -> None:
        world = self._resolve_world()
        if world is None:
            return
        log_action(
            source=source,
            actor_id=actor_id,
            action_id=action_id,
            args=args,
            time_min=time_min,
            clock_before=clock_before,
            clock_after=self._normalize_clock(world.get("clock")),
            emotion_before=emotion_before,
            emotion_after=self._emotion_snapshot(world, actor_id),
            mode=self.director.mode if self.director is not None else None,
            microgoal=microgoal,
        )

    def _build_ctx(self, actor_obj: Any, action: str, args: list, raw_key: str | None = None) -> dict:
        """Build context for scene resolution"""
        target_name = (args[0] if args else self.game_state.get("current_target"))
        labels = set()
        if target_name and hasattr(actor_obj, "get_labels_from"):
            party = self.game_state.get("party", {})
            tgt = party.get(target_name)
            if tgt and hasattr(tgt, "relationship_tags_from"):
                labels = tgt.relationship_tags_from.get(actor_obj.name, set())

        r, g, b = getattr(actor_obj, "emotion_color", (127, 127, 255))

        return {
            "actor": actor_obj.name,
            "raw_key": (raw_key if raw_key is not None else action),
            "action": action,
            "args": args,
            "location": self.game_state.get("current_location", "どこか"),
            "time": self.game_state.get("time_of_day", "night"),
            "relation_labels": labels,
            "emotion": {"red": r/255.0, "green": g/255.0, "blue": b/255.0},
        }

    def _guess_materials_from_player(self, actor_obj: Any, action: str) -> list:
        """Guess materials from player equipment"""
        mats = []
        w = getattr(actor_obj, "equipped_weapon", None)
        wtype = w.get("weapon_type") if isinstance(w, dict) else getattr(w, "weapon_type", None)
        if action in ("swing_sword", "attack") and wtype == "sword":
            mats += ["steel_brushed", "leather_soft"]
        return mats

    def _emit_scene_graph(self, actor_obj: Any, action_id: str, args: list, world: dict, micro_goal: str | None, source: str = "UI") -> None:
        """Emit scene graph if enabled in config and passes filters"""
        try:
            cfg = get_cfg()
            datalab_cfg = cfg.get("datalab", {})
            
            # A) emit_scene_graph が true
            if not datalab_cfg.get("emit_scene_graph", True):
                return
            
            # B) source が emit_sources に含まれる
            emit_sources = datalab_cfg.get("emit_sources", ["GUI", "HUD", "CLI"])
            if not isinstance(emit_sources, list):
                emit_sources = ["GUI", "HUD", "CLI"]
            if source not in emit_sources:
                return
            
            # C) action_id が emit_exclude_actions に含まれない
            emit_exclude_actions = datalab_cfg.get("emit_exclude_actions", ["switch_character"])
            if not isinstance(emit_exclude_actions, list):
                emit_exclude_actions = ["switch_character"]
            if action_id in emit_exclude_actions:
                return
            
            # Convert args to list of strings
            args_str = [str(arg) for arg in args] if args else []
            
            job_root = Path(job_root_from_cfg())
            job_root.mkdir(parents=True, exist_ok=True)
            
            # emotion eval（emotion_eval_sources でフィルタリング）
            emotion_eval_sources = datalab_cfg.get("emotion_eval_sources", emit_sources)
            if not isinstance(emotion_eval_sources, list):
                emotion_eval_sources = emit_sources
            if source in emotion_eval_sources:
                signals_doc = emit_emotion_eval(job_root, actor_obj=actor_obj, game_state=self.game_state)
            else:
                # emotion_eval を出力しない場合は、ダミーの signals_doc を作成
                signals_doc = {"signals": {}}
            
            thresholds = datalab_cfg.get("emit_thresholds", {})
            decision = summarize_why_now(signals_doc.get("signals", {}), thresholds)
            
            # D) 既存 emit_policy 判定を通る
            policy = datalab_cfg.get("emit_policy", "always")
            emit_ok = (policy == "always") or (policy == "threshold" and decision["ok"])
            why_now_text = f'{decision["text"]} | policy={policy} {"emit" if emit_ok else "skip"}'
            
            if not emit_ok:
                return
            
            # scene resolution
            action = normalize_action(action_id, args_str)
            ctx = self._build_ctx(actor_obj, action, args_str, raw_key=action_id)
            picked = resolve(ctx)
            
            # objects conversion
            objs = []
            for o in (picked.get("objects") or []):
                pose = o.get("pose")
                pose_obj = Pose(**pose) if isinstance(pose, dict) else None
                
                kwargs = dict(
                    name=o.get("name", "{actor}").format(actor=actor_obj.name),
                    category=o.get("category", "character"),
                    base_prompt=o.get("base_prompt", ""),
                    action=o.get("action", action),
                    pose=pose_obj,
                )
                
                mats = o.get("materials_hint", None)
                if mats is not None:
                    if isinstance(mats, (list, tuple, set)):
                        kwargs["materials_hint"] = list(mats)
                    else:
                        kwargs["materials_hint"] = [mats]
                
                sc = o.get("scale", None)
                if isinstance(sc, dict):
                    kwargs["scale"] = sc
                
                objs.append(ObjectSpec(**kwargs))
            
            fallback_mats = self._guess_materials_from_player(actor_obj, action)
            fallback_kwargs = dict(
                name=f"{actor_obj.name}",
                category="character",
                base_prompt="default character",
                action=action,
            )
            if fallback_mats:
                fallback_kwargs["materials_hint"] = fallback_mats
            
            objects = objs if objs else [ObjectSpec(**fallback_kwargs)]
            
            # emit scene graph（source を渡して seedledger の制御を可能にする）
            emit_scene_graph(
                job_root=job_root,
                theme=picked.get("theme", f"{ctx['location']}での{action}"),
                background=picked.get("background", "generic scene"),
                objects=objects,
                loras=picked.get("loras", []),
                why_now=why_now_text,
                profile=cfg.get("profile", "prod"),
                actor=actor_obj.name,
                action=action,
                args=args_str,
                source=source,
                extra_meta={
                    "camera": picked.get("camera"),
                    "lighting": picked.get("lighting"),
                    "tpo_ctx": {
                        "location": ctx["location"],
                        "time": ctx["time"],
                        "relation_labels": sorted(list(ctx["relation_labels"])),
                    },
                },
            )
        except Exception as e:
            # エラーが発生してもアクション実行は続行
            print(f"[ActionPipeline] scene_graph emit failed: {e}")

    def execute_action(
        self,
        action_id: str,
        actor_obj: Any | None = None,
        actor_id: str | None = None,
        args: Iterable[Any] | None = None,
        time_min_override: int | None = None,
        source: str = "UI",
    ) -> ActionExecutionResult:
        """Execute only the Action stage and return its follow-up envelope."""

        resolved_actor_id = (
            actor_id
            if isinstance(actor_id, str) and actor_id
            else self._resolve_actor_id(actor_obj)
        )
        if not action_id:
            return ActionExecutionResult(
                outcome=ActionOutcome(
                    action_id="",
                    actor_id=resolved_actor_id,
                    executed=False,
                    effects_committed=False,
                    source=source,
                    reason="missing_action_id",
                )
            )

        world = self._resolve_world()
        spec = get_action_spec(action_id)
        if spec is None:
            return ActionExecutionResult(
                outcome=ActionOutcome(
                    action_id=action_id,
                    actor_id=resolved_actor_id,
                    executed=False,
                    effects_committed=False,
                    source=source,
                    reason="missing_action_spec",
                )
            )

        arg_list = list(args) if args else []
        result: Any | None = None
        clock_before = None
        emotion_before = None
        if world is not None:
            clock_before = self._normalize_clock(world.get("clock"))
            emotions_by_actor = self.game_state.get("emotions_by_actor", {})
            if resolved_actor_id and resolved_actor_id in emotions_by_actor:
                emotion_before = emotions_by_actor[resolved_actor_id].copy()
            else:
                emotion_before = (
                    world.get("emotion", {}).copy()
                    if isinstance(world.get("emotion"), dict)
                    else {}
                )

        if action_id == MOVE_ACTION_ID:
            destination = (
                arg_list[0]
                if arg_list and isinstance(arg_list[0], str)
                else None
            )
            ok, move_result = move_to_location(
                world,
                self.game_state,
                resolved_actor_id,
                destination,
            )
            if not ok:
                print(
                    "[ActionPipeline] move_to_location rejected: "
                    f"{move_result.get('error')}"
                )
                return ActionExecutionResult(
                    outcome=ActionOutcome(
                        action_id=action_id,
                        actor_id=resolved_actor_id,
                        executed=False,
                        effects_committed=False,
                        source=source,
                        reason="move_rejected",
                    )
                )
            if actor_obj is not None and hasattr(actor_obj, "location"):
                actor_obj.location = destination
            return ActionExecutionResult(
                outcome=ActionOutcome(
                    action_id=action_id,
                    actor_id=resolved_actor_id,
                    executed=True,
                    effects_committed=True,
                    source=source,
                    value=move_result,
                ),
                operation_input=None,
                post_action_context=_PostActionContext(
                    action_id=action_id,
                    actor_id=resolved_actor_id,
                    actor_obj=actor_obj,
                    args=tuple(arg_list),
                    spec=spec,
                    world=world,
                    source=source,
                    time_min_override=time_min_override,
                    clock_before=clock_before,
                    emotion_before=emotion_before,
                    is_move=True,
                ),
            )

        if action_id in legacy_actions and actor_obj is not None:
            if spec.requirements:
                checker = RequirementsChecker(self.game_state, actor_obj)
                if not checker.check_all(spec.requirements, args=arg_list):
                    return ActionExecutionResult(
                        outcome=ActionOutcome(
                            action_id=action_id,
                            actor_id=resolved_actor_id,
                            executed=False,
                            effects_committed=False,
                            source=source,
                            reason="requirements_failed",
                        )
                    )
            if spec.function:
                result = spec.function(actor_obj, self.game_state, *arg_list)
        else:
            if world is None:
                return ActionExecutionResult(
                    outcome=ActionOutcome(
                        action_id=action_id,
                        actor_id=resolved_actor_id,
                        executed=False,
                        effects_committed=False,
                        source=source,
                        reason="not_executed",
                    )
                )
            if world is not None:
                if self.director is not None:
                    can_execute_tpo = getattr(
                        self.director,
                        "can_execute_tpo_hud_action",
                        None,
                    )
                    if callable(can_execute_tpo) and not can_execute_tpo(
                        world,
                        self.game_state,
                        resolved_actor_id,
                        action_id,
                        source=source,
                        action_layer=getattr(spec, "action_layer", None),
                    ):
                        print(
                            "[ActionPipeline] TPO HUD action rejected at execution gate: "
                            f"actor={resolved_actor_id} action={action_id}"
                        )
                        return ActionExecutionResult(
                            outcome=ActionOutcome(
                                action_id=action_id,
                                actor_id=resolved_actor_id,
                                executed=False,
                                effects_committed=False,
                                source=source,
                                reason="tpo_gate_failed",
                            )
                        )
                if hasattr(action_registry, "execute_action_core"):
                    if action_registry.execute_action_core(world, action_id) is not True:
                        return ActionExecutionResult(
                            outcome=ActionOutcome(
                                action_id=action_id,
                                actor_id=resolved_actor_id,
                                executed=False,
                                effects_committed=False,
                                source=source,
                                reason="core_requirements_failed",
                            )
                        )
                else:  # TODO: implement execute_action_core in src.action_registry
                    return ActionExecutionResult(
                        outcome=ActionOutcome(
                            action_id=action_id,
                            actor_id=resolved_actor_id,
                            executed=False,
                            effects_committed=False,
                            source=source,
                            reason="core_executor_missing",
                        )
                    )

        operation_input = OperationRuntimeInput(
            action_id=action_id,
            actor_id=resolved_actor_id,
            executed=True,
            effects_committed=True,
            source=source,
            operation_start_directive=self._operation_start_directive_from_spec(spec),
        )
        return ActionExecutionResult(
            outcome=ActionOutcome(
                action_id=action_id,
                actor_id=resolved_actor_id,
                executed=True,
                effects_committed=True,
                source=source,
                value=result,
            ),
            operation_input=operation_input,
            post_action_context=_PostActionContext(
                action_id=action_id,
                actor_id=resolved_actor_id,
                actor_obj=actor_obj,
                args=tuple(arg_list),
                spec=spec,
                world=world,
                source=source,
                time_min_override=time_min_override,
                clock_before=clock_before,
                emotion_before=emotion_before,
            ),
        )

    def finalize_post_action(self, execution_result: ActionExecutionResult) -> None:
        """Run the existing post-Action lifecycle once, without presentation."""

        outcome = execution_result.outcome
        context = execution_result.post_action_context
        if (
            not outcome.executed
            or not outcome.effects_committed
            or not isinstance(context, _PostActionContext)
        ):
            return

        action_id = context.action_id
        actor_id = context.actor_id
        actor_obj = context.actor_obj
        arg_list = list(context.args)
        spec = context.spec
        world = context.world
        source = context.source
        clock_before = context.clock_before
        emotion_before = context.emotion_before

        if context.is_move:
            self.game_state["hud_cache_rev"] = (
                self.game_state.get("hud_cache_rev", 0) + 1
            )
            self._record_action_log(
                source=source,
                actor_id=actor_id,
                action_id=action_id,
                args=arg_list,
                time_min=0,
                clock_before=clock_before,
                emotion_before=emotion_before,
                microgoal=self.game_state.get("director_micro_goal"),
            )
            return

        dt = (
            context.time_min_override
            if context.time_min_override is not None
            else spec.time_min
        )
        try:
            dt_value = int(dt)
        except (TypeError, ValueError):
            dt_value = 0
        if world is not None and dt_value > 0:
            self._advance_time(world, dt_value)
            # レバーB: RC実行時に入力待ち中なら累積時間を記録
            if source == "RC_AI" and self.game_state.get("input_pending"):
                prev = self.game_state.get("_rc_minutes_advanced_while_pending", 0)
                self.game_state["_rc_minutes_advanced_while_pending"] = prev + dt_value
            # プレイヤー実行時は累積をリセット
            if source in ("GUI", "CLI", "HUD"):
                self.game_state["_rc_minutes_advanced_while_pending"] = 0

        if action_id != "switch_character":
            self.game_state["hud_cache_rev"] = self.game_state.get("hud_cache_rev", 0) + 1

        if world is not None:
            action_registry.ensure_emotion(world)
            # set_emotion/switch_characterはemotion_colorを自前で管理するため、delta適用をスキップ
            if action_id not in ("set_emotion", "switch_character"):
                # SoT(emotions_by_actor) → world["emotion"]へロードしてからdelta適用
                _eba = self.game_state.get("emotions_by_actor", {})
                _aname = actor_obj.name if actor_obj is not None and hasattr(actor_obj, "name") else None
                if _aname and _aname in _eba:
                    _src = _eba[_aname]
                    world["emotion"]["R"] = _src.get("R", 127)
                    world["emotion"]["G"] = _src.get("G", 127)
                    world["emotion"]["B"] = _src.get("B", 127)
                action_registry.apply_emotion_delta(world, action_id)
                emo = world.get("emotion")
                if isinstance(emo, dict) and actor_obj is not None and hasattr(actor_obj, "emotion_color"):
                    actor_obj.emotion_color = (
                        int(emo.get("R", 127)),
                        int(emo.get("G", 127)),
                        int(emo.get("B", 127)),
                    )
                    # actor別emotionも同期
                    emotions_by_actor = self.game_state.get("emotions_by_actor")
                    if emotions_by_actor is not None and hasattr(actor_obj, "name"):
                        actor_name = actor_obj.name
                        emotions_by_actor.setdefault(actor_name, {})
                        emotions_by_actor[actor_name]["R"] = actor_obj.emotion_color[0]
                        emotions_by_actor[actor_name]["G"] = actor_obj.emotion_color[1]
                        emotions_by_actor[actor_name]["B"] = actor_obj.emotion_color[2]

            # world["emotion"]を現在のアクティブactorのSoTと常に同期
            # director.tick / rc_ai / emotion_traits がworld["emotion"]を参照するため
            _active = self.game_state.get("active_char")
            _eba_sync = self.game_state.get("emotions_by_actor", {})
            _active_name = _active.name if _active is not None and hasattr(_active, "name") else None
            if _active_name and _active_name in _eba_sync:
                _s = _eba_sync[_active_name]
                world.setdefault("emotion", {})
                world["emotion"]["R"] = _s.get("R", 127)
                world["emotion"]["G"] = _s.get("G", 127)
                world["emotion"]["B"] = _s.get("B", 127)

        scenes = None
        micro_goal = None
        if self.director is not None and world is not None:
            scenes = self.director.tick(world)
            if scenes and self.emit_director_scenes is not None:
                self.emit_director_scenes(scenes)

            active_actor = self.game_state.get("active_char")
            micro_actor_id = (
                active_actor.name
                if active_actor is not None and hasattr(active_actor, "name")
                else None
            )
            get_for_actor = getattr(self.director, "get_micro_goal_for_actor", None)
            is_done_for_actor = getattr(self.director, "is_micro_goal_done_for_actor", None)
            clear_for_actor = getattr(self.director, "clear_micro_goal_for_actor", None)
            if callable(get_for_actor):
                micro_goal = get_for_actor(world, micro_actor_id, reroll=False)
            else:
                micro_goal = self.director.get_micro_goal(world, reroll=False)
            micro_done = (
                is_done_for_actor(world, micro_actor_id)
                if callable(is_done_for_actor)
                else self.director.is_micro_goal_done(world)
            )
            if action_id != "switch_character" and micro_done:
                if callable(clear_for_actor):
                    clear_for_actor(world, micro_actor_id)
                    micro_goal = get_for_actor(world, micro_actor_id, reroll=True)
                else:
                    self.director.clear_micro_goal()
                    micro_goal = self.director.get_micro_goal(world, reroll=True)
            self.game_state["director_micro_goal"] = micro_goal
            self.game_state["director_micro_goal_actor_id"] = micro_actor_id

        # Affordance discovery evaluation + opportunity spent tracking
        if self.director is not None and world is not None:
            from src.affordance_bridge import evaluate_discoveries, mark_opportunity_spent
            aff_rules = self.director.affordance_rules()
            disc_rules = aff_rules.get("discovery_rules", [])
            if disc_rules:
                new_discoveries = evaluate_discoveries(
                    world, self.game_state, action_id, disc_rules,
                    mode=self.director.mode,
                    actor_id=self._resolve_actor_id(actor_obj),
                )
                if new_discoveries:
                    self.game_state["hud_cache_rev"] = self.game_state.get("hud_cache_rev", 0) + 1
                    for nd in new_discoveries:
                        print(f"[Affordance] discovered: {nd}")
            # opportunity spent tracking
            mark_opportunity_spent(world, action_id)

        # ログ出力（director update の後、UI refresh の前）
        if world is not None:
            self._record_action_log(
                source=source,
                actor_id=actor_id,
                action_id=action_id,
                args=arg_list,
                time_min=dt_value,
                clock_before=clock_before,
                emotion_before=emotion_before,
                microgoal=micro_goal,
            )

            # RO recommendation (player sources only)
            if source in ("GUI", "HUD", "CLI") and self.director is not None:
                try:
                    from src.ro.ro import recommend as ro_recommend
                    candidates = [
                        r.get("action") or r.get("id") or r.get("action_id")
                        for r in self.director.list_actions_for_mode(self.director.mode)
                        if r.get("action") or r.get("id") or r.get("action_id")
                    ]
                    mg_action, _, mg_text = self.director.recommended_action(world)
                    rec = ro_recommend(actor_id, candidates, mg_action, mg_text)
                    if rec is not None:
                        self.game_state["ro_recommendation"] = rec
                except Exception:
                    pass  # RO failure must never block gameplay

            # scene_graph emit（設定ONのときだけ、フィルタリングは _emit_scene_graph 内で実施）
            cfg = get_cfg()
            emit_enabled = cfg.get("datalab", {}).get("emit_scene_graph", True)
            if emit_enabled and actor_obj is not None and hasattr(actor_obj, "name"):
                self._emit_scene_graph(actor_obj, action_id, arg_list, world, micro_goal, source)

    def refresh_presentation(self, outcome: ActionOutcome) -> None:
        """Refresh legacy Python presentation after command orchestration."""

        if not outcome.executed:
            return
        if outcome.action_id == MOVE_ACTION_ID:
            if self.ui_refresh is not None:
                self.ui_refresh()
            return

        world = self._resolve_world()
        if world is not None and self.hud_set_clock is not None:
            clock_label = world.get("clock")
            if isinstance(clock_label, dict):
                day = clock_label.get("day")
                hour = clock_label.get("hour")
                minute = clock_label.get("minute")
                if day is not None and hour is not None and minute is not None:
                    self.hud_set_clock(f"Day{day} {hour:02d}:{minute:02d}")
                else:
                    label = clock_label.get("label")
                    if isinstance(label, str):
                        self.hud_set_clock(label)
                    else:
                        ensure_clock(world)
                        refreshed = world.get("clock")
                        if isinstance(refreshed, str):
                            self.hud_set_clock(refreshed)
            elif isinstance(clock_label, str):
                self.hud_set_clock(clock_label)
            else:
                ensure_clock(world)
                refreshed = world.get("clock")
                if isinstance(refreshed, str):
                    self.hud_set_clock(refreshed)
        if self.hud_set_microgoal is not None and self.ui_refresh is None:
            micro_text = self.game_state.get("director_micro_goal")
            micro_actor_id = self.game_state.get("director_micro_goal_actor_id")
            display = (
                f"MicroGoal({micro_actor_id}): {micro_text}"
                if micro_actor_id
                else micro_text
            )
            self.hud_set_microgoal(display)
        if self.ui_refresh is not None:
            self.ui_refresh()

    def request_action(
        self,
        action_id: str,
        actor_obj: Any | None = None,
        args: Iterable[Any] | None = None,
        time_min_override: int | None = None,
        source: str = "UI",
        return_outcome: bool = False,
    ) -> Any | ActionExecutionOutcome | None:
        """Legacy full-lifecycle entry point retained for existing callers."""

        execution_result = self.execute_action(
            action_id,
            actor_obj=actor_obj,
            args=args,
            time_min_override=time_min_override,
            source=source,
        )
        outcome = execution_result.outcome
        if not outcome.executed or not outcome.effects_committed:
            return _action_result(
                outcome.action_id,
                return_outcome=return_outcome,
                executed=False,
                reason=outcome.reason,
                value=outcome.value,
            )

        world = self._resolve_world()
        committed_transitions = []
        if execution_result.operation_input is not None:
            committed_transitions = apply_action_outcome(
                world,
                self.game_state,
                execution_result.operation_input,
            )

        for transition_event in committed_transitions:
            memory = None
            try:
                memory = project_transition_to_rc_memory(world, transition_event)
            except Exception as exc:
                print(f"[RC Memory] live projection failed: {exc}")
            if memory is not None:
                try:
                    project_memory_to_rc_belief(world, memory)
                except Exception as exc:
                    print(f"[RC Belief] live projection failed: {exc}")

        self.finalize_post_action(execution_result)
        self.refresh_presentation(outcome)
        return _action_result(
            outcome.action_id,
            return_outcome=return_outcome,
            executed=outcome.executed,
            reason=outcome.reason,
            value=outcome.value,
        )
