import sys
import types
from src.character_status import CharacterStatus
from src.control_manager  import switch_control

sys.modules.setdefault("openai", types.ModuleType("openai"))

def test_switch():
    hero = CharacterStatus("Hero", is_rc=True, is_npc=False)
    luna = CharacterStatus("Luna", is_rc=True, is_npc=True)
    state = {
        "party": {
            hero.name: hero,
            luna.name: luna,
        },
        "party_map": {
            hero.name: hero,
            luna.name: luna,
        },
        "active_char": hero,
    }
    
    assert state["active_char"].name == "Hero"

    # actor は現在アクティブな CharacterStatus オブジェクト
    prev = switch_control(state["active_char"], state, "Luna")
    assert prev.name == "Hero"
    assert state["active_char"].name == "Luna"
    # 元に戻す
    prev = switch_control(state["active_char"], state, "Hero")
    assert prev.name == "Luna"