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
from src.utility.config_loader import (
    job_root_from_cfg,
    load_config,
    is_hud_debug_enabled,
    get_rc_decision_interval_sec,
    get_rc_max_advance_minutes,
)
from director.registry import load_pack, extract_goals_from_pack, synthesize_from_text
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
from src.ui.hud_callbacks import HUDCallbacks

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

director_cfg = _cfg.get("director", {})
director_enabled = bool(director_cfg.get("enabled", False))


def request_auto_step() -> None:
    """自動ステップをリクエストする"""
    ctx.request_auto_step()


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
    if reason and is_hud_debug_enabled():
        print(f"[HUD_DEBUG] bump reason={reason} rev={gs['hud_cache_rev']}")


def _update_microgoal(micro_goal, gs: dict) -> None:
    previous = gs.get("director_micro_goal")
    gs["director_micro_goal"] = micro_goal
    if previous != micro_goal:
        _bump_hud_cache_rev(gs, reason="microgoal_change")


def ui_show_micro(micro_goal, gs, actor_id=None):
    _update_microgoal(micro_goal, gs)
    gs["director_micro_goal_actor_id"] = actor_id
    if ctx.director_hud is not None:
        display = f"MicroGoal({actor_id}): {micro_goal}" if actor_id else micro_goal
        ctx.director_hud.set_microgoal(display)


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
    except Exception as exc:
        print(f"[SAVE] failed to persist director world: {exc}")


def load_director_world(fallback: dict | None) -> dict | None:
    path = _director_world_path()
    if not path.exists():
        return fallback
    try:
        loaded = yaml.safe_load(path.read_text(encoding="utf-8"))
    except Exception as exc:
        print(f"[LOAD] failed to restore director world: {exc}")
        return fallback
    if isinstance(loaded, dict):
        ensure_clock(loaded)
        return loaded
    return fallback


if director_enabled:
    if simulation_cli_args.premise_text:
        premise, goals, pack_id = synthesize_from_text(simulation_cli_args.premise_text)
    else:
        premise_path = Path(director_cfg.get("premise_path", "data/director/premise.yml"))
        if not premise_path.is_absolute():
            premise_path = BASE_DIR / premise_path
        premise_doc = load_yaml(str(premise_path)) or {}
        premise = premise_doc.get("premise", {})
        pack_id = "cop_trickster"
    pack_data = load_pack(pack_id) if pack_id else None
    if not simulation_cli_args.premise_text:
        goals = extract_goals_from_pack(pack_data) if pack_data else {}
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
    ctx.game_state["director_micro_goal_actor_id"] = None
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
    ctx.game_state["director_micro_goal_actor_id"] = None
    print("[Director] disabled")


def _pump_director_hud() -> None:
    if ctx.director_hud is None:
        return
    if threading.current_thread() is threading.main_thread():
        ctx.director_hud.pump()
    else:
        ctx.director_hud.request_update()


# HUD コールバックのセットアップ（dispatch_action 定義後に初期化）
_hud_cbs: HUDCallbacks | None = None
_available_modes: list[str] = []

if director_enabled and ctx.director_hud is not None:
    ctx.current_actions = []
    _available_modes = ctx.director.available_modes()
    if not _available_modes:
        print("[Director] warning: no modes found in goals_dict")


def _init_hud_callbacks() -> None:
    """dispatch_action 定義後に呼び出される HUD コールバック初期化"""
    global _hud_cbs
    if not director_enabled or ctx.director_hud is None:
        return

    _hud_cbs = HUDCallbacks(
        ctx=ctx,
        get_action_spec=get_action_spec,
        pick_action=pick_action,
        dispatch_action=dispatch_action,
        ui_show_micro=ui_show_micro,
        director_clock_string=_director_clock_string,
        save_director_world=save_director_world,
        load_director_world=load_director_world,
        ensure_clock=ensure_clock,
        request_auto_step=request_auto_step,
    )
    _hud_cbs.bind_to_hud()

    # モードドロップダウンのバインド
    ctx.director_hud.set_modes(_available_modes, on_change=_hud_cbs.on_mode_dropdown)
    ctx.director_hud.set_mode(ctx.director.mode)
    ctx.director_hud.set_auto_enabled(ctx.auto_enabled)
    _hud_cbs.on_show_micro()


# HUDCallbacks へのデリゲート関数（後方互換性のため）
def refresh_hud() -> None:
    if _hud_cbs is not None:
        _hud_cbs.refresh_hud()


def ai_step_once() -> None:
    if _hud_cbs is not None:
        _hud_cbs.ai_step_once()


def set_auto(enabled: bool) -> None:
    if _hud_cbs is not None:
        _hud_cbs.set_auto(enabled)
    else:
        ctx.set_auto(enabled)


def maybe_run_auto() -> None:
    if _hud_cbs is not None:
        _hud_cbs.maybe_run_auto()
    elif ctx.game_state.get("auto_step_pending"):
        ctx.game_state["auto_step_pending"] = False


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

