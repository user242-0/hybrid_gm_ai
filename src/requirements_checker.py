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
                member.is_rc and not member.is_active
                for member in self.game_state["party"].values()
            )
        }

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
