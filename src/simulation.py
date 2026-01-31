# simulation.py
# ターゲット選択時に使う
import argparse
import random
from pathlib import Path
import yaml

# ゲーム用モジュール
from src.character_status import CharacterStatus
from src.init_state  import init_game_state

# dictionary import
from src.action_definitions import actions, get_action_spec, get_action_specs

#gui import
from src.event_bus import event_q, log_q
import threading, time
from gui          import start_gui
from queue import Empty        # ← 追加

# 追加import
from src.scheduler import Scheduler
from src.world import init_world, world_tick
from src.rc_ai import pick_action, select_action
from src.choice_definitions import get_available_choices
from src.utility.args_parser import parse_args
from src.utility.config_loader import job_root_from_cfg, load_config
from director.registry import load_pack, synthesize_from_text
from director.director import Director, load_yaml
from src.world_defaults import apply_world_defaults

try:
    from tkinter import TclError
except ImportError:  # pragma: no cover - tkinter may be missing in headless environments
    TclError = Exception  # type: ignore

try:
    from src.ui.director_hud import DirectorHUD
except ImportError:  # pragma: no cover - optional dependency
    DirectorHUD = None  # type: ignore

# execute_player_choice import
from src.simulation_utils import (
    add_minutes,
    ensure_clock,
)
from src.choice_ui import present_choices
from src.ui.action_pipeline import ActionPipeline

# 安全に終了したい
from src.quit_helper import handle_quit

# コンテキスト管理
from src.game_context import GameContext

# 中略...
USE_CLI = False     # True にすると黒い端末だけでプレイ

# --- 起動時に GameContext を初期化 ---
BASE_DIR = Path(__file__).resolve().parent.parent

cli_parser = argparse.ArgumentParser(add_help=False)
cli_parser.add_argument("--premise-text", type=str, default=None)
simulation_cli_args, _ = cli_parser.parse_known_args()

_cfg = load_config()
_game_state = init_game_state()
_game_state["last_auto_ts"] = 0.0
_game_state.setdefault("hud_cache_rev", 0)
_game_state.setdefault("hud_last_rendered_rev", -1)
_game_state.setdefault("hud_cached_actions", [])
_game_state.setdefault("hud_cached_progress", None)
_game_state.setdefault(
    "hud_cached_recommended",
    {"label": None, "enabled": False, "action_id": None, "minutes": None},
)
init_world(_game_state)

# GameContext インスタンス（唯一のグローバル状態）
ctx = GameContext(
    scheduler=Scheduler(),
    game_state=_game_state,
    cfg=_cfg,
)

# 後方互換用エイリアス（段階的に削除予定）
scheduler = ctx.scheduler
game_state = ctx.game_state
cfg = ctx.cfg
director = ctx.director
director_world = ctx.director_world
director_hud = ctx.director_hud
pipeline = ctx.pipeline
auto_enabled = ctx.auto_enabled

director_cfg = _cfg.get("director", {})
director_enabled = bool(director_cfg.get("enabled", False))


def ai_step_once() -> None:
    """Fallback no-op when director HUD is unavailable."""


def set_auto(enabled: bool) -> None:
    ctx.set_auto(enabled)


def request_auto_step() -> None:
    ctx.request_auto_step()


def maybe_run_auto() -> None:
    if ctx.game_state.get("auto_step_pending"):
        ai_step_once()
        ctx.game_state["auto_step_pending"] = False
        return
    if not ctx.auto_enabled:
        return
    last_auto_ts = ctx.game_state.get("last_auto_ts", 0.0)
    if time.monotonic() - last_auto_ts < ctx.AUTO_STEP_INTERVAL_SECONDS:
        return
    ai_step_once()

