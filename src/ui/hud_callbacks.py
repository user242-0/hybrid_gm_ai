"""HUD コールバック関数群を管理するクラス"""

from __future__ import annotations

import time
from typing import TYPE_CHECKING, Any, Callable

from src.utility.config_loader import is_hud_debug_enabled

if TYPE_CHECKING:
    from src.game_context import GameContext


class HUDCallbacks:
    """
    DirectorHUD のコールバック関数を一元管理するクラス。

    simulation.py から HUD 関連のロジックを分離し、
    コードの見通しを良くする。
    """

    def __init__(
        self,
        ctx: GameContext,
        *,
        get_action_spec: Callable[[str], Any],
        pick_action: Callable,
        dispatch_action: Callable,
        ui_show_micro: Callable,
        director_clock_string: Callable[[dict | None], str],
        save_director_world: Callable[[dict], None],
        load_director_world: Callable[[dict | None], dict | None],
        ensure_clock: Callable[[dict], None],
        request_auto_step: Callable[[], None],
    ) -> None:
        self.ctx = ctx
        self._get_action_spec = get_action_spec
        self._pick_action = pick_action
        self._dispatch_action = dispatch_action
        self._ui_show_micro = ui_show_micro
        self._director_clock_string = director_clock_string
        self._save_director_world = save_director_world
        self._load_director_world = load_director_world
        self._ensure_clock = ensure_clock
        self._request_auto_step = request_auto_step

    def refresh_hud(self) -> None:
        """HUD の表示を更新する"""
        ctx = self.ctx
        if ctx.director_hud is None:
            return
        if ctx.director_world is None:
            ctx.director_hud.set_progress(None)
            ctx.director_hud.set_recommended(None, enabled=False)
            ctx.director_hud.set_actions([])
            ctx.game_state["hud_cached_progress"] = None
            ctx.game_state["hud_cached_actions"] = []
            ctx.game_state["hud_cached_recommended"] = {
                "label": None,
                "enabled": False,
                "action_id": None,
                "minutes": None,
            }
            ctx.game_state["hud_last_rendered_rev"] = ctx.game_state.get("hud_cache_rev", 0)
            return

        cache_rev = ctx.game_state.get("hud_cache_rev", 0)
        last_rendered_rev = ctx.game_state.get("hud_last_rendered_rev", -1)
        if cache_rev != last_rendered_rev:
            if is_hud_debug_enabled():
                print(f"[HUD_DEBUG] recompute rev={cache_rev} last={last_rendered_rev}")
            progress_text = ctx.director.progress_text(ctx.director_world)
            ctx.game_state["hud_cached_progress"] = progress_text

            rec_action, rec_minutes, rec_label = ctx.director.recommended_action(ctx.director_world)
            if is_hud_debug_enabled():
                print(f"[HUD_DEBUG] rec_action={rec_action} minutes={rec_minutes} label={rec_label}")
            if isinstance(ctx.director_world, dict):
                if rec_action:
                    ctx.director_world["_recommended_action_id"] = rec_action
                else:
                    ctx.director_world.pop("_recommended_action_id", None)
            if rec_action:
                label = f"★ {rec_label or rec_action} (+{rec_minutes}m)"
                recommended = {
                    "label": label,
                    "enabled": True,
                    "action_id": rec_action,
                    "minutes": rec_minutes,
                }
            else:
                recommended = {
                    "label": "(Recommended)",
                    "enabled": False,
                    "action_id": None,
                    "minutes": None,
                }
            ctx.game_state["hud_cached_recommended"] = recommended

            ctx.current_actions.clear()
            for record in ctx.director.list_actions_for_mode(ctx.director.mode):
                action_id = None
                label = None
                minutes = None
                if isinstance(record, dict):
                    action_id = record.get("action") or record.get("id") or record.get("action_id")
                    label = record.get("text") or record.get("label")
                    raw_time = record.get("time_min")
                    if raw_time is not None:
                        try:
                            minutes = int(raw_time)
                        except (TypeError, ValueError):
                            pass
                if not action_id:
                    continue
                spec = self._get_action_spec(action_id)
                if not label:
                    label = spec.label if spec else action_id
                # time_min: record優先 → spec優先 → Noneのまま（ActionPipelineで再取得）
                if minutes is None and spec and spec.time_min:
                    minutes = spec.time_min
                ctx.current_actions.append((action_id, label, minutes))
            ctx.current_actions.sort(key=lambda item: item[0])
            if is_hud_debug_enabled():
                print("[HUD_DEBUG] actions=", [aid for (aid, _, _) in ctx.current_actions])
            ctx.game_state["hud_cached_actions"] = ctx.current_actions.copy()
            ctx.game_state["hud_last_rendered_rev"] = cache_rev

        ctx.director_hud.set_progress(ctx.game_state.get("hud_cached_progress"))
        recommended = ctx.game_state.get("hud_cached_recommended") or {}
        ctx.director_hud.set_recommended(
            recommended.get("label"),
            enabled=bool(recommended.get("enabled")),
        )
        cached_actions = ctx.game_state.get("hud_cached_actions") or []
        ctx.current_actions[:] = list(cached_actions)
        ctx.director_hud.set_actions(list(cached_actions))

    def hud_adjust_value(self, path: list, delta: float, *, minimum=None, maximum=None) -> None:
        """HUD から値を調整する"""
        node = self.ctx.director_world
        if node is None:
            return
        for key in path[:-1]:
            if not isinstance(node, dict):
                return
            node = node.get(key)
        if not isinstance(node, dict):
            return
        leaf_key = path[-1]
        value = node.get(leaf_key, 0)
        if not isinstance(value, (int, float)):
            return
        new_value = value + delta
        if minimum is not None:
            new_value = max(minimum, new_value)
        if maximum is not None:
            new_value = min(maximum, new_value)
        node[leaf_key] = new_value

    def on_show_micro(self) -> None:
        """マイクロゴールを表示する"""
        ctx = self.ctx
        if ctx.director_world is None:
            return
        micro = ctx.director.get_micro_goal(ctx.director_world, reroll=False)
        self._ui_show_micro(micro, ctx.game_state)
        micro_text = micro or "(MicroGoal なし)"
        print(f"[UI] MicroGoal: {micro_text}")

    def on_reroll(self) -> None:
        """マイクロゴールを再抽選する"""
        ctx = self.ctx
        if ctx.director_world is None:
            return
        micro = ctx.director.get_micro_goal(ctx.director_world, reroll=True)
        self._ui_show_micro(micro, ctx.game_state)
        micro_text = micro or "(MicroGoal なし)"
        print(f"[UI] MicroGoal (reroll): {micro_text}")
        self.refresh_hud()

    def ai_step_once(self) -> None:
        """AI による1ステップ実行"""
        ctx = self.ctx
        if ctx.director_world is None:
            return

        actions = ctx.director.list_actions_for_mode(ctx.director.mode) or []
        micro = ctx.director.get_micro_goal(ctx.director_world, reroll=False)
        action_id, tmin, reason = self._pick_action(ctx.director_world, ctx.director.mode, actions, micro)

        if not action_id:
            ctx.director.clear_micro_goal()
            self.on_show_micro()
            self.refresh_hud()
            print("[RC_AI] no action; rerolled micro")
            return

        emo_before = ctx.director_world.get("emotion", {}).copy()
        self._dispatch_action(
            action_id,
            actor_obj=ctx.game_state.get("active_char"),
            args=[],
            time_min_override=tmin,
            source="RC_AI",
        )
        ctx.game_state["last_auto_ts"] = time.monotonic()
        if isinstance(ctx.director_world, dict):
            ctx.director_world["_last_action_id"] = action_id

        emo_after = ctx.director_world.get("emotion", {})
        print(
            f"[RC_AI] picked={action_id} reason={reason} "
            f"emotion R:{emo_before.get('R')}→{emo_after.get('R')} "
            f"G:{emo_before.get('G')}→{emo_after.get('G')} "
            f"B:{emo_before.get('B')}→{emo_after.get('B')}"
        )
        clock_label = self._director_clock_string(ctx.director_world)
        if ctx.director_hud is not None:
            ctx.director_hud.set_clock(clock_label)
        non_progress_actions = {"switch_character", "感情を設定する"}
        if action_id not in non_progress_actions and ctx.director.is_micro_goal_done(ctx.director_world):
            ctx.director.clear_micro_goal()
            next_micro = ctx.director.get_micro_goal(ctx.director_world, reroll=False)
            if next_micro and next_micro != "(MicroGoal なし)":
                print("[MICRO] completed -> next")
        self.on_show_micro()
        self.refresh_hud()

    def set_auto(self, enabled: bool) -> None:
        """自動ステップモードを切り替える"""
        self.ctx.set_auto(enabled)

    def maybe_run_auto(self) -> None:
        """自動ステップを実行（条件を満たす場合）"""
        ctx = self.ctx
        if ctx.game_state.get("auto_step_pending"):
            if ctx.director_world is None:
                ctx.game_state["auto_step_pending"] = False
                return
            self.ai_step_once()
            ctx.game_state["auto_step_pending"] = False
            return
        if ctx.director_world is None:
            return
        if not ctx.auto_enabled:
            return
        last_auto_ts = ctx.game_state.get("last_auto_ts", 0.0)
        if time.monotonic() - last_auto_ts < ctx.AUTO_STEP_INTERVAL_SECONDS:
            return
        self.ai_step_once()

    def on_save(self) -> None:
        """ワールド状態を保存する"""
        if self.ctx.director_world is None:
            return
        self._save_director_world(self.ctx.director_world)
        print("[SAVE] world saved")

    def on_load(self) -> None:
        """ワールド状態を読み込む"""
        ctx = self.ctx
        loaded = self._load_director_world(ctx.director_world)
        if loaded is None:
            return
        ctx.director_world = loaded
        self._ensure_clock(ctx.director_world)
        if isinstance(ctx.director_world, dict):
            ctx.director_world["reload_epoch"] = ctx.director_world.get("reload_epoch", 0) + 1
        ctx.game_state["director_world"] = ctx.director_world
        ctx.game_state["world"] = ctx.director_world
        ctx.bump_hud_cache_rev(reason="world_load")
        if ctx.director_hud is not None:
            ctx.director_hud.set_clock(self._director_clock_string(ctx.director_world))
        ctx.director.clear_micro_goal()
        self.on_show_micro()
        reload_epoch = (
            ctx.director_world.get("reload_epoch") if isinstance(ctx.director_world, dict) else None
        )
        print(f"[LOAD] world loaded; reload_epoch={reload_epoch}")

    def on_action_select(self, which: object) -> None:
        """HUD からアクションを選択する"""
        ctx = self.ctx
        if ctx.director_world is None:
            return
        action_id = None
        time_min = None
        if which == "__recommended__":
            recommended = ctx.game_state.get("hud_cached_recommended") or {}
            action_id = recommended.get("action_id")
            time_min = recommended.get("minutes")
        elif isinstance(which, int) and 0 <= which < len(ctx.current_actions):
            action_id, _, time_min = ctx.current_actions[which]
        if not action_id or not isinstance(action_id, str) or not action_id.strip():
            print(f"[HUD] invalid action_id={action_id!r} (empty)")
            return
        if any(not char.isascii() for char in action_id):
            print(f"[HUD] invalid action_id={action_id!r} (non-ascii)")
            return
        spec = self._get_action_spec(action_id)
        print(
            f"[HUD] which={which} action_id={action_id} "
            f"spec={'OK' if spec else 'NONE'}"
        )
        if spec is None:
            print(f"[HUD] invalid action_id={action_id!r} (spec missing)")
            return
        actor = ctx.game_state.get("active_char")
        self._dispatch_action(
            action_id,
            actor_obj=actor,
            args=[],
            time_min_override=time_min,
            source="HUD",
        )

    def on_mode_dropdown(self, new_mode: str) -> None:
        """モードを切り替える"""
        ctx = self.ctx
        if not ctx.director.set_mode(new_mode):
            return
        ctx.director_hud.set_mode(ctx.director.mode)
        ctx.bump_hud_cache_rev(reason="mode_change")
        print(f"[Director] mode -> {new_mode}")
        self.on_show_micro()
        self.refresh_hud()

    def bind_to_hud(self) -> None:
        """コールバックを DirectorHUD にバインドする"""
        hud = self.ctx.director_hud
        if hud is None:
            return
        hud.on_auto_action = self.ai_step_once
        hud.on_ai_step = self._request_auto_step
        hud.on_toggle_auto = self.set_auto
        hud.on_reroll = self.on_reroll
        hud.on_save = self.on_save
        hud.on_load = self.on_load
        hud.on_show_micro = self.on_show_micro
        hud.on_action_select = self.on_action_select
