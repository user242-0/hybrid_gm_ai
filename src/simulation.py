# simulation.py（仮構成）

from CharacterStatus import CharacterStatus
from actions import actions

def main():
    player = CharacterStatus(name="プレイヤー")
    game_state = {
        "is_safe_zone": True,
        "available_items": [],
        "events": {
            "statue_trial_unlocked": False  # 初期状態では未解放
        }
    }

    while True:
        print("\n=== 行動選択 ===")
        for i, (action_key, action) in enumerate(actions.items(), start=1):
            if "player" in action.get("available_to", []):  # プレイヤー用のアクションだけ表示
                print(f"{i}. {action_key} - {action['description']}")
        try:
            choice = int(input("行動番号を選んでください（0で終了）: ")) - 1
            if choice == -1:
                break
            selected_action_key = list(actions.keys())[choice]
            action = actions[selected_action_key]
            effect = action["effects"]["function"]
            args = action["effects"].get("args", [])
            effect(player, game_state, *args)
        except Exception as e:
            print(f"エラー: {e}")

if __name__ == "__main__":
    main()
