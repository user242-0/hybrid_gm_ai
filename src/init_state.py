from src.character_status import CharacterStatus

def init_game_state():
    hero = CharacterStatus("Hero", is_rc=True, is_npc=False)
    luna = CharacterStatus("Luna", is_rc=True, is_npc=True)
    hero.equip_weapon({"name": "鉄の剣", "weapon_type":"sword","attack_bonus": 5})
    return {
        "party": {
            hero.name: hero,
            luna.name: luna,
        },
        "party_map": {
            hero.name: hero,
            luna.name: luna,
        },
        "active_char": hero,
        "allow_ai_to_seize_control" : True,  # セッション14用：NPCが“自分”をターゲットにして奪う
        "running": True,
        "input_pending" : False,
        "use_gui" : True,
        # ほか HP, ロケーション, etc.
        "events": {
            "statue_trial_unlocked": False
        },
        "current_location": "祭壇",
        "current_target": "古代の石像"
    }
