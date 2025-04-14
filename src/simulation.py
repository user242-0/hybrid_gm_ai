# simulation.py（仮構成）

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
            effect(player, game_state, *args)

        except ValueError:
            print("数値を入力してください。")
        except Exception as e:
            print(f"エラーが発生しました: {e}")
            
if __name__ == "__main__":
    main()
