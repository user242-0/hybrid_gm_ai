import sys
import types
from src.simulation       import init_game_state
from src.control_manager  import switch_control

sys.modules.setdefault("openai", types.ModuleType("openai"))

def test_switch():
    state = init_game_state()
    assert state["active_char"].name == "Hero"

    # actor は現在アクティブな CharacterStatus オブジェクト
    prev = switch_control(state["active_char"], state, "Luna")
    assert prev.name == "Hero"
    assert state["active_char"].name == "Luna"
    # 元に戻す
    prev = switch_control(state["active_char"], state, "Hero")
    assert prev.name == "Luna"