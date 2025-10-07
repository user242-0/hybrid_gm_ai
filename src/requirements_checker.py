class RequirementsChecker:
    def __init__(self, game_state, player_status):
        self.game_state = game_state
        self.player_status = player_status

        # 条件を辞書形式で管理（追加・削除が容易！）
        self.checks = {
            "is_tired": lambda: self.player_status.is_tired,
            "check_hp_or_stamina": lambda: (
                self.player_status.hp < self.player_status.max_hp or
                self.player_status.stamina < self.player_status.max_stamina
            ),
            "requires_items": lambda: bool(self.game_state.get("available_items")),
            "has_weapon_in_inventory": lambda: any(
                item for item in self.player_status.inventory if item["type"] == "weapon"
            ),
            "has_weapon": lambda: self.player_status.equipped_weapon is not None,
            #"has_weapon": lambda: self.player_status.has_weapon,
            "has_enemy": lambda: self.game_state.get("has_enemy"),   # この行を追加
            "location": lambda loc: self.game_state.get("current_location") == loc,
            "has_item": lambda item_name: any(
                item["name"] == item_name for item in self.player_status.inventory
            ),
            "target": lambda target_name: self.game_state.get("current_target") == target_name,
            #"has_rc_in_party": lambda: any(member.is_rc and not member.is_active for member in self.game_state["party"].values()),
            "has_rc_in_party": lambda: any(
                member.is_rc and not member.is_active and member.faction == "player"
                for member in self.game_state["party"].values()
            ),
            # ---- Emotion related (LC基準) ----
            "emotion_r_at_least": lambda v: self._lc()[0] >= int(v),
            "emotion_g_at_least": lambda v: self._lc()[1] >= int(v),
            "emotion_b_at_least": lambda v: self._lc()[2] >= int(v),
            "emotion_any_at_least": lambda v: any(c >= int(v) for c in self._lc()),
            "emotion_is_linear_ordered": lambda: self._lc()[0] >= self._lc()[1] >= self._lc()[2],
            # ---- Relationship label (observer=player_status → target=current_target) ----
            "has_relation_label_to_target": lambda label: self._has_relation_label_to_target(label),            
        }

    # --- helpers ---
    def _lc(self):
        """現在のプレイヤーUI色（LC）を取得。EmotionState優先、なければ従来のemotion_color。"""
        if hasattr(self.player_status, "emotion"):
            return tuple(self.player_status.emotion.linear)
        return tuple(getattr(self.player_status, "emotion_color", (127,127,255)))

    def _find_character_by_name(self, name: str):
        if not name:
            return None
        party = self.game_state.get("party")
        if isinstance(party, dict):
            for ch in party.values():
                if getattr(ch, "name", None) == name:
                    return ch
        party_map = self.game_state.get("party_map")
        if isinstance(party_map, dict) and name in party_map:
            return party_map[name]
        enemy = self.game_state.get("enemy")
        if enemy and getattr(enemy, "name", None) == name:
            return enemy
        return None

    def _has_relation_label_to_target(self, label: str) -> bool:
        target_name = self.game_state.get("current_target")
        target = self._find_character_by_name(target_name)
        if not target or not hasattr(target, "relationship_tags_from"):
            return False
        labels = target.relationship_tags_from.get(self.player_status.name, set())
        return str(label) in labels


    def check_all(self, requirements):
        """
        requirements が
        ① None           → 制約なし
        ② list[str]      → 各関数を True/False で評価
        ③ dict[str, Any] → 既存ロジック（値を引数に渡す）
        """

        # requirementsがNoneまたは空の場合、常にTrue
        if not requirements:
            return True
        
        if isinstance(requirements, list):
            # NG: getattr(self, key)()
            return all(self.checks[key]() for key in requirements)   # ← ここを修正

        for key, value in requirements.items():
            check = self.checks.get(key)
            if not check:
                # 存在しない条件キーの場合はFalse
                print(f"未定義の条件キーが指定されました: {key}")
                return False

            # 条件が関数（ラムダ）かつ引数が必要な場合とそうでない場合を区別
            if isinstance(value, bool) and value is True:
                if not check():
                    return False
            else:
                if not check(value):
                    return False
        return True
