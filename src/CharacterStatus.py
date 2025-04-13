class CharacterStatus:
    def __init__(self, name, hp=100, stamina=100, attack_power=10, inventory=None, is_npc=False):
        self.name = name
        self.hp = hp
        self.max_hp = hp
        self.stamina = stamina
        self.max_stamina = stamina
        self.attack_power = attack_power
        self.is_tired = False
        self.inventory = inventory if inventory else []
        self.equipped_weapon = None
        self.is_npc = is_npc  # NPCかプレイヤーかを区別
    
    def equip_weapon(self, weapon):
        # 武器装備ロジック
        if weapon in self.inventory:
            self.equipped_weapon = weapon
            self.attack_power += weapon.get('attack_bonus', 0)
            print(f"{self.name}が{weapon['name']}を装備しました。攻撃力: {self.attack_power}")

# 使用例：
player = CharacterStatus("プレイヤー")
npc = CharacterStatus("NPC戦士", is_npc=True)
