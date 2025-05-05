# simulation.py
# ログ録り用モジュール
import json
from datetime import datetime
import os
# ゲーム用モジュール
from src.character_status import CharacterStatus
from src.control_manager   import switch_control

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

# デバッグ
import traceback

# simulation.py の先頭に追加
from colorama import Fore, Style, init

# coloramaを初期化（最初に一度）
init(autoreset=True)

# 中略...

# simulation.pyの冒頭部分
conversation_manager = ConversationManager()

def init_game_state():
    hero = CharacterStatus("Hero", is_rc=True)      # 主人公自身も RC 扱いにすると後々ラク
    npc  = CharacterStatus("Luna", is_rc=True)

    party = {c.name: c for c in (hero, npc)}
    hero.is_active = True        # 初期操作キャラ

    return {
        "party": party,
        "active_char": hero,
        # 既存キー(game_turn 等)はそのまま
    }

choices = []

for label, meta in choice_definitions.items():
    if label in actions:
        axis = meta["axis"]
        value = meta.get("value", 255)
        choices.append(Choice(label, label, axis, value))

def rgb_to_ansi(r, g, b):
    return f"\033[38;2;{r};{g};{b}m"  # 文字色をRGBで指定

def display_choices_with_emotion(choices, player_emotion_color):
    for i, choice in enumerate(choices, start=1):
        r, g, b = choice.get_emotion_x_player_scaled_color(player_emotion_color)
        color_code = rgb_to_ansi(r, g, b)
        print(f"{color_code}{i}. {choice.label}{Style.RESET_ALL}")

def main():
    # ① 二重生成をやめる
    player   = CharacterStatus("プレイヤー", faction="player", is_rc=True)
    player.equip_weapon({"name": "鉄の剣", "attack_bonus": 5})
    luna     = CharacterStatus("ルナ",       faction="player", is_rc=True)
    ally     = CharacterStatus("仲間NPC",    faction="player", is_rc=True)
    goblin   = CharacterStatus("ゴブリン",   faction="enemy",  is_rc=True)
    merchant = CharacterStatus("旅の商人",   faction="neutral", is_rc=False)

    party = {c.name: c for c in (player, luna, ally, goblin)}   # ← goblin も入れると切替可
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
    
    while True:
        # UIを青く表示
        player = game_state["active_char"]
        checker = RequirementsChecker(game_state, player)
        print(Fore.BLUE + "\n=== 選択可能なアクション ===" + Style.RESET_ALL)


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
            log_action(
                actor= actor,   # 実際に動いたキャラ,
                action=selected_choice.action_key,
                target=target_for_log,
                location=game_state.get("current_location", "不明"),
                result=result,
                game_state=game_state
            )


        else:
            print(Fore.BLUE + "無効な選択です。再度選択してください。" + Style.RESET_ALL)









def list_switch_candidates(game_state, allow_enemy=False):
    return [
        m.name for m in game_state["party"].values()
        if m.is_rc and not m.is_active and
           (allow_enemy or m.faction == "player")
    ]

       
def parse_args(action_def, player, game_state):
    resolved = []
    for token in action_def.get("args_template", []):
        if token == "<target_name>":
            resolved.append(prompt_target_rc(game_state))
        else:
            resolved.append(token)
    return resolved

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
    function_to_execute = action_details["effects"]["function"]
    args = action_details["effects"]["args"]

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
    function_to_execute = action_details["effects"]["function"]
    args = action_details["effects"]["args"]

    result = function_to_execute(player, game_state, enemy_character_status=enemy_npc) if selected_action_name == "戦う" else function_to_execute(player, game_state)

    print(f"行動結果：{result}")

    # ログに記録
    log_action(
        actor=player.name,
        action=selected_action_name,
        target=enemy_npc.name,
        location=player.location,
        result=result,
        game_state=game_state
    )


if __name__ == "__main__":
    main()
