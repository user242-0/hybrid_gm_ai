class Relationship:
    """プレイヤー⇔NPC の感情値を一元管理"""
    def __init__(self, affinity: int = 0, trust: int = 0):
        self.affinity = affinity   # -100 ~ +100
        self.trust    = trust      #    0 ~ 100

class CharacterStatus:
    def __init__(self, name:str,faction: str = "player", is_rc: bool = False, hp=100, stamina=100, attack_power=10, inventory=None, is_npc=False):
        self.name = name
        self.faction = faction,        # ← デフォルトは 'player' # 'player' / 'enemy' / 'neutral'
        self.is_rc = is_rc # Reversible Character か？
        self.is_active = False  # 現在操作中？
        self.hp = hp
        self.max_hp = hp
        self.stamina = stamina
        self.max_stamina = stamina
        self.attack_power = attack_power
        self.is_tired = True
        self.inventory = inventory if inventory else []
        self.has_weapon = False
        self.equipped_weapon = None
        self.location = None
        self.is_npc = is_npc  # NPCかプレイヤーかを区別
        self.rel_to_player = Relationship()

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
