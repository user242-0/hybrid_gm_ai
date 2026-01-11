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

# 中略...
USE_CLI = False     # True にすると黒い端末だけでプレイ

# --- 起動時に Scheduler 用意 ---
scheduler = Scheduler()
game_state = init_game_state()    # ★ ここで一度だけ生成
init_world(game_state)
BASE_DIR = Path(__file__).resolve().parent.parent

cli_parser = argparse.ArgumentParser(add_help=False)
cli_parser.add_argument("--premise-text", type=str, default=None)
simulation_cli_args, _ = cli_parser.parse_known_args()

cfg = load_config()
director_cfg = cfg.get("director", {})
director_enabled = bool(director_cfg.get("enabled", False))

director = None
director_world = None
director_hud = None
director_hud = None
pipeline: ActionPipeline | None = None

auto_enabled = False
_last_auto_step_ts = 0.0
AUTO_STEP_INTERVAL_SECONDS = 0.5


def ai_step_once() -> None:
    """Fallback no-op when director HUD is unavailable."""


def set_auto(enabled: bool) -> None:
    global auto_enabled
    auto_enabled = bool(enabled)


def maybe_run_auto() -> None:
    """Fallback no-op."""

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
    director = Director(premise=premise, goals_dict=goals)
    print(
        f"[Director] enabled seed={premise.get('seed')} "
        f"premise='{premise.get('title')}' pack={pack_id}"
    )

    existing_world = game_state.get("director_world")
    if existing_world:
        director_world = existing_world
        director_world["reload_epoch"] = director_world.get("reload_epoch", 0) + 1
    else:
        director_world = director.synthesize_world()
        director_world = apply_world_defaults(director_world, pack_data)
    ensure_clock(director_world)

    game_state["director_world"] = director_world
    game_state["world"] = director_world
    game_state["director_micro_goal"] = None

    if DirectorHUD is not None:
        try:
            director_hud = DirectorHUD(title="Director HUD")
        except TclError as exc:  # pragma: no cover - GUI unavailable
            director_hud = None
            print(f"[DirectorHUD] failed to initialize: {exc}")
        else:
            director_hud.run_async()
            director_hud.set_mode(director.mode)
            director_hud.set_clock(_director_clock_string(director_world))
            director_hud.set_microgoal(game_state.get("director_micro_goal"))
else:
    game_state["director_world"] = None
    game_state["director_micro_goal"] = None
    print("[Director] disabled")


def _pump_director_hud() -> None:
    if director_hud is None:
        return
    if threading.current_thread() is threading.main_thread():
        director_hud.pump()
    else:
        director_hud.request_update()


def ui_show_micro(micro_goal, gs):
    gs["director_micro_goal"] = micro_goal
    if director_hud is not None:
        director_hud.set_microgoal(micro_goal)