###[deBug]
# simulation.py 等で定義している GridWorld に追記/調整
class GridWorld:
    def __init__(self, rooms=None, dt_per_action=30, clock=None, weather=None, t_min=0):
        self.rooms = rooms or {}                                      # {(x,y): "部屋名"}
        self.dt_per_action = dt_per_action                            # world.get("dt_per_action", 30)
        self.clock = clock or {"minute": 0, "hour": 8, "day": 1}      # world["clock"]
        self.weather = weather or {"kind": "clear", "intensity": 0}   # world.setdefault("weather", {...})
        self.t_min = t_min                                            # world["t_min"]

    # --- 辞書ライク API（world.py が dict を想定しても動く）---
    def get(self, key, default=None):
        return getattr(self, key, default)

    def __getitem__(self, key):
        if hasattr(self, key):
            return getattr(self, key)
        raise KeyError(key)

    def __setitem__(self, key, value):
        setattr(self, key, value)

    def setdefault(self, key, default=None):              # ← 今回これが無くて落ちた
        if not hasattr(self, key) or getattr(self, key) is None:
            setattr(self, key, default)
            return default
        return getattr(self, key)

    # 任意：'in' ガードが書かれていても落ちないように
    def __contains__(self, key):
        return hasattr(self, key)

    # 位置前進（例。既にあるならそのままでOK）
    def advance(self, pos, direction=None):
        x = (pos or {}).get("x", 0)
        y = (pos or {}).get("y", 0)
        dx, dy = {"N": (0,1), "S": (0,-1), "E": (1,0), "W": (-1,0)}.get(direction or "N", (0,1))
        new_pos = {"x": x+dx, "y": y+dy}
        name = self.rooms.get((new_pos["x"], new_pos["y"]), f"通路({new_pos['x']},{new_pos['y']})")
        return new_pos, name


###
###[deBug]
"""
game_state["position"] = {"x":0, "y":0}
game_state["direction"] = "N"
game_state["world"] = GridWorld(
    rooms = {(0,1): "洞窟入口", (0,2): "湿った通路", (0,3): "石像の間"},
    dt_per_action = 30,
    clock = {"minute": 0, "hour": 8, "day": 1},
)
"""
###
def _director_clock_string(world: dict | None) -> str:
    if not isinstance(world, dict):
        return "Day1 00:00"
    ensure_clock(world)
    clock = world.get("clock")
    if isinstance(clock, str):
        return clock
    if isinstance(clock, dict):
        label = clock.get("label")
        if label:
            return str(label)
        day = clock.get("day")
        time = clock.get("time")
        if day is not None and time is not None:
            return f"Day{day} {time}"
        hour = clock.get("hour")
        minute = clock.get("minute")
        if day is not None and hour is not None and minute is not None:
            return f"Day{day} {hour:02d}:{minute:02d}"
    return "Day1 00:00"


def _bump_hud_cache_rev(gs: dict, reason: str | None = None) -> None:
    gs["hud_cache_rev"] = gs.get("hud_cache_rev", 0) + 1
    if reason:
        print(f"[HUD_DEBUG] bump reason={reason} rev={gs['hud_cache_rev']}")


def _update_microgoal(micro_goal, gs: dict) -> None:
    previous = gs.get("director_micro_goal")
    gs["director_micro_goal"] = micro_goal
    if previous != micro_goal:
        _bump_hud_cache_rev(gs, reason="microgoal_change")


def ui_show_micro(micro_goal, gs):
    _update_microgoal(micro_goal, gs)
    if ctx.director_hud is not None:
        ctx.director_hud.set_microgoal(micro_goal)


if director_enabled:
    if simulation_cli_args.premise_text:
        premise, goals, pack_id = synthesize_from_text(simulation_cli_args.premise_text)
    else:
        premise_path = Path(director_cfg.get("premise_path", "data/director/premise.yml"))
        if not premise_path.is_absolute():
            premise_path = BASE_DIR / premise_path
        premise_doc = load_yaml(str(premise_path)) or {}
        premise = premise_doc.get("premise", {})
        goals_path = BASE_DIR / "data/director/cop_trickster_goals.yml"
        goals = load_yaml(str(goals_path)) or {}
        pack_id = "cop_trickster"
    pack_data = load_pack(pack_id) if pack_id else None
    if isinstance(pack_data, dict):
        pack_data = dict(pack_data)
        pack_data.setdefault("id", pack_id)
    get_action_specs(pack_data)
    ctx.director = Director(premise=premise, goals_dict=goals)
    print(
        f"[Director] enabled seed={premise.get('seed')} "
        f"premise='{premise.get('title')}' pack={pack_id}"
    )

    existing_world = ctx.game_state.get("director_world")
    if existing_world:
        ctx.director_world = existing_world
        ctx.director_world["reload_epoch"] = ctx.director_world.get("reload_epoch", 0) + 1
    else:
        ctx.director_world = ctx.director.synthesize_world()
        ctx.director_world = apply_world_defaults(ctx.director_world, pack_data)
    ensure_clock(ctx.director_world)

    ctx.game_state["director_world"] = ctx.director_world
    ctx.game_state["world"] = ctx.director_world
    ctx.game_state["director_micro_goal"] = None
    ctx.bump_hud_cache_rev(reason="director_init")

    if DirectorHUD is not None:
        try:
            ctx.director_hud = DirectorHUD(title="Director HUD")
        except TclError as exc:  # pragma: no cover - GUI unavailable
            ctx.director_hud = None
            print(f"[DirectorHUD] failed to initialize: {exc}")
        else:
            ctx.director_hud.run_async()
            ctx.director_hud.set_mode(ctx.director.mode)
            ctx.director_hud.set_clock(_director_clock_string(ctx.director_world))
            ctx.director_hud.set_microgoal(ctx.game_state.get("director_micro_goal"))
