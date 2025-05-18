from src.character_status import CharacterStatus

def init_game_state():
    hero = CharacterStatus("Hero", is_rc=True, is_npc=False)
    luna = CharacterStatus("Luna", is_rc=True, is_npc=True)

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
        "running": True,
        "input_pending" : False,
        # ほか HP, ロケーション, etc.
        "events": {
            "statue_trial_unlocked": False
        },
        "current_location": "祭壇",
        "current_target": "古代の石像"
    }
