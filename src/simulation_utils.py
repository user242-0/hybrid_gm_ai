# simulation_utils.py （場所は任意）
import json
from src.event_bus import log_q   # ※使わないなら削除可

from src.choice_definitions   import choice_definitions
from src.action_definitions   import actions
from src.requirements_checker import RequirementsChecker
from src.utility.args_parser    import parse_args            # 既にある util を想定
from src.logger               import log_action
#register用import
from src.character_status import CharacterStatus
# --- 不要な import を削除 ---
# from src.simulation_e import rc_tick
# from src.scheduler import Scheduler

#以下、datalab用インポート
import re
from pathlib import Path
from datalab.registry.action_registry import normalize_action
from datalab.emitters.scene_graph_emitter import emit_scene_graph
from schemas.scene_graph import ObjectSpec, Pose

SCENE_EMIT_ON = True           # 一旦ハードコード。後でconfig化
SCENE_JOB_DIR = Path("jobs/quick/")  # とりあえず固定。後で日付ジョブに

LOG_RE = re.compile(r"^\[PLY\]\s+(?P<player>.+?)\s+▶\s+(?P<key>\w+)\s*(?P<args>.*)$")

def emit_from_log_if_good(moment_text: str):
    """
    既存のログ1行を受け取って、条件に合えば scene_graph.yml を吐く。
    """
    if not SCENE_EMIT_ON:
        return
    m = LOG_RE.match(moment_text)
    if not m:
        return

    key = m.group("key")
    args = m.group("args").strip().split() if m.group("args") else []
    action = normalize_action(key, args)
    if action not in {"swing_sword", "crouch_ready"}:  # まず2語彙だけ拾う
        return

    # とりあえず決め打ち：Knightを2パターン出す（後で可変に）
    objs = [
        ObjectSpec(
            name="Knight_A",
            category="character",
            base_prompt="chibi knight in plate armor",
            action="swing_sword",
            pose=Pose(kind="skeleton", ref="controls/poses/swing_A.json"),
            materials_hint=["steel_brushed","leather_soft"],
            scale={"height_m": 1.2},
        ),
        ObjectSpec(
            name="Knight_B",
            category="character",
            base_prompt="chibi knight ready stance",
            action="crouch_ready",
            pose=Pose(kind="skeleton", ref="controls/poses/ready_crouch.json"),
        ),
    ]
    emit_scene_graph(
        job_root=SCENE_JOB_DIR,
        theme="古城の回廊での稽古",
        background="torch-lit stone corridor",
        objects=objs,
        loras=["ferlon_style_v1"],
    )

# --- 追加 ---
DEBUG_SCENE = True

def emit_from_choice(player_name: str, key: str, args: list[str]):
    if not SCENE_EMIT_ON:
        return
    action = normalize_action(key, args)
    if DEBUG_SCENE:
        print(f"[SCENE] player={player_name} key={key} args={args} -> action={action}")
    if action not in {"swing_sword", "crouch_ready"}:
        return

    objs = [
        ObjectSpec(
            name="Knight_A",
            category="character",
            base_prompt="chibi knight in plate armor",
            action="swing_sword",
            pose=Pose(kind="skeleton", ref="controls/poses/swing_A.json"),
            materials_hint=["steel_brushed","leather_soft"],
            scale={"height_m": 1.2},
        ),
        ObjectSpec(
            name="Knight_B",
            category="character",
            base_prompt="chibi knight ready stance",
            action="crouch_ready",
            pose=Pose(kind="skeleton", ref="controls/poses/ready_crouch.json"),
        ),
    ]
    emit_scene_graph(
        job_root=SCENE_JOB_DIR,
        theme="古城の回廊での稽古",
        background="torch-lit stone corridor",
        objects=objs,
        loras=["ferlon_style_v1"],
    )


def execute_player_choice(player, cmd: str, game_state):
    """
    cmd は GUI で入力した文字列（例: 'attack' / '1' / 'switch Hero'）
    1) Choice を特定し requirements をチェック
    2) 対応する action.function を呼び出す
    3) ログを残す（persist   + 画面用 log_q）
    """
    # ---- (1) 入力文字列を Choice にマッピング ----
    #   例: 数字なら choice_definitions のインデックス順で解釈 など
    # 入力を解析
    if cmd.isdigit():
        idx = int(cmd) - 1
        keys = list(choice_definitions.keys())
        if idx < 0 or idx >= len(keys):
            game_state["last_action_note"] = {"text": f"⚠ 無効な番号: {cmd}", "tag": "red"}
            return
        key = keys[idx]
        rest = []
    else:
        parts = cmd.split()
        key  = parts[0] if parts else ""
        rest = parts[1:] if len(parts) > 1 else []

    if key not in choice_definitions:
        game_state["last_action_note"] = {"text": f"⚠ 無効なコマンド: {cmd}", "tag": "red"}
        return

    choice_meta = choice_definitions[key]
    action_info = actions[key]
    checker = RequirementsChecker(game_state, player)
    if not checker.check_all(action_info.get("requirements")):
        game_state["last_action_note"] = {"text": f"⚠ 実行条件を満たしていません: {key}", "tag": "red"}
        return

    # まずGUIで自動解決できる引数は埋める
    args = list(rest)
    if not args:
        if key == "攻撃する":
            enemy = game_state.get("enemy")
            if enemy:
                args = [enemy.name]
            elif game_state.get("current_target"):
                # 例：初期状態だと「古代の石像」を攻撃対象にする
                args = [game_state["current_target"]]
    # まだ空なら汎用パーサに委譲（※ 文字列ではなく CharacterStatus を渡す）
    if not args:
        args = parse_args(action_info, player, game_state)

    result = action_info["function"](player, game_state, *args)


    # ---- (3) ログ出力 ----
    # 3-a) 永続ログ
    log_action(
        actor      = player.name,
        action_key = key,
        target     = " ".join(args) if args else "",
        result     = result,
        #game_state = game_state,
    )
    # 3-b) 画面ノート（次の手番で α として出す）
    line = f"[PLY] {player.name} ▶ {key} {' '.join(args)}"
    game_state["last_action_note"] = {
        "text": line,
        "tag":  "green"
    }
    emit_from_choice(player.name, key, args)

    return result       # ← 戻り値として返すだけ