else:
    ctx.game_state["director_world"] = None
    ctx.game_state["director_micro_goal"] = None
    print("[Director] disabled")


def _pump_director_hud() -> None:
    if ctx.director_hud is None:
        return
    if threading.current_thread() is threading.main_thread():
        ctx.director_hud.pump()
    else:
        ctx.director_hud.request_update()


if director_enabled and ctx.director_hud is not None:

    ctx.current_actions = []
    available_modes = ctx.director.available_modes()
    if not available_modes:
        print("[Director] warning: no modes found in goals_dict")

    def refresh_hud() -> None:
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
            print(f"[HUD_DEBUG] recompute rev={cache_rev} last={last_rendered_rev}")
            progress_text = ctx.director.progress_text(ctx.director_world)
            ctx.game_state["hud_cached_progress"] = progress_text

            rec_action, rec_minutes, rec_label = ctx.director.recommended_action(ctx.director_world)
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
                minutes = 5
                if isinstance(record, dict):
                    action_id = record.get("action") or record.get("id") or record.get("action_id")
                    label = record.get("text") or record.get("label")
                    try:
                        minutes = int(record.get("time_min", 5))
                    except (TypeError, ValueError):
                        minutes = 5
                if not action_id:
                    continue
                spec = get_action_spec(action_id)
                if not label:
                    label = spec.label if spec else action_id
                ctx.current_actions.append((action_id, label, max(0, minutes)))
            ctx.current_actions.sort(key=lambda item: item[0])
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

    def _hud_adjust_value(path, delta, *, minimum=None, maximum=None):
        node = ctx.director_world
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

    def on_show_micro() -> None:
        if ctx.director_world is None:
            return
        micro = ctx.director.get_micro_goal(ctx.director_world, reroll=False)
        ui_show_micro(micro, ctx.game_state)
        micro_text = micro or "(MicroGoal なし)"
        print(f"[UI] MicroGoal: {micro_text}")

    def on_reroll() -> None:
        if ctx.director_world is None:
            return
        micro = ctx.director.get_micro_goal(ctx.director_world, reroll=True)
        ui_show_micro(micro, ctx.game_state)
        micro_text = micro or "(MicroGoal なし)"
        print(f"[UI] MicroGoal (reroll): {micro_text}")
        refresh_hud()

    def ai_step_once() -> None:
        if ctx.director_world is None:
            return

        actions = ctx.director.list_actions_for_mode(ctx.director.mode) or []
        micro = ctx.director.get_micro_goal(ctx.director_world, reroll=False)
        action_id, tmin, _ = pick_action(ctx.director_world, ctx.director.mode, actions, micro)

        if not action_id:
            ctx.director.clear_micro_goal()
            on_show_micro()
            refresh_hud()
            print("[RC_AI] no action; rerolled micro")
            return
        emo_before = ctx.director_world.get("emotion", {}).copy()
        dispatch_action(
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
            f"[RC_AI] picked={action_id} reason={_} "
            f"emotion R:{emo_before.get('R')}→{emo_after.get('R')} "
            f"G:{emo_before.get('G')}→{emo_after.get('G')} "
            f"B:{emo_before.get('B')}→{emo_after.get('B')}"
        )
        clock_label = _director_clock_string(ctx.director_world)
        if ctx.director_hud is not None:
            ctx.director_hud.set_clock(clock_label)
        non_progress_actions = {"switch_character", "感情を設定する"}
        if action_id not in non_progress_actions and ctx.director.is_micro_goal_done(ctx.director_world):
            ctx.director.clear_micro_goal()
            next_micro = ctx.director.get_micro_goal(ctx.director_world, reroll=False)
            if next_micro and next_micro != "(MicroGoal なし)":
                print("[MICRO] completed -> next")
        on_show_micro()
        refresh_hud()

    def set_auto(enabled: bool) -> None:
        ctx.set_auto(enabled)

    def maybe_run_auto() -> None:
        if ctx.game_state.get("auto_step_pending"):
            if ctx.director_world is None:
                ctx.game_state["auto_step_pending"] = False
                return
            ai_step_once()
            ctx.game_state["auto_step_pending"] = False
            return
        if ctx.director_world is None:
            return
        if not ctx.auto_enabled:
            return
        last_auto_ts = ctx.game_state.get("last_auto_ts", 0.0)
        if time.monotonic() - last_auto_ts < ctx.AUTO_STEP_INTERVAL_SECONDS:
            return
        ai_step_once()

    def on_save() -> None:
        if ctx.director_world is None:
            return
        save_director_world(ctx.director_world)
        print("[SAVE] world saved")

    def on_load() -> None:
        loaded = load_director_world(ctx.director_world)
        if loaded is None:
            return
        ctx.director_world = loaded
        ensure_clock(ctx.director_world)
        if isinstance(ctx.director_world, dict):
            ctx.director_world["reload_epoch"] = ctx.director_world.get("reload_epoch", 0) + 1
        ctx.game_state["director_world"] = ctx.director_world
        ctx.game_state["world"] = ctx.director_world
        ctx.bump_hud_cache_rev(reason="world_load")
        if ctx.director_hud is not None:
            ctx.director_hud.set_clock(_director_clock_string(ctx.director_world))
        ctx.director.clear_micro_goal()
        on_show_micro()
        reload_epoch = (
            ctx.director_world.get("reload_epoch") if isinstance(ctx.director_world, dict) else None
        )
        print(f"[LOAD] world loaded; reload_epoch={reload_epoch}")

    def on_action_select(which: object) -> None:
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
        spec = get_action_spec(action_id)
        print(
            f"[HUD] which={which} action_id={action_id} "
            f"spec={'OK' if spec else 'NONE'}"
        )
        if spec is None:
            print(f"[HUD] invalid action_id={action_id!r} (spec missing)")
            return
        actor = ctx.game_state.get("active_char")
        dispatch_action(
            action_id,
            actor_obj=actor,
            args=[],
            time_min_override=time_min,
            source="HUD",
        )

    ctx.director_hud.on_auto_action = ai_step_once
    ctx.director_hud.on_ai_step = request_auto_step
    ctx.director_hud.on_toggle_auto = set_auto
    ctx.director_hud.on_reroll = on_reroll
    ctx.director_hud.on_save = on_save
    ctx.director_hud.on_load = on_load
    ctx.director_hud.on_show_micro = on_show_micro
    ctx.director_hud.on_action_select = on_action_select

    def on_mode_dropdown(new_mode: str) -> None:
        if not ctx.director.set_mode(new_mode):
            return
        ctx.director_hud.set_mode(ctx.director.mode)
        ctx.bump_hud_cache_rev(reason="mode_change")
        print(f"[Director] mode -> {new_mode}")
        on_show_micro()
        refresh_hud()

    ctx.director_hud.set_modes(available_modes, on_change=on_mode_dropdown)
    ctx.director_hud.set_mode(ctx.director.mode)
    ctx.director_hud.set_auto_enabled(ctx.auto_enabled)
    on_show_micro()

