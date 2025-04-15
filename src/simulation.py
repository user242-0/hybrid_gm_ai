# simulation.py
# ログ録り用モジュール
import json
from datetime import datetime
import os
# ゲーム用モジュール
from CharacterStatus import CharacterStatus
from actions import actions
from requirements_checker import RequirementsChecker

# simulation.py の先頭に追加
from colorama import Fore, Style, init

# coloramaを初期化（最初に一度）
init(autoreset=True)

# 中略...

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
            effect(player, game_state, *args)

            # 成功時の表示も青く
            print(Fore.BLUE + "アクションが正常に実行されました。" + Style.RESET_ALL)

            # ログ記録
            log_action(
                actor=player.name,
                action=selected_action_key,
                target=game_state.get("current_target", "なし"),
                location=game_state.get("current_location", "不明"),
                result="成功"
            )

        except ValueError:
            print(Fore.BLUE + "数値を入力してください。" + Style.RESET_ALL)
            log_action(
                actor=player.name,
                action="アクション選択",
                target="なし",
                location=game_state.get("current_location", "不明"),
                result="数値入力エラーで失敗"
            )

        except Exception as e:
            print(Fore.BLUE + f"エラーが発生しました: {e}" + Style.RESET_ALL)
            log_action(
                actor=player.name,
                action=selected_action_key,
                target=game_state.get("current_target", "なし"),
                location=game_state.get("current_location", "不明"),
                result=f"例外エラー: {str(e)}"
            )


def log_action(actor, action, target, location, result):
    log_entry = {
        "timestamp": datetime.now().isoformat(),
        "actor": actor,
        "action": action,
        "target": target,
        "location": location,
        "result": result
    }
    
    # ログフォルダを用意する（無ければ作成）
    os.makedirs("data/logs", exist_ok=True)
    
    with open("data/logs/gameplay_blue_log.json", "a", encoding="utf-8") as logfile:
        logfile.write(json.dumps(log_entry, ensure_ascii=False) + "\n")


if __name__ == "__main__":
    main()
