import random
from playerstatus01 import PlayerStatus
from actions import actions

class RequirementsChecker:
    def __init__(self, game_state, player_status):
        self.game_state = game_state
        self.player_status = player_status

    def is_tired(self, requirements):
        if not requirements:  # requirementsがNoneの場合をチェック
            return True
        return self.player_status.is_tired if "is_tired" in requirements else True

    def hp_or_stamina(self, requirements):
        if not requirements:  # requirementsがNoneの場合をチェック
            return True
        return (
            self.player_status.hp < self.player_status.max_hp or
            self.player_status.stamina < self.player_status.max_stamina
        ) if "check_hp_or_stamina" in requirements else True

    def items_available(self, requirements):
        if not requirements:  # requirementsがNoneの場合をチェック
            return True
        return bool(self.game_state.get("available_items")) if "requires_items" in requirements else True

    def has_weapon_in_inventory(self, requirements):
        """
        持ち物に装備可能な武器があるかをチェック。
        """
        if not requirements or "has_weapon_in_inventory" not in requirements:
            return True
        return any(item for item in self.player_status.inventory if item["type"] == "weapon")
    
    def check_all(self, requirements):
        if not requirements:  # requirementsがNoneの場合
            return True  # 条件がない場合は許可
        return all([
            self.is_tired(requirements),
            self.hp_or_stamina(requirements),
            self.items_available(requirements),
            self.has_weapon_in_inventory(requirements)
        ])

def get_available_actions(game_state, player_status):
    """
    条件を満たすアクションを抽出して available_actions を生成。
    """
    checker = RequirementsChecker(game_state, player_status)

    # 条件を満たすアクションだけを抽出
    available_actions = {
        action_id: action
        for action_id, action in actions.items()
        if checker.check_all(action["requirements"])
    }

    return available_actions


def show_actions_and_select(player_status, game_state):
    """
    有効なアクションを表示し、プレイヤーに選択させる。
    """
    available_actions = get_available_actions(game_state, player_status)

    if not available_actions:
        print("実行可能なアクションがありません。")
        return None

    print("選択可能なアクション:")
    for idx, (action_id, action) in enumerate(available_actions.items(), start=1):
        print(f"{idx}. {action['name']} - {action['description']}")
    
    try:
        choice = int(input("行動を選択してください: ")) - 1
        if 0 <= choice < len(available_actions):
            selected_action_id = list(available_actions.keys())[choice]
            return selected_action_id
        else:
            print("無効な選択です。")
            return None
    except ValueError:
        print("数値を入力してください。")
        return None

def perform_action(action_id, player_status, game_state):
    action = actions.get(action_id)
    if not action:
        print("無効な行動です。")
        return

    # 効果を実行
    effects = action.get("effects")
    if effects and "function" in effects:
        function = effects["function"]
        args = effects.get("args", [])
        function(player_status, game_state, *args)  # 関数を実行
    else:
        print(action.get("effects", "効果なし"))
    

def main():
    player_status = PlayerStatus()
    
    game_state = {
    "available_items" : [
    {"name": "剣", "type": "weapon", "category": "equipment", "attack_bonus": 5},
    {"name": "ポーション", "type": "healing_item", "category": "consumable", "hp_bonus": 20},
    {"name": "鉄鉱石", "type": "crafting_material", "category": "material"}
    ],
    "is_safe_zone": False  # True: 安全地帯, False: 危険地帯
    }
    # アクション選択ループ
    while True:
        action_id = show_actions_and_select(player_status, game_state)
        if action_id is not None:
            perform_action(action_id, player_status, game_state)
        else:
            print("行動選択を終了します。")
            break

if __name__ == "__main__":
    main()