"""
# Luna への参照を取得
if isinstance(game_state["party"], dict):
    luna_from_party = game_state["party"]["Luna"]
else:  # list or tuple
    luna_from_party = next(c for c in game_state["party"] if c.name == "Luna")

luna_from_map = game_state["party_map"]["Luna"]

print("id in party:", id(luna_from_party))
print("id in map  :", id(luna_from_map))
"""


def record(msg):
    log_q.put(msg)          # ← 旧 logger と二重にしても OK


def write_scenes_to_scene_graph(scenes):
    if not scenes:
        return
    job_root = Path(job_root_from_cfg())
    sg_path = job_root / "scene_graph.yml"
    sg_path.parent.mkdir(parents=True, exist_ok=True)
    if sg_path.exists():
        existing = yaml.safe_load(sg_path.read_text(encoding="utf-8")) or {}
    else:
        existing = {}
    if not isinstance(existing, dict):
        existing = {}
    meta = existing.setdefault("meta", {})
    entries = meta.setdefault("director_scenes", [])
    for scene in scenes:
        entries.append(
            {
                "intent": scene.get("intent"),
                "why_now": scene.get("why_now"),
                "salience": float(scene.get("salience", 0.0)),
            }
        )
    sg_path.write_text(yaml.safe_dump(existing, allow_unicode=True, sort_keys=False), encoding="utf-8")

