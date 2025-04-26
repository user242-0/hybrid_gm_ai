class CharacterStatus:
    def __init__(self, name, hp=100, stamina=100, attack_power=10, inventory=None, is_npc=False):
        self.name = name
        self.hp = hp
        self.max_hp = hp
        self.stamina = stamina
        self.max_stamina = stamina
        self.attack_power = attack_power
        self.is_tired = True
        self.inventory = inventory if inventory else []
        self.equipped_weapon = None
        self.is_npc = is_npc  # NPCかプレイヤーかを区別
        
    def change_status(self, hp_change=0, stamina_change=0, attack_power_change=0):
        self.hp = max(0, min(self.max_hp, self.hp + hp_change))
        self.stamina = max(0, min(self.max_stamina, self.stamina + stamina_change))
        self.attack_power = max(0, self.attack_power + attack_power_change)

        print(f"\n{self.name}の現在のステータス: HP={self.hp}/{self.max_hp}, スタミナ={self.stamina}/{self.max_stamina}, 攻撃力={self.attack_power}")
        
    
    def equip_weapon(self, weapon):
        # 武器装備ロジック
        if weapon in self.inventory:
            self.equipped_weapon = weapon
            self.attack_power += weapon.get('attack_bonus', 0)
            print(f"{self.name}が{weapon['name']}を装備しました。攻撃力: {self.attack_power}")

# 使用例：
player = CharacterStatus("プレイヤー")
npc = CharacterStatus("NPC戦士", is_npc=True)
