# simulation_utils.py （場所は任意）
import json
from event_bus import log_q

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

def execute_player_choice(player, cmd: str, game_state):
    """
    cmd は GUI で入力した文字列（例: 'attack' / '1' / 'switch Hero'）
    1) Choice を特定し requirements をチェック
    2) 対応する action.function を呼び出す
    3) ログを残す（persist   + 画面用 log_q）
    """
    # ---- (1) 入力文字列を Choice にマッピング ----
    #   例: 数字なら choice_definitions のインデックス順で解釈 など
    if cmd.isdigit():
        idx = int(cmd) - 1
        key = list(choice_definitions.keys())[idx]
    else:
        # 'switch Hero' → ['switch','Hero']
        key, *rest = cmd.split()
    if key not in choice_definitions:
        log_q.put(f"[ERR] Unknown command: {cmd}")
        return

    choice_meta = choice_definitions[key]
    checker = RequirementsChecker(game_state, player)
    if not checker.check_all(choice_meta.get("requirements", [])):
        log_q.put(f"[ERR] Requirements not met: {key}")
        return

    # ---- (2) Action 呼び出し ----
    action_info = actions[key]
    # 固定で 1 つだけ追加引数がある例（switch_character）
    args = rest or parse_args(action_info, player.name, game_state)
    result = action_info["function"](player, game_state, *args)


    # ---- (3) ログ出力 ----
    # 3-a) 永続ログ
    log_action(
        actor      = player.name,
        action_key = key,
        target     = " ".join(args) if args else "",
        result     = result,
        game_state = game_state,
    )
    # 3-b) 画面ログ
    log_q.put(f"[PLY] {player.name} ▶ {key} {' '.join(args)}")

    return result       # ← 戻り値として返すだけ