def _advance_time(minutes: int) -> None:
    world = ctx.game_state.get("director_world") or ctx.game_state.get("world")
    if not isinstance(world, dict):
        return
    if world.get("t_min") is not None or isinstance(world.get("clock"), dict):
        if ctx.game_state.get("world") is world:
            world_tick(ctx.game_state, dt=minutes)
        else:
            temp_state = {"world": world, "time_of_day": ctx.game_state.get("time_of_day")}
            world_tick(temp_state, dt=minutes)
            if "time_of_day" in temp_state:
                ctx.game_state["time_of_day"] = temp_state["time_of_day"]
    else:
        ensure_clock(world)
        add_minutes(world, minutes)

hud_refresh_cb = globals().get("refresh_hud")
ctx.pipeline = ActionPipeline(
    game_state=ctx.game_state,
    director=ctx.director,
    emit_director_scenes=write_scenes_to_scene_graph,
    ui_refresh=hud_refresh_cb if callable(hud_refresh_cb) else None,
    hud_set_clock=(ctx.director_hud.set_clock if ctx.director_hud else None),
    hud_set_microgoal=(ctx.director_hud.set_microgoal if ctx.director_hud else None),
    advance_time=_advance_time,
)

def dispatch_action(
    action_id: str,
    actor_obj: object | None = None,
    args: list[object] | None = None,
    time_min_override: int | None = None,
    source: str = "UI",
):
    if ctx.pipeline is None:
        return None
    return ctx.pipeline.request_action(
        action_id,
        actor_obj=actor_obj,
        args=args or [],
        time_min_override=time_min_override,
        source=source,
    )


def _director_world_path() -> Path:
    job_root = Path(job_root_from_cfg())
    job_root.mkdir(parents=True, exist_ok=True)
    return job_root / "director_world.yml"


def save_director_world(world: dict) -> None:
    path = _director_world_path()
    try:
        path.write_text(
            yaml.safe_dump(world, allow_unicode=True, sort_keys=False),
            encoding="utf-8",
        )
    except Exception as exc:  # pragma: no cover - logging only
        print(f"[SAVE] failed to persist director world: {exc}")


def load_director_world(fallback: dict | None) -> dict | None:
    path = _director_world_path()
    if not path.exists():
        return fallback
    try:
        loaded = yaml.safe_load(path.read_text(encoding="utf-8"))
    except Exception as exc:  # pragma: no cover - logging only
        print(f"[LOAD] failed to restore director world: {exc}")
        return fallback
    if isinstance(loaded, dict):
        ensure_clock(loaded)
        return loaded
    return fallback


# ---------------- ワールド Tick コールバック ----------------
def world_tick_cb(gs):
    if not gs.get("running", False):
        return

# ---------------- RC Tick コールバック ----------------
def rc_tick(rc_char, gs):
    if not rc_char.is_npc:
        return

    # 現時点で実行可能な choice 一覧を取得
    choices = get_available_choices(rc_char, gs)

    # AI に選択させる
    choice = select_action(rc_char, gs, choices)
    if not choice:
        return

    # アクション実行
    act_info = actions[choice.action_key]
    args = parse_args(act_info, rc_char, gs)
    if choice.action_key == "switch_character":
        target_name = choose_target_for_switch(rc_char, gs)
        args = [target_name]
    else:
        args = list(args)
    result = dispatch_action(
        choice.action_key,
        actor_obj=rc_char,
        args=args,
        source="RC_AI",
    )

    record(f"[AI] {rc_char.name} ▶ {choice.action_key}")

    if isinstance(result, CharacterStatus) and result.is_npc:
        ctx.scheduler.register(rc_tick, 0.01, result, gs)

    # 次の RC Tick を再登録（0.2 s 後）
    if rc_char.is_npc:
        ctx.scheduler.register(rc_tick, 0.2, rc_char, gs)

# -------------------------------


