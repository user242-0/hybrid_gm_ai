import random

def add_item_to_inventory(player_status, item_name):
    """持ち物にアイテムを追加する関数"""
    player_status.inventory.append(item_name)
    print(f"{item_name}を持ち物に追加しました！")

def rest(player_status):
    """
    プレイヤーの体力やスタミナを回復し、疲労状態を解除する。
    """
    if player_status.hp < player_status.max_hp:
        player_status.hp = min(player_status.hp + 20, player_status.max_hp)
        print(f"HPを回復しました: {player_status.hp}/{player_status.max_hp}")
    
    if player_status.stamina < player_status.max_stamina:
        player_status.stamina = min(player_status.stamina + 20, player_status.max_stamina)
        print(f"スタミナを回復しました: {player_status.stamina}/{player_status.max_stamina}")
    
    player_status.is_tired = False
    print("疲労状態が解除されました！")

def rest_with_event(player_status, game_state):
    """
    安全地帯/危険地帯を考慮して休む処理をラップする。
    """
    rest(player_status)  # 休む処理を実行

    # 危険地帯の場合、一定確率で敵襲発生
    if not game_state["is_safe_zone"]:
        if random.random() < 0.3:  # 30%の確率で敵が襲ってくる
            print("敵が襲ってきた！戦闘開始！")
            # 戦闘処理をここに追加
        else:
            print("周囲は静かです。安全に休めました。")

def select_and_add_item(player_status, game_state):
    """
    プレイヤーが「やめる」と言うまで取得可能なアイテムを選択し、持ち物に追加する。
    """
    while True:
        if not game_state["available_items"]:
            print("取得可能なアイテムがありません。")
            return

        # 取得可能なアイテムを表示
        print("取得可能なアイテム:")
        for idx, item in enumerate(game_state["available_items"], start=1):
            print(f"{idx}. {item['name']}")
        print("0. やめる")

        # プレイヤーに選択を促す
        try:
            item_choice = int(input("取得するアイテムを選んでください: ")) - 1
            if item_choice == -1:
                print("アイテム取得を終了しました。")
                return
            elif 0 <= item_choice < len(game_state["available_items"]):
                item_name = game_state["available_items"][item_choice]
                player_status.inventory.append(item_name)  # 持ち物に追加
                game_state["available_items"].remove(item_name)  # リストから削除
                print(f"{item_name['name']}を持ち物に追加しました！")
            else:
                print("無効な選択です。")
        except ValueError:
            print("数値を入力してください。")

actions = {
    1: {
        "name": "進む",
        "description": "プレイヤーが洞窟の奥に進む",
        "requirements": None,
        "effects": {"function": lambda player_status, game_state: print("洞窟の奥に進みました"), "args": []}
    },
    2: {
        "name": "休む",
        "description": "プレイヤーの体力が回復する。",
        "requirements": {"is_tired": True, "check_hp_or_stamina": True},
        "effects": {"function": rest_with_event, "args": []}
    },    
    6: {
        "name": "アイテムを取得する",
        "description": "プレイヤーが取得可能なアイテムを選択し、持ち物に追加する",
        "requirements": {"requires_items": True},  # 取得可能なアイテムが必要
        "effects": {"function": select_and_add_item, "args": []}
    },
    7: {
        "name": "武器を装備する",
        "description": "武器を使用できる状態にする",
        "requirements": {"has_weapon_in_inventory": True},  # 取得可能なアイテムが必要
        "effects": {"function": lambda player_status, game_state: player_status.equip_weapon(), "args": []}
    },    
}