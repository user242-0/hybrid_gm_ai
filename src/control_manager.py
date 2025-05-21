# src/control_manager.py
from src.utility.targeting import prompt_target_rc
from src.character_status import CharacterStatus

def switch_control(actor, game_state: dict, target_name: str) -> CharacterStatus:
    """
    現在の操作キャラ(current) → NPC 化
    target_name のキャラ(next_) → プレイヤー化
    戻り値: current  (= 新たに NPC になったキャラ)
    """
    party = game_state["party"]

    # 操作キャラクターは常に game_state から取得する
    current = game_state["active_char"]

    if target_name not in party:
        print("[DeBUG]:ターゲットがパーティに居ません")
        return False
    target = party[target_name]

    """
    if not target.is_rc or target is current:
        print("[DeBUG]:ターゲットがRCでないか、自分自身に切り替えようとしています")
        return False
    """

    current.is_npc   = True      # 今まで手動だったキャラを AI 化
    target.is_npc = False     # 新しい操作キャラを手動化

    current.is_active = False
    target.is_active  = True
    game_state["active_char"] = target
   
   

    # print('[SW]', current.name, current.is_npc, '|', target.name, target.is_npc)
    print("{}は操作キャラクターを{} に切り替えた".format(actor.name,target.name))
    """
    print("DBG active:", game_state["active_char"].name)
    print("DBG hero npc?", target.is_npc, "luna npc?", current.is_npc)
    """
    return current


def switch_character_action(actor, game_state, target_name):
    return switch_control(actor, game_state, target_name)