# ---------------- Simulation スレッド ----------------
def player_loop(gs):
    # 全キャラをスケジューラに登録
    for ch in gs["party"].values():
        ctx.scheduler.register(rc_tick, 0.2, ch, gs)

    # メインループ
    while gs["running"]:
        maybe_run_auto()
        while ctx.scheduler.run_once():
            if ctx.director_hud is not None:
                ctx.director_hud.pump()
            maybe_run_auto()
        actor = gs["active_char"]
        dw = gs.get("director_world")
        if ctx.director is not None and dw is not None:
            micro_goal = ctx.director.get_micro_goal(dw, reroll=False)
            ui_show_micro(micro_goal, gs)
            if ctx.director_hud is not None:
                ctx.director_hud.set_mode(ctx.director.mode)
                ctx.director_hud.set_clock(_director_clock_string(dw))
        num_choice_map = {}
        command_ready = False
        # CLI で直接 input() する場合（GUI を使わないモード）
        if USE_CLI:
            gs["input_pending"] = True
            raw = input(">> ").strip()
            gs["input_pending"] = False
            handle_quit(raw, gs)
            cmd = raw
            command_ready = True

        # GUI モード：Entry から event_q を受信
        else:
            gs["input_pending"] = True
            try:
                num_choice_map = present_choices(actor, gs)
                cmd = event_q.get(timeout=0.05)
                command_ready = True
            except Empty:
                maybe_run_auto()
                if ctx.director_hud is not None:
                    ctx.director_hud.pump()
                time.sleep(0.01)
                continue
            finally:
                gs["input_pending"] = False
            handle_quit(cmd, gs)

        if not command_ready:
            if ctx.director_hud is not None:
                _pump_director_hud()
            maybe_run_auto()
            time.sleep(0.01)
            continue

        # 数字入力なら Choice に変換
        if cmd.isdigit():
            idx = int(cmd)
            if idx in num_choice_map:
                selected_choice = num_choice_map[idx]
                # action_key と対象キャラ名を組み合わせて文字列化
                cmd = selected_choice.action_key
                if selected_choice.action_key == "switch_character":
                    # シンプルに Actor 以外の最初のキャラをターゲット
                    others = [c for c in gs["party"].values() if c is not actor]
                    cmd += f" {others[0].name}"
        

        # プレイヤーが操作する瞬間に必ず手動フラグを立て直す
        actor.is_npc = False
        parts = cmd.split()
        if not parts:
            if ctx.director_hud is not None:
                _pump_director_hud()
            maybe_run_auto()
            time.sleep(0.01)
            continue
        action_id = parts[0]
        args = parts[1:]
        result = dispatch_action(
            action_id,
            actor_obj=actor,
            args=args,
            source="CLI" if USE_CLI else "GUI",
        )

        # 旧プレイヤーが CharacterStatus なら AI キューに登録
        if isinstance(result, CharacterStatus):
            print('[REG]', result.name, result.is_npc)
            ctx.scheduler.register(rc_tick, 0.01, result, gs)
        # flush AI 行動
        while ctx.scheduler.run_once() is not None:
            if ctx.director_hud is not None:
                _pump_director_hud()
            maybe_run_auto()

        # 操作キャラが変わっている可能性があるので再表示
        present_choices(gs["active_char"], gs)
        if ctx.director_hud is not None:
            _pump_director_hud()
        maybe_run_auto()
        time.sleep(0.01)

def choose_target_for_switch(rc_char, game_state):
    """
    Policy:
      - デフォルト(no_seize): アクティブでないNPCは現在のアクティブキャラをターゲットにし、
        プレイヤー操作を“奪わない”。（テスト期待と一致）
      - もし game_state['allow_ai_to_seize_control'] が True のときは、
        従来どおり“自分自身”をターゲットにしてスイッチ（目まぐるしい入れ替え用）。
    """
    seize = bool(game_state.get("allow_ai_to_seize_control", False))
    if game_state["active_char"] is not rc_char:
        # 非アクティブNPC → デフォルトは“奪わない”
        return rc_char.name if seize else game_state["active_char"].name

    # rc_char がアクティブな場合は従来通り、他候補から選択
    candidates = [c for c in game_state["party"].values() if c is not rc_char]
    return random.choice(candidates).name if candidates else rc_char.name

# ---------------- 起動処理 ----------------
if __name__ == "__main__":
    gs = ctx.game_state

    threading.Thread(target=player_loop, args=(gs,), daemon=True).start()
    start_gui(gs)
    # メインスレッドは生存維持だけ
    try:
        while gs["running"]:
            if ctx.director_hud is not None:
                _pump_director_hud()
            time.sleep(0.01)
    except SystemExit:
        pass
