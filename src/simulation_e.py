# simulation.py
# ログ録り用モジュール
import json
from datetime import datetime
import os
# ターゲット選択時に使う
import random

# ゲーム用モジュール
from src.character_status import CharacterStatus
from src.control_manager   import switch_control
from src.init_state  import init_game_state

# functions import
from src.actions import determine_next_location, generate_dynamic_event, generate_location_event, choose_event_parameters, present_event_choices, pre_combat_moment, npc_speak, npc_speak_and_log
# dictionary import
from src.action_definitions import actions

from src.requirements_checker import RequirementsChecker
from src.utility.targeting import get_contextual_target, prompt_target_rc
from src.logger import log_action
from src.conversation_manager import ConversationManager

# emotion color import
from choice_definitions import choice_definitions
from src.choice_model import Choice

#gui import
from src.event_bus import event_q, log_q
import threading, time
from gui          import start_gui
from queue import Empty        # ← 追加

# 追加import
from src.scheduler import Scheduler
from src.rc_ai import select_action
from src.choice_definitions import get_available_choices
from src.utility.args_parser import parse_args

# execute_player_choice import
from src.simulation_utils import execute_player_choice
from src.choice_ui import present_choices

# デバッグ
import traceback

# simulation.py の先頭に追加
from colorama import Fore, Style, init

# coloramaを初期化（最初に一度）
init(autoreset=True)

# 安全に終了したい
from src.quit_helper import handle_quit

# 中略...
USE_CLI = False     # True にすると黒い端末だけでプレイ

# simulation.pyの冒頭部分
conversation_manager = ConversationManager()


# --- 起動時に Scheduler 用意 ---
scheduler = Scheduler()
game_state = init_game_state()    # ★ ここで一度だけ生成

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

    # ② メインループ
    while gs["running"]:
        while scheduler.run_once():          # due を全部消化
            pass
        actor = gs["active_char"]
        # ▼ CLI で直接 input() する場合（GUI を使わないモード）
        if USE_CLI:
            gs["input_pending"] = True
            raw = input(">> ").strip()
            gs["input_pending"] = False
            handle_quit(raw, gs)          # ★ ここで判定
            cmd = raw                     # → 後続処理へ

        # ▼ GUI モード：Entry から event_q を受信
        else:
            gs["input_pending"] = True
            try:
                num_choice_map = present_choices(actor, gs)     # ← dict を受け取る
                cmd = event_q.get(timeout=0.05)
            except Empty:
                continue
            finally:
                gs["input_pending"] = False
            handle_quit(cmd, gs)          # ★ ここでも同じ
        

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



        # 旧プレイヤーが CharacterStatus なら AI キューに登録
        if isinstance(result, CharacterStatus):
            print('[REG]', result.name, result.is_npc)
            scheduler.register(rc_tick, 0.01, result, gs)
        # flush AI 行動
        while scheduler.run_once() is not None:
            pass

        # 操作キャラが変わっている可能性があるので再表示
        present_choices(gs["active_char"], gs)

choices = []
for label, meta in choice_definitions.items():
    if label in actions:
        axis = meta["axis"]
        value = meta.get("value", 255)
        req = actions[label].get("requirements")
        choices.append(Choice(label, label, axis, value, requirements=req))

def rgb_to_ansi(r, g, b):
    return f"\033[38;2;{r};{g};{b}m"  # 文字色をRGBで指定

def display_choices_with_emotion(choices, player_emotion_color):
    for i, choice in enumerate(choices, start=1):
        r, g, b = choice.get_emotion_x_player_scaled_color(player_emotion_color)
        color_code = rgb_to_ansi(r, g, b)
        print(f"{color_code}{i}. {choice.label}{Style.RESET_ALL}")

def choose_target_for_switch(rc_char, game_state):
    # rc_charが現在アクティブでないなら、自分自身をターゲット（プレイヤー操作役に）する
    if game_state["active_char"] is not rc_char:
        return rc_char.name
    # rc_charがアクティブキャラの場合は、他の候補から選ぶ（従来処理）
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
            time.sleep(1)
    except SystemExit:
        pass                        # どこかのスレッドで raise SystemExit 渡ってきたら即終了

