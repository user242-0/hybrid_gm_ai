    # プレイヤーと敵対NPCの定義
    player = CharacterStatus("プレイヤー", hp=100, stamina=100)
    player.equip_weapon({"name": "鉄の剣", "attack_bonus": 5})
    player.location = "力の洞窟"

    enemy_npc = CharacterStatus("敵対的NPC", hp=80, attack_power=10)
    enemy_npc.location = "力の洞窟"

    # ゲーム世界の状態
    global_game_state = {
        "力の洞窟": {
            "has_enemy": True,
            "enemy": {"name": enemy_npc.name, "hp": enemy_npc.hp, "attack_power": enemy_npc.attack_power}
        }
    }
    # 敵対的NPCのターン（攻撃モーメントが発生）
    run_simulation_step(enemy_npc, global_game_state, controlled_by_ai=True, opponent_character=player)

#########################################################################
    player = CharacterStatus("プレイヤー", hp=100, stamina=100)
    player.location = "祭壇"
    global_game_state = {
        "祭壇": {
            "has_enemy": True,
            "enemy": {"name": "ゴブリン", "hp": 20, "attack_power": 4}
        }
    }
    run_simulation_step(player, global_game_state)