if director_enabled and director_hud is not None:

    current_actions: list[tuple[str, str, int]] = []
    available_modes = director.available_modes()
    if not available_modes:
        print("[Director] warning: no modes found in goals_dict")

    def refresh_hud() -> None:
        if director_hud is None:
            return
        if director_world is None:
            director_hud.set_progress(None)
            director_hud.set_recommended(None, enabled=False)
            director_hud.set_actions([])
            return

        director_hud.set_progress(director.progress_text(director_world))

        rec_action, rec_minutes, rec_label = director.recommended_action(director_world)
        if isinstance(director_world, dict):
            if rec_action:
                director_world["_recommended_action_id"] = rec_action
            else:
                director_world.pop("_recommended_action_id", None)
        if rec_action:
            label = f"★ {rec_label or rec_action} (+{rec_minutes}m)"
            director_hud.set_recommended(label, enabled=True)
        else:
            director_hud.set_recommended("(Recommended)", enabled=False)

        current_actions.clear()
        for record in director.list_actions_for_mode(director.mode):
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
            current_actions.append((action_id, label, max(0, minutes)))
        director_hud.set_actions(current_actions.copy())

    def _hud_adjust_value(path, delta, *, minimum=None, maximum=None):
        node = director_world
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
        if director_world is None:
            return
        micro = director.get_micro_goal(director_world, reroll=False)
        ui_show_micro(micro, game_state)
        micro_text = micro or "(MicroGoal なし)"
        print(f"[UI] MicroGoal: {micro_text}")
        refresh_hud()

    def on_reroll() -> None:
        if director_world is None:
            return
        micro = director.get_micro_goal(director_world, reroll=True)
        ui_show_micro(micro, game_state)
        micro_text = micro or "(MicroGoal なし)"
        print(f"[UI] MicroGoal (reroll): {micro_text}")
        refresh_hud()

    def ai_step_once() -> None:
        global _last_auto_step_ts

        if director_world is None:
            return

        actions = director.list_actions_for_mode(director.mode) or []
        micro = director.get_micro_goal(director_world, reroll=False)
        action_id, tmin, _ = pick_action(director_world, director.mode, actions, micro)
        _last_auto_step_ts = time.monotonic()

        if not action_id:
            director.clear_micro_goal()
            on_show_micro()
            refresh_hud()
            print("[RC_AI] no action; rerolled micro")
            return
        ###↓
        emo_before = director_world.get("emotion", {}).copy()
        ###↑
        dispatch_action(
            action_id,
            actor_obj=game_state.get("active_char"),
            args=[],
            time_min_override=tmin,
            source="RC_AI",
        )
        if isinstance(director_world, dict):
            director_world["_last_action_id"] = action_id

        ###↓
        emo_after = director_world.get("emotion", {})
        print(
            f"[RC_AI] picked={action_id} reason={_} "
            f"emotion R:{emo_before.get('R')}→{emo_after.get('R')} "
            f"G:{emo_before.get('G')}→{emo_after.get('G')} "
            f"B:{emo_before.get('B')}→{emo_after.get('B')}"
        )
        ###↑
        clock_label = _director_clock_string(director_world)
        if director_hud is not None:
            director_hud.set_clock(clock_label)
        if director.is_micro_goal_done(director_world):
            director.clear_micro_goal()
            print("[MICRO] completed -> next")
        on_show_micro()
        refresh_hud()

    def set_auto(enabled: bool) -> None:
        global auto_enabled, _last_auto_step_ts

        auto_enabled = bool(enabled)
        if auto_enabled:
            _last_auto_step_ts = time.monotonic() - AUTO_STEP_INTERVAL_SECONDS
        if director_hud is not None:
            director_hud.set_auto_enabled(auto_enabled)
        state = "on" if auto_enabled else "off"
        print(f"[RC_AI] auto={state}")

    def maybe_run_auto() -> None:
        if not auto_enabled:
            return
        if director_world is None:
            return
        if time.monotonic() - _last_auto_step_ts < AUTO_STEP_INTERVAL_SECONDS:
            return
        ai_step_once()

    def on_save() -> None:
        if director_world is None:
            return
        save_director_world(director_world)
        print("[SAVE] world saved")

    def on_load() -> None:
        global director_world
        loaded = load_director_world(director_world)
        if loaded is None:
            return
        director_world = loaded
        ensure_clock(director_world)
        if isinstance(director_world, dict):
            director_world["reload_epoch"] = director_world.get("reload_epoch", 0) + 1
        game_state["director_world"] = director_world
        game_state["world"] = director_world
        if director_hud is not None:
            director_hud.set_clock(_director_clock_string(director_world))
        director.clear_micro_goal()
        on_show_micro()
        reload_epoch = (
            director_world.get("reload_epoch") if isinstance(director_world, dict) else None
        )
        print(f"[LOAD] world loaded; reload_epoch={reload_epoch}")

    def on_action_select(which: object) -> None:
        if director_world is None:
            return
        action_id = None
        time_min = None
        if which == "__recommended__":
            action_id, time_min, _ = director.recommended_action(director_world)
        elif isinstance(which, int) and 0 <= which < len(current_actions):
            action_id, _, time_min = current_actions[which]
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
        actor = game_state.get("active_char")
        dispatch_action(
            action_id,
            actor_obj=actor,
            args=[],
            time_min_override=time_min,
            source="HUD",
        )

    director_hud.on_auto_action = ai_step_once
    director_hud.on_ai_step = ai_step_once
    director_hud.on_toggle_auto = set_auto
    director_hud.on_reroll = on_reroll
    director_hud.on_save = on_save
    director_hud.on_load = on_load
    director_hud.on_show_micro = on_show_micro
    director_hud.on_action_select = on_action_select

    def on_mode_dropdown(new_mode: str) -> None:
        if not director.set_mode(new_mode):
            return
        director_hud.set_mode(director.mode)
        print(f"[Director] mode -> {new_mode}")
        on_show_micro()
        refresh_hud()

    director_hud.set_modes(available_modes, on_change=on_mode_dropdown)
    director_hud.set_mode(director.mode)
    director_hud.set_auto_enabled(auto_enabled)
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
    world = game_state.get("director_world") or game_state.get("world")
    if not isinstance(world, dict):
        return
    if world.get("t_min") is not None or isinstance(world.get("clock"), dict):
        if game_state.get("world") is world:
            world_tick(game_state, dt=minutes)
        else:
            temp_state = {"world": world, "time_of_day": game_state.get("time_of_day")}
            world_tick(temp_state, dt=minutes)
            if "time_of_day" in temp_state:
                game_state["time_of_day"] = temp_state["time_of_day"]
    else:
        ensure_clock(world)
        add_minutes(world, minutes)