#-----------------以下は旧実装--------------------------
def main():
    # ① 二重生成をやめる
    player   = CharacterStatus("Hero", faction="player", is_rc=True, is_npc=False)
    player.equip_weapon({"name": "鉄の剣", "attack_bonus": 5})
    luna     = CharacterStatus("ルナ",       faction="player", is_rc=True, is_npc=True)
    ally     = CharacterStatus("仲間NPC",    faction="player", is_rc=True, is_npc=True)
    goblin   = CharacterStatus("ゴブリン",   faction="enemy",  is_rc=True,  is_npc=True)
    merchant = CharacterStatus("旅の商人",   faction="neutral", is_rc=False)

    party = {c.name: c for c in (player, luna)}   # ← goblin も入れると切替可
    player.is_active = True

    game_state = {
        "active_char": player,            # ← ここは上で作った player の参照を使う
        "party": party,
        "has_enemy": True,
        "enemy": goblin,                  # そのままオブジェクトを保持
        "is_safe_zone": True,
        "available_items": [],
        "events": {
            "statue_trial_unlocked": False
        },
        "current_location": "祭壇",
        "current_target": "古代の石像"
    }

    conversation_key = f"{player.name}_{game_state['current_target']}"
    
    
    # 起動時に 全キャラ分 登録する
    for ch in game_state["party"].values():
        scheduler.register(rc_tick, 0.2, ch, game_state)

    while True:
        # UIを青く表示
        player = game_state["active_char"]
        checker = RequirementsChecker(game_state, player)
        print(Fore.BLUE + "\n=== {}(あなた)の 選択可能なアクション ===".format(player.name) + Style.RESET_ALL)


        # 利用可能な選択肢の抽出
        available_choices = []
        for choice in choices:
            action = actions.get(choice.action_key)
            if action and "player" in action.get("available_to", []) and checker.check_all(action.get("requirements", {})):
                available_choices.append(choice)

        # 選択肢の表示
        display_choices_with_emotion(available_choices, player.emotion_color)

        # ユーザーの選択
        choice_index = int(input(Fore.BLUE + "行動番号を選んでください（0で終了）: " + Style.RESET_ALL)) - 1
        if choice_index == -1:
                break
        if 0 <= choice_index < len(available_choices):
            selected_choice = available_choices[choice_index]
            selected_action = actions[selected_choice.action_key]
            actor=game_state["active_char"].name
            effect = selected_action["function"]
            args = parse_args(selected_action, player.name, game_state)
            result = effect(player, game_state, *args)

            

            # 必要に応じて結果の処理を追加

            # switch_charactorしたら新たに NPC になったキャラを 0.01 s 後に AI キューへ
            if selected_choice.action_key in ["switch_character"]:
                prev_ai =result
                scheduler.register(rc_tick, 0.01, prev_ai, game_state)
            
            # 会話関連アクションの場合のみ履歴更新するよう修正
            if selected_choice.action_key in ["石像に話す", "石像に話す（クールダウン）"]:
                actor = player.name
                target = game_state.get('current_target', 'なし')
                
                # 会話履歴を更新
                conversation_manager.update_conversation(actor, target)
                # game_state更新
                game_state["talk_count"] = conversation_manager.get_talk_count(actor, target)
                game_state["talk_situation"] = conversation_manager.get_talk_situation(actor, target)
                game_state["interval"] = conversation_manager.get_interval(actor, target)

            else:
                # 会話以外のアクションでは履歴の更新をしない、またはデフォルトを明確に設定
                game_state["talk_count"] = None
                game_state["interval"] = None
                game_state["talk_situation"] = ["normal"]
                talk_count = 0  # 会話以外のアクションでは明示的に初期化



            if selected_choice.action_key in ["石像に話す（クールダウン）"]:
                game_state["player_choice"] = result["player_choice"]
                # 次のロケーションを決定
                determine_next_location(game_state)

                # 動的イベントを生成
                generate_dynamic_event(game_state["player_choice"], game_state)

                event_type, difficulty = choose_event_parameters()

                event_description = generate_location_event(
                    location=game_state["location"],
                    event_type=event_type,
                    player_choice=game_state["player_choice"],
                    difficulty=difficulty
                )

                print(f"\n【イベントタイプ】：{event_type}（難易度：{difficulty}）")
                print(f"イベント内容：{event_description}")

                choice_result = present_event_choices(event_type)

                if choice_result:
                    # 選択肢に応じてステータス変動
                    player.change_status(
                        hp_change=choice_result["hp"],
                        stamina_change=choice_result["stamina"],
                        attack_power_change=choice_result["attack"]
                    )

                    print(f"\nあなたは「{choice_result['description']}」を選択しました。")
                    # 結果の描写や追加ロジックも可能
                else:
                    print("\n無効な選択がされました。行動をスキップします。")
            # 成功時の表示も青く
            print(Fore.BLUE + "アクションが正常に実行されました。" + Style.RESET_ALL)
            #print("[DEBUG] candidates:", list_switch_candidates(game_state))

            target_for_log = get_contextual_target(selected_choice.action_key, actor, game_state, *args)
            # log_actionはすべてのアクションで実行
            if selected_choice.action_key == "switch_character":
                log_action(
                    actor= actor,   # 実際に動いたキャラ,
                    action=selected_choice.action_key,
                    target=target_for_log,
                    location=game_state.get("current_location", "不明"),
                    result="操作キャラクターを{}に切り替えた".format(target_for_log),
                    game_state=game_state
                )
            
            else:log_action(
                    actor= actor,   # 実際に動いたキャラ,
                    action=selected_choice.action_key,
                    target=target_for_log,
                    location=game_state.get("current_location", "不明"),
                    result=result,
                    game_state=game_state
                )

        else:
            print(Fore.BLUE + "無効な選択です。再度選択してください。" + Style.RESET_ALL)

        scheduler.run_once() 





