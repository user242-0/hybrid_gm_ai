from src.simulation       import init_game_state
from src.control_manager  import switch_control

def test_switch():
    state = init_game_state()
    assert state["active_char"].name == "Hero"

    # actor は現在アクティブな CharacterStatus オブジェクト
    ok = switch_control(state["active_char"], state, "Luna")
    assert ok
    assert state["active_char"].name == "Luna"
    # 元に戻す
    assert switch_control(state["active_char"],state, "Hero")