hud_refresh_cb = globals().get("refresh_hud")
pipeline = ActionPipeline(
    game_state=game_state,
    director=director,
    emit_director_scenes=write_scenes_to_scene_graph,
    ui_refresh=hud_refresh_cb if callable(hud_refresh_cb) else None,
    hud_set_clock=(director_hud.set_clock if director_hud else None),
    hud_set_microgoal=(director_hud.set_microgoal if director_hud else None),
    advance_time=_advance_time,
)

def dispatch_action(
    action_id: str,
    actor_obj: object | None = None,
    args: list[object] | None = None,
    time_min_override: int | None = None,
    source: str = "UI",
):
    if pipeline is None:
        return None
    return pipeline.request_action(
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
def rc_tick(rc_char, game_state):
    #[DEBUG]
    #print('[TICK]', rc_char.name, rc_char.is_npc)
    #END[DEBUG]
    if not rc_char.is_npc:       # ← 手動キャラなら
        return                   #    AI ロジックを完全スキップ

    # ❶ 現時点で実行可能な choice 一覧を取得
    choices = get_available_choices(rc_char, game_state)

    # ❷ AI に選択させる
    choice = select_action(rc_char, game_state, choices)
    if not choice:
        return                                    # 該当なしなら終了

    # ❸ アクション実行
    act_info = actions[choice.action_key]
    args = parse_args(act_info, rc_char, game_state)
    if choice.action_key == "switch_character":
        target_name = choose_target_for_switch(rc_char, game_state)
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
        scheduler.register(rc_tick, 0.01, result, game_state)


    # ❹ 次の RC Tick を再登録（0.2 s 後）
    if rc_char.is_npc:           # ← 再登録は AI 時だけで OK
        scheduler.register(rc_tick, 0.2, rc_char, game_state)

# -------------------------------


# ---------------- Simulation スレッド ----------------
def player_loop(gs):              # ← 引数で参照を受け取る
    # ① 全キャラをスケジューラに登録
    for ch in gs["party"].values():
        scheduler.register(rc_tick, 0.2, ch, gs)

    # ② メインループ
    while gs["running"]:
        maybe_run_auto()
        while scheduler.run_once():          # due を全部消化
            if director_hud is not None:
                director_hud.pump()
            maybe_run_auto()
        actor = gs["active_char"]
        director_world = gs.get("director_world")
        if director is not None and director_world is not None:
            micro_goal = director.get_micro_goal(director_world, reroll=False)
            ui_show_micro(micro_goal, gs)
            if director_hud is not None:
                director_hud.set_mode(director.mode)
                director_hud.set_clock(_director_clock_string(director_world))
        num_choice_map = {}
        command_ready = False
        # ▼ CLI で直接 input() する場合（GUI を使わないモード）
        if USE_CLI:
            gs["input_pending"] = True
            raw = input(">> ").strip()
            gs["input_pending"] = False
            handle_quit(raw, gs)          # ★ ここで判定
            cmd = raw                     # → 後続処理へ
            command_ready = True

        # ▼ GUI モード：Entry から event_q を受信
        else:
            gs["input_pending"] = True
            try:
                num_choice_map = present_choices(actor, gs)     # ← dict を受け取る
                cmd = event_q.get(timeout=0.05)
                command_ready = True
            except Empty:
                maybe_run_auto()
                if director_hud is not None:
                    director_hud.pump()
                time.sleep(0.01)
                continue
            finally:
                gs["input_pending"] = False
            handle_quit(cmd, gs)          # ★ ここでも同じ

        if not command_ready:
            if director_hud is not None:
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
        

        # ★ プレイヤーが操作する瞬間に必ず手動フラグを立て直す
        actor.is_npc = False                   # ← これを追加
        parts = cmd.split()
        if not parts:
            if director_hud is not None:
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
            scheduler.register(rc_tick, 0.01, result, gs)
        # flush AI 行動
        while scheduler.run_once() is not None:
            if director_hud is not None:
                _pump_director_hud()
            maybe_run_auto()

        # 操作キャラが変わっている可能性があるので再表示
        present_choices(gs["active_char"], gs)
        if director_hud is not None:
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
    gs = game_state                           # ローカル短縮も可

    threading.Thread(target=player_loop, args=(gs,), daemon=True).start()
    start_gui(gs)                               # GUI は内部でサブスレッドを立てても良い
    # メインスレッドは生存維持だけ
    try:
        while gs["running"]:
            if director_hud is not None:
                _pump_director_hud()
            time.sleep(0.01)
    except SystemExit:
        pass                        # どこかのスレッドで raise SystemExit 渡ってきたら即終了
