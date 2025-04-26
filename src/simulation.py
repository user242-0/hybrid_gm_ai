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
        "is_safe_zone": True,
        "available_items": [],
        "events": {
            "statue_trial_unlocked": False
        },
        "current_location": "祭壇", 
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



if __name__ == "__main__":
    main()
