class PlayerStatus:
    def __init__(self):
        self.hp = 50
        self.max_hp = 100
        self.stamina = 30
        self.max_stamina = 100
        self.attack_power = 10  # 初期攻撃力
        self.is_tired = True
        self.inventory = [
            # {"name": "剣", "type": "weapon", "category": "equipment", "attack_bonus": 5},
            # {"name": "弓", "type": "weapon", "category": "equipment", "attack_bonus": 3},
            {"name": "盾", "type": "armor"}
        ]
        self.equipped_weapon = None  # 装備中の武器
        self.is_ready = False  # 構え状態

    def add_weapon(self, weapon):
        """武器を所持する"""
        self.inventory.append(weapon)
        print(f"{weapon}を所持しました。")

    def equip_weapon(self):
        """
        プレイヤーに装備可能な武器を選択させ、装備する。
        """
        # 装備可能な武器をフィルタリング
        weapons = [item for item in self.inventory if item["type"] == "weapon"]

        if not weapons:
            print("装備可能な武器がありません。")
            return

        # 選択肢を表示
        print("装備可能な武器:")
        for idx, weapon in enumerate(weapons, start=1):
            print(f"{idx}. {weapon['name']} (攻撃力 +{weapon.get('attack_bonus', 0)})")

        # プレイヤーに選択させる
        while True:
            try:
                choice = int(input("装備する武器の番号を選んでください（0でキャンセル）: ")) - 1
                if choice == -1:
                    print("武器の装備をキャンセルしました。")
                    return
                if 0 <= choice < len(weapons):
                    selected_weapon = weapons[choice]
                    break
                else:
                    print("無効な選択です。もう一度入力してください。")
            except ValueError:
                print("数字を入力してください。")

        # 現在の武器を外す
        if self.equipped_weapon:
            print(f"{self.equipped_weapon['name']} を外しました。")
            self.attack_power -= self.equipped_weapon.get("attack_bonus", 0) # ステータスを減らす
            self.inventory.append(self.equipped_weapon)

        # 新しい武器を装備
        self.equipped_weapon = selected_weapon
        self.inventory.remove(selected_weapon)
        print(f"{selected_weapon['name']} を装備しました！")

        # ステータスを更新
        self.attack_power += selected_weapon.get("attack_bonus", 0)
        print(f"現在の攻撃力: {self.attack_power}")

    def ready_weapon(self):
        """武器を構える"""
        if self.equipped_weapon:
            self.is_ready = True
            print(f"{self.equipped_weapon}を構えました。")
        else:
            print("武器を装備していません。")

    def get(self, attr, default=None):
        return getattr(self, attr, default)