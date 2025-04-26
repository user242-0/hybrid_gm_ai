# simulation.py
# ログ録り用モジュール
import json
from datetime import datetime
import os
# ゲーム用モジュール
from CharacterStatus import CharacterStatus
from actions import actions
from action_functions import determine_next_location, generate_dynamic_event, generate_location_event, choose_event_parameters, present_event_choices
from requirements_checker import RequirementsChecker
from logger import log_action
from conversation_manager import ConversationManager

# デバッグ
import traceback

# simulation.py の先頭に追加
from colorama import Fore, Style, init

# coloramaを初期化（最初に一度）
init(autoreset=True)

# 中略...

# simulation.pyの冒頭部分
conversation_manager = ConversationManager()


def main():
    player = CharacterStatus(name="プレイヤー")
    game_state = {
        "has_enemy": True,
        "enemy": {"name": "洞窟のゴブリン", "hp": 20, "attack_power": 4},
        "is_safe_zone": True,
        "available_items": [],
        "events": {
            "statue_trial_unlocked": False
        },
        "current_location": "力の洞窟", 
        "current_target": "古代の石像"
    }
    conversation_key = f"{player.name}_{game_state['current_target']}"
    checker = RequirementsChecker(game_state, player)

    while True:
        # UIを青く表示
        print(Fore.BLUE + "\n=== 選択可能なアクション ===" + Style.RESET_ALL)

        available_actions = {
            key: action for key, action in actions.items()
            if "player" in action.get("available_to", [])
            and checker.check_all(action.get("requirements"))
        }

        if not available_actions:
            print(Fore.BLUE + "現在実行可能なアクションがありません。" + Style.RESET_ALL)
            break

        for i, (action_key, action) in enumerate(available_actions.items(), start=1):
            print(Fore.BLUE + f"{i}. {action_key} - {action['description']}" + Style.RESET_ALL)

        try:
            choice = int(input(Fore.BLUE + "行動番号を選んでください（0で終了）: " + Style.RESET_ALL)) - 1
            if choice == -1:
                break
            if choice < 0 or choice >= len(available_actions):
                print(Fore.BLUE + "無効な選択です。再度選択してください。" + Style.RESET_ALL)
                continue

            selected_action_key = list(available_actions.keys())[choice]
            selected_action = available_actions[selected_action_key]
            effect = selected_action["effects"]["function"]
            args = selected_action["effects"].get("args", [])



            # 会話関連アクションの場合のみ履歴更新するよう修正
            if selected_action_key in ["石像に話す", "石像に話す（クールダウン）"]:
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


            # アクション実行
            result = effect(player, game_state, *args)

            if selected_action_key in ["石像に話す（クールダウン）"]:
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



            # log_actionはすべてのアクションで実行
            log_action(
                actor=player.name,
                action=selected_action_key,
                target=game_state.get("current_target", "なし"),
                location=game_state.get("current_location", "不明"),
                result=result,
                game_state=game_state
            )


        except ValueError:
            print(Fore.GREEN + "数値を入力してください。" + Style.RESET_ALL)

        except Exception as e:
            print(Fore.RED + f"エラーが発生しました: {e}" + Style.RESET_ALL)
            traceback.print_exc()


def run_simulation_step(character, global_game_state, controlled_by_ai=False):
    current_location = character.location
    current_state = global_game_state[current_location]

    available_actions = []
    checker = RequirementsChecker(current_state, character)

    for action_name, details in actions.items():
        if checker.check_all(details["requirements"]):
            available_actions.append(action_name)

    # AI制御の場合は表示をOFF
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
        # AIの場合は自動選択（ランダム・もしくは戦略的に）
        selected_action_name = available_actions[0]  # 例として最初の行動を選択

    action_details = actions[selected_action_name]
    function_to_execute = action_details["effects"]["function"]
    args = action_details["effects"]["args"]

    result = function_to_execute(character, current_state, *args)

    if not controlled_by_ai:
        # プレイヤー操作の場合のみ結果表示
        print(f"行動結果：{result}")

    log_action(
        actor=character.name,
        action=selected_action_name,
        target=args[0] if args else None,
        location=current_location,
        result=result,
        game_state=current_state
    )

if __name__ == "__main__":
    # 敵対的NPC設定
    enemy_npc = CharacterStatus("敵対的NPC", hp=80, attack_power=10)
    enemy_npc.location = "力の洞窟"


    # 世界全体の状態（場所ごと）
    global_game_state = {
        "力の洞窟": {
            "has_enemy": True,
            "enemy": {"name": "洞窟のゴーレム", "hp": 50, "attack_power": 8}
        },
        "祭壇": {
            "has_enemy": False,
            "enemy": None
        }
    }

    # プレイヤーの初期位置
    player = CharacterStatus("プレイヤー")
    player.location = "力の洞窟"
    global_game_state["力の洞窟"]["has_enemy"] = True
    global_game_state["力の洞窟"]["enemy"] = {
        "name": player.name,
        "hp": player.hp,
        "attack_power": player.attack_power
    }

    # プレイヤー（手動操作）
    run_simulation_step(player, global_game_state)

    # 敵対的NPC（AI制御）
    run_simulation_step(enemy_npc, global_game_state, controlled_by_ai=True)