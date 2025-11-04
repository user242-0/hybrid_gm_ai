# simulation.py
# ターゲット選択時に使う
import random
from pathlib import Path
import yaml

# ゲーム用モジュール
from src.character_status import CharacterStatus
from src.init_state  import init_game_state

# dictionary import
from src.action_definitions import actions

#gui import
from src.event_bus import event_q, log_q
import threading, time
from gui          import start_gui
from queue import Empty        # ← 追加

# 追加import
from src.scheduler import Scheduler
from src.world import init_world, world_tick
from src.rc_ai import select_action
from src.choice_definitions import get_available_choices
from src.utility.args_parser import parse_args
from src.utility.config_loader import job_root_from_cfg, load_config
from director.director import Director, load_yaml

try:
    from tkinter import TclError
except ImportError:  # pragma: no cover - tkinter may be missing in headless environments
    TclError = Exception  # type: ignore

try:
    from src.ui.director_hud import DirectorHUD
except ImportError:  # pragma: no cover - optional dependency
    DirectorHUD = None  # type: ignore

# execute_player_choice import
from src.simulation_utils import execute_player_choice
from src.choice_ui import present_choices

# 安全に終了したい
from src.quit_helper import handle_quit

# 中略...
USE_CLI = False     # True にすると黒い端末だけでプレイ

# --- 起動時に Scheduler 用意 ---
scheduler = Scheduler()
game_state = init_game_state()    # ★ ここで一度だけ生成
init_world(game_state)

BASE_DIR = Path(__file__).resolve().parent.parent

cfg = load_config()
director_cfg = cfg.get("director", {})
director_enabled = bool(director_cfg.get("enabled", False))

director = None
director_world = None
director_hud = None
director_hud = None


def _director_clock_string(world: dict | None) -> str:
    if not world:
        return "Day1 08:00"
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
    return "Day1 08:00"

if director_enabled:
    premise_path = Path(director_cfg.get("premise_path", "data/director/premise.yml"))
    if not premise_path.is_absolute():
        premise_path = BASE_DIR / premise_path
    premise_doc = load_yaml(str(premise_path)) or {}
    premise = premise_doc.get("premise", {})
    goals_path = BASE_DIR / "data/director/cop_trickster_goals.yml"
    goals = load_yaml(str(goals_path)) or {}
    director = Director(premise=premise, goals_dict=goals)

    existing_world = game_state.get("director_world")
    if existing_world:
        director_world = existing_world
        director_world["reload_epoch"] = director_world.get("reload_epoch", 0) + 1
    else:
        director_world = director.synthesize_world()

    game_state["director_world"] = director_world
    game_state["director_micro_goal"] = None

    seed_value = premise.get("seed", director_cfg.get("seed"))
    title = premise.get("title", "")
    print(f"[Director] enabled seed={seed_value} premise='{title}'")

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


    def on_mode_change(new_mode: str) -> None:
        director.mode = new_mode
        director.clear_micro_goal(new_mode)
        director_hud.set_mode(new_mode)
        print(f"[Director] mode -> {new_mode}")
        on_show_micro()


    def on_show_micro() -> None:
        if director_world is None:
            return
        micro = director.get_micro_goal(director_world, reroll=False)
        ui_show_micro(micro, game_state)
        micro_text = micro or "(MicroGoal なし)"
        print(f"[UI] MicroGoal: {micro_text}")


    def on_reroll() -> None:
        if director_world is None:
            return
        micro = director.get_micro_goal(director_world, reroll=True)
        ui_show_micro(micro, game_state)
        micro_text = micro or "(MicroGoal なし)"
        print(f"[UI] MicroGoal (reroll): {micro_text}")


    def on_auto_action() -> None:
        if director_world is None:
            return
        director.apply_auto_step(director_world)
        scenes = director.tick(director_world)
        if scenes:
            write_scenes_to_scene_graph(scenes)
            for scene in scenes:
                print(
                    f"[SCENE] intent={scene.get('intent')} why_now={scene.get('why_now')} "
                    f"salience={scene.get('salience')}"
                )
        director_hud.set_clock(_director_clock_string(director_world))
        if director.is_micro_goal_done(director_world):
            director.clear_micro_goal()
        on_show_micro()


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
        if isinstance(director_world, dict):
            director_world["reload_epoch"] = director_world.get("reload_epoch", 0) + 1
        game_state["director_world"] = director_world
        director_hud.set_clock(_director_clock_string(director_world))
        director.clear_micro_goal()
        on_show_micro()
        reload_epoch = (
            director_world.get("reload_epoch") if isinstance(director_world, dict) else None
        )
        print(f"[LOAD] world loaded; reload_epoch={reload_epoch}")


    director_hud.on_mode_change = on_mode_change
    director_hud.on_auto_action = on_auto_action
    director_hud.on_reroll = on_reroll
    director_hud.on_save = on_save
    director_hud.on_load = on_load
    director_hud.on_show_micro = on_show_micro
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
    return loaded if isinstance(loaded, dict) else fallback


# ---------------- ワールド Tick コールバック ----------------
def world_tick_cb(gs):
    messages = world_tick(gs)
    for msg in messages:
        record(msg)

    if gs.get("running", False):
        delay = gs.get("clock", {}).get("dt", 0.5)
        scheduler.register(world_tick_cb, delay, gs)

# ---------------- RC Tick コールバック ----------------
def rc_tick(rc_char, game_state):
    #[DEBUG]
    print('[TICK]', rc_char.name, rc_char.is_npc)
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
        result = act_info["function"](rc_char, game_state, target_name)
    else:
        result = act_info["function"](rc_char, game_state, *args)

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

    scheduler.register(world_tick_cb, gs.get("clock", {}).get("dt", 0.5), gs)

    # ② メインループ
    while gs["running"]:
        while scheduler.run_once():          # due を全部消化
            if director_hud is not None:
                director_hud.pump()
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
        result = execute_player_choice(actor, cmd, gs)

        if director is not None and director_world is not None:
            scenes = director.tick(director_world)
            if scenes:
                write_scenes_to_scene_graph(scenes)
            if director_hud is not None:
                director_hud.set_clock(_director_clock_string(director_world))



        # 旧プレイヤーが CharacterStatus なら AI キューに登録
        if isinstance(result, CharacterStatus):
            print('[REG]', result.name, result.is_npc)
            scheduler.register(rc_tick, 0.01, result, gs)
        # flush AI 行動
        while scheduler.run_once() is not None:
            if director_hud is not None:
                _pump_director_hud()

        # 操作キャラが変わっている可能性があるので再表示
        present_choices(gs["active_char"], gs)
        if director_hud is not None:
            _pump_director_hud()
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