hud_refresh_cb = globals().get("refresh_hud")
ctx.pipeline = ActionPipeline(
    game_state=ctx.game_state,
    director=ctx.director,
    emit_director_scenes=write_scenes_to_scene_graph,
    ui_refresh=hud_refresh_cb if callable(hud_refresh_cb) else None,
    hud_set_clock=(ctx.director_hud.set_clock if ctx.director_hud else None),
    hud_set_microgoal=(ctx.director_hud.set_microgoal if ctx.director_hud else None),
    # advance_time uses ActionPipeline's built-in _advance_time
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


# HUD コールバックを初期化（dispatch_action 定義後）
_init_hud_callbacks()


# ---------------- ワールド Tick コールバック ----------------
def world_tick_cb(gs):
    if not gs.get("running", False):
        return

# ---------------- RC Tick コールバック ----------------
def rc_tick(rc_char, gs):
    if not rc_char.is_npc:
        return

    now = time.time()

    # レバーA: 意思決定頻度制限
    interval = get_rc_decision_interval_sec()
    last_action_time = gs.get("_rc_last_action_time", 0.0)
    if now - last_action_time < interval:
        # 間隔未満なら待機して再登録
        ctx.scheduler.register(rc_tick, 0.1, rc_char, gs)
        return

    # レバーB: 入力待ち中の時間予算チェック
    if gs.get("input_pending"):
        max_minutes = get_rc_max_advance_minutes()
        advanced = gs.get("_rc_minutes_advanced_while_pending", 0)
        if advanced >= max_minutes:
            # 予算超過：推薦だけして実行しない（レバーC: no-op）
            ctx.scheduler.register(rc_tick, 0.5, rc_char, gs)
            return
        # 予算内でも入力待ち中は抑制的に（再登録間隔を長めに）
        # pass through で実行を許可するが、次の登録は長めに

    # 現時点で実行可能な choice 一覧を取得
    choices = get_available_choices(rc_char, gs)

    # AI に選択させる
    choice = select_action(rc_char, gs, choices)
    if not choice:
        return

    # アクション実行
    try:
        act_info = actions[choice.action_key]
    except KeyError:
        # id_aliasesで見つからない場合はget_action_specを使用
        act_info = {}
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

    # RC実行時刻を記録（レバーA用）
    gs["_rc_last_action_time"] = time.time()

    # switch_characterがブロックされた場合（result=None）、フォールバック選択をログ
    if choice.action_key == "switch_character" and result is None:
        # 緑アクションにフォールバック
        from src.requirements_checker import RequirementsChecker
        checker = RequirementsChecker(gs, rc_char)
        green = [c for c in choices if c.emotion_axis == "green" and c.action_key != "switch_character" and c.is_available(checker)]
        if green:
            candidates = ", ".join(f"{c.label}({c.emotion_value})" for c in green)
            print(f"[RC_AI] {rc_char.name}: switch BLOCKED → フォールバック候補=[{candidates}]")
            from random import choices as rnd_choices
            weights = [c.emotion_value for c in green]
            fallback = rnd_choices(green, weights=weights, k=1)[0]
            print(f"[RC_AI] {rc_char.name}: → {fallback.label} にフォールバック")
            # フォールバックアクションを実行
            try:
                fb_info = actions[fallback.action_key]
            except KeyError:
                fb_info = {}
            fb_args = parse_args(fb_info, rc_char, gs)
            result = dispatch_action(
                fallback.action_key,
                actor_obj=rc_char,
                args=list(fb_args),
                source="RC_AI",
            )
            record(f"[AI] {rc_char.name} ▶ {fallback.action_key} (fallback)")
        else:
            print(f"[RC_AI] {rc_char.name}: switch BLOCKED, フォールバック候補なし")
    else:
        record(f"[AI] {rc_char.name} ▶ {choice.action_key}")

    if isinstance(result, CharacterStatus) and result.is_npc:
        ctx.scheduler.register(rc_tick, 0.5, result, gs)

    # 次の RC Tick を再登録（入力待ち中は長めに、通常時は設定間隔）
    if rc_char.is_npc:
        next_interval = interval if not gs.get("input_pending") else max(interval, 0.5)
        ctx.scheduler.register(rc_tick, next_interval, rc_char, gs)

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
            actor_id = actor.name if actor is not None and hasattr(actor, "name") else None
            get_for_actor = getattr(ctx.director, "get_micro_goal_for_actor", None)
            if callable(get_for_actor):
                micro_goal = get_for_actor(dw, actor_id, reroll=False)
            else:
                micro_goal = ctx.director.get_micro_goal(dw, reroll=False)
            ui_show_micro(micro_goal, gs, actor_id)
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
        # Choice生成時のactor_idを使用（キャラ切替されても正しいactorで実行）
        choice_actor = None
        if cmd.isdigit():
            idx = int(cmd)
            if idx in num_choice_map:
                selected_choice = num_choice_map[idx]
                # actor_idからactorを復元（スナップショット時のactor）
                if selected_choice.actor_id:
                    choice_actor = gs["party"].get(selected_choice.actor_id)
                # action_key と対象キャラ名を組み合わせて文字列化
                cmd = selected_choice.action_key
                if selected_choice.action_key == "switch_character":
                    # シンプルに Actor 以外の最初のキャラをターゲット
                    exec_actor = choice_actor or actor
                    others = [c for c in gs["party"].values() if c is not exec_actor]
                    cmd += f" {others[0].name}" if others else ""

        # 実行に使うactor（Choice経由ならスナップショット、それ以外は現在のactor）
        exec_actor = choice_actor or actor

        # プレイヤーが操作する瞬間に必ず手動フラグを立て直す
        exec_actor.is_npc = False
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
            actor_obj=exec_actor,
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
