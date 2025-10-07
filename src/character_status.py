class Relationship:
    """キャラ間の関係（親近/信頼など）。"""
    def __init__(self, affinity: int = 0, trust: int = 0):
        self.affinity = affinity   # -100 ~ +100
        self.trust    = trust      #    0 ~ 100


class CharacterStatus:
    def __init__(self, name:str,faction: str = "player", is_rc: bool = False, hp=100, stamina=100, attack_power=10, inventory=None, is_npc=False):
        self.name = name
        self.faction = faction        # ← デフォルトは 'player' # 'player' / 'enemy' / 'neutral'
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
        # --- Relationships ---
        self.rel_to_player = Relationship()  # 既存互換
        self.relationships = {}              # 任意の相手 name -> Relationship
        # 主観ラベル（誰から見たか → このキャラへのラベル集合）
        # 例: B.relationship_tags_from["主人公"] = {"友人","恋人候補"}
        self.relationship_tags_from = {}

        # --- Emotion ---
        # EmotionState(NLC主) を導入。LC は UI 用射影をキャッシュ。
        from src.emotion_state import EmotionState
        from src.emotion_math import project_nlc_to_lc
        self.emotion = EmotionState(nonlinear=(127, 127, 255))
        self.emotion.linear = project_nlc_to_lc(self.emotion.nonlinear, self.emotion.confidence)
        # 後方互換: 既存コードが参照する LC
        self.emotion_color = self.emotion.linear  # 心の色（初期表示）

    def change_status(self, hp_change=0, stamina_change=0, attack_power_change=0):
        self.hp = max(0, min(self.max_hp, self.hp + hp_change))
        self.stamina = max(0, min(self.max_stamina, self.stamina + stamina_change))
        self.attack_power = max(0, self.attack_power + attack_power_change)

        print(f"\n{self.name}の現在のステータス: HP={self.hp}/{self.max_hp}, スタミナ={self.stamina}/{self.max_stamina}, 攻撃力={self.attack_power}")
        
    def update_emotion_color(self, red_delta=0, green_delta=0, blue_delta=0):
        """感情座標を変化させる"""
        from src.emotion_math import clip_rgb
        r, g, b = self.emotion.linear
        new_lc = clip_rgb((r + red_delta, g + green_delta, b + blue_delta))
        # LCを直接更新 → NLCは残差サンプリングで再推定（“ゆらぎ”）
        self.set_emotion_linear(new_lc)
        print(f"{self.name}の心の色が更新されました: RGB{self.emotion_color}")
    

    def equip_weapon(self, weapon):
        # 武器装備ロジック
        if weapon :
            self.equipped_weapon = weapon
            self.attack_power += weapon.get('attack_bonus', 0)
            print(f"{self.name}が{weapon['name']}を装備しました。攻撃力: {self.attack_power}")

    # --------- Emotion API（追加）---------
    def set_emotion_linear(self, rgb, *, confidence: float = None):
        """UIで直接設定された LC を反映（NLCへ拡張し保持）。"""
        if confidence is not None:
            self.emotion.confidence = float(confidence)
        self.emotion.set_linear(tuple(rgb), update_nonlinear=True)
        # 後方互換のLCも同期
        self.emotion_color = self.emotion.linear

    def set_emotion_nonlinear(self, rgb, *, source: str = "inferred", confidence: float = None):
        """外部推定などで得た NLC を反映（LCに射影してUIへ）。"""
        if confidence is not None:
            self.emotion.confidence = float(confidence)
        self.emotion.set_nonlinear(tuple(rgb), update_linear=True, source=source)  # LCも更新
        self.emotion_color = self.emotion.linear

    # --------- Relationship Labels（追加）---------
    def add_label_from(self, observer_name: str, label: str):
        """observer（例：主人公）から見たこのキャラへのラベルを付与。"""
        s = self.relationship_tags_from.setdefault(observer_name, set())
        s.add(label)

    def remove_label_from(self, observer_name: str, label: str):
        s = self.relationship_tags_from.setdefault(observer_name, set())
        if label in s:
            s.remove(label)

    def get_labels_from(self, observer_name: str):
        return set(self.relationship_tags_from.get(observer_name, set()))

# 使用例：
player = CharacterStatus("プレイヤー")
npc = CharacterStatus("NPC戦士", is_npc=True)