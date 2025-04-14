# simulation.py
# ログ録り用モジュール
import json
from datetime import datetime
import os
# ゲーム用モジュール
from CharacterStatus import CharacterStatus
from actions import actions
from requirements_checker import RequirementsChecker

def main():
    player = CharacterStatus(name="プレイヤー")
    game_state = {
        "is_safe_zone": True,
        "available_items": [],
        "events": {
            "statue_trial_unlocked": False
        },
        "current_location": "祭壇",  # 場所を仮設定
        "current_target": "古代の石像"  # ターゲットを仮設定
    }

    checker = RequirementsChecker(game_state, player)

    while True:
        print("\n=== 選択可能なアクション ===")
        # 条件を満たすアクションのみリストアップするように変更
        available_actions = {
            key: action for key, action in actions.items()
            if "player" in action.get("available_to", [])
            and checker.check_all(action.get("requirements"))
        }

        # 利用可能なアクションがない場合の処理
        if not available_actions:
            print("現在実行可能なアクションがありません。")
            break

        for i, (action_key, action) in enumerate(available_actions.items(), start=1):
            print(f"{i}. {action_key} - {action['description']}")

        try:
            choice = int(input("行動番号を選んでください（0で終了）: ")) - 1
            if choice == -1:
                break
            if choice < 0 or choice >= len(available_actions):
                print("無効な選択です。再度選択してください。")
                continue

            selected_action_key = list(available_actions.keys())[choice]
            selected_action = available_actions[selected_action_key]
            effect = selected_action["effects"]["function"]
            args = selected_action["effects"].get("args", [])

            # アクション実行
            effect(player, game_state, *args)

            # ログを記録（成功時）
            log_action(
                actor=player.name,
                action=selected_action_key,
                target=game_state.get("current_target", "なし"),
                location=game_state.get("current_location", "不明"),
                result="成功"
            )

        except ValueError:
            print("数値を入力してください。")
            # ログを記録（数値以外入力で失敗）
            log_action(
                actor=player.name,
                action="アクション選択",
                target="なし",
                location=game_state.get("current_location", "不明"),
                result="数値入力エラーで失敗"
            )

        except Exception as e:
            print(f"エラーが発生しました: {e}")
            # ログを記録（例外エラーで失敗）
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
    
    with open("data/logs/gameplay_log.json", "a", encoding="utf-8") as logfile:
        logfile.write(json.dumps(log_entry, ensure_ascii=False) + "\n")


if __name__ == "__main__":
    main()
