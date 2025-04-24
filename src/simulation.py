# simulation.py
# ログ録り用モジュール
import json
from datetime import datetime
import os
# ゲーム用モジュール
from CharacterStatus import CharacterStatus
from actions import actions
from requirements_checker import RequirementsChecker
from logger import log_action, classify_talk_situation # simulation.pyでもloggerからインポートする

# デバッグ
import traceback

# simulation.py の先頭に追加
from colorama import Fore, Style, init

# coloramaを初期化（最初に一度）
init(autoreset=True)

# 中略...

# simulation.pyの冒頭部分
conversation_history = {}


def main():
    global conversation_history  # これが必要

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


            # アクション実行
            result = effect(player, game_state, *args)

            # 成功時の表示も青く
            print(Fore.BLUE + "アクションが正常に実行されました。" + Style.RESET_ALL)

            # 会話関連アクションの場合のみ履歴更新するよう修正
            if selected_action_key in ["石像に話す", "石像に話す（クールダウン）"]:
                conversation_key = f"{player.name}_{game_state['current_target']}"

                if conversation_key in conversation_history:
                    last_talk_time_str = conversation_history[conversation_key]["last_talk_time"]
                    count = conversation_history[conversation_key]["talk_count"]

                    # 安全な型変換処理
                    if isinstance(last_talk_time_str, str):
                        last_talk_time = datetime.fromisoformat(last_talk_time_str)
                    else:
                        last_talk_time = last_talk_time_str

                    interval = (datetime.now() - last_talk_time).total_seconds()
                    talk_count = count + 1
                else:
                    interval = None
                    talk_count = 1

                # game_state更新
                game_state["talk_count"] = talk_count
                game_state["interval"] = interval
                game_state["talk_situation"] = classify_talk_situation(talk_count, interval)

                # 履歴を更新
                conversation_history[conversation_key] = {
                    "last_talk_time": datetime.now().isoformat(),
                    "talk_count": talk_count
                }

            else:
                # 会話以外のアクションでは履歴の更新をしない、またはデフォルトを明確に設定
                game_state["talk_count"] = None
                game_state["interval"] = None
                game_state["talk_situation"] = ["normal"]
                talk_count = 0  # 会話以外のアクションでは明示的に初期化

            # log_actionはすべてのアクションで実行
            log_action(
                actor=player.name,
                action=selected_action_key,
                target=game_state.get("current_target", "なし"),
                location=game_state.get("current_location", "不明"),
                result=result
            )


        except ValueError:
            print(Fore.GREEN + "数値を入力してください。" + Style.RESET_ALL)

        except Exception as e:
            print(Fore.RED + f"エラーが発生しました: {e}" + Style.RESET_ALL)
            traceback.print_exc()



if __name__ == "__main__":
    main()
