# src/control_manager.py
from src.utility.targeting import prompt_target_rc

def switch_control(actor, game_state: dict, target_name:str)-> bool:
    #print(f"[DEBUG] target_name={target_name!r}")
    #print(f"[DEBUG] party keys={list(game_state['party'].keys())}")
    """
    actor = 現在操作しているキャラクター（不要でも受け取る）
    game_state["party"] などはそのまま利用
    """
    party = game_state["party"]
    current = actor

    if target_name not in party:
        return False
    target = party[target_name]

    if not target.is_rc or target is current:
        return False

    current.is_active = False
    target.is_active  = True
    game_state["active_char"] = target
    return True, f"操作キャラクターを {target.name} に切り替えた"


def switch_character_action(actor, game_state, target_name):
    return switch_control(actor, game_state, target_name)