def list_switch_candidates(game_state, allow_enemy=False):
    return [
        m.name for m in game_state["party"].values()
        if m.is_rc and not m.is_active and
           (allow_enemy or m.faction == "player")
    ]

       

def run_simulation_step(character, global_game_state, controlled_by_ai=False, opponent_character=None):
    current_location = character.location
    current_state = global_game_state[current_location]

    available_actions = []
    checker = RequirementsChecker(current_state, character)

    for action_name, details in actions.items():
        if checker.check_all(details["requirements"]):
            available_actions.append(action_name)

    if controlled_by_ai and opponent_character and current_state.get("has_enemy"):
        # NPCがセリフを喋り、ログに記録する
        npc_speak_and_log(character.name, "combat_start", current_location, current_state)

        # プレイヤーにモーメントを提供
        pre_combat_moment(opponent_character, character, current_state)
        return


    if not controlled_by_ai:
        print(f"\n{character.name}（現在地：{current_location}）の行動可能リスト:")
        for idx, act in enumerate(available_actions, 1):
            print(f"{idx}. {act}：{actions[act]['description']}")

        selected_idx = input("\n番号を選択してください: ")
        try:
            selected_action_name = available_actions[int(selected_idx)-1]
        except (IndexError, ValueError):
            print("無効な入力です。")
            return
    else:
        selected_action_name = available_actions[0]

    action_details = actions[selected_action_name]
    function_to_execute = action_details["function"]
    args = parse_args(action_details, character.name, global_game_state)

    result = function_to_execute(character, current_state, *args)

    if not controlled_by_ai:
        print(f"行動結果：{result}")

    log_action(
        actor=character.name,
        action=selected_action_name,
        target=args[0] if args else None,
        location=current_location,
        result=result,
        game_state=current_state
    )


def pre_combat_moment(player, enemy_npc, game_state):
    moment_actions = ["戦う", "戦わない", "ただ、受け入れる"]

    print(f"\n【緊迫のモーメント】{enemy_npc.name}があなたに敵意を向けています……")
    print("あなたはどうしますか？")
    for idx, act in enumerate(moment_actions, 1):
        print(f"{idx}. {act}：{actions[act]['description']}")

    choice = input("番号を選択してください（1～3）: ")

    try:
        selected_action_name = moment_actions[int(choice)-1]
    except (IndexError, ValueError):
        print("無効な入力です。何もしませんでした。")
        return

    # アクション実行
    action_details = actions[selected_action_name]
    function_to_execute = action_details["function"]
    # 「戦う」だけは敵を引数として渡す約束のままにする（engage_combat 側の既存インタフェース維持）
    result = (function_to_execute(player, game_state, enemy_character_status=enemy_npc)
              if selected_action_name == "戦う"
              else function_to_execute(player, game_state))

    print(f"行動結果：{result}")

    # ログに記録
    log_action(
        actor=player.name,
        action=selected_action_name,
        target=enemy_npc.name,
        location=player.location,
        result=result,
        # game_state=game_state
    )


