# src/control_manager.py
import threading
from src.utility.targeting import prompt_target_rc
from src.character_status import CharacterStatus

def switch_control(actor, game_state: dict, target_name: str) -> CharacterStatus:
    """
    現在の操作キャラ(current) → NPC 化
    target_name のキャラ(next_) → プレイヤー化
    戻り値: current  (= 新たに NPC になったキャラ)
    """

    lock = game_state.setdefault("lock", threading.Lock())
    with lock:
        # ロック下で最新の状態を取得
        party = game_state["party"]
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

        # ログ用に「入れ替わる相手」を決める
        #  - 非アクティブNPCが自分(target=actor)を指名 → 相手は current
        #  - それ以外（アクティブが他者を指名など）   → 相手は target
        partner_for_log = current.name if target is actor else target.name

        current.is_npc = True      # 今まで手動だったキャラを AI 化
        target.is_npc  = False     # 新しい操作キャラを手動化


        current.is_active = False
        target.is_active  = True
        game_state["active_char"] = target
    
    

        # 表示は「交換した相手」を出す
        print("{}は操作キャラクターを{} に切り替えた".format(actor.name, partner_for_log))
        """
        print("DBG active:", game_state["active_char"].name)
        print("DBG hero npc?", target.is_npc, "luna npc?", current.is_npc)
        """
    return current


def switch_character_action(actor, game_state, target_name):
    return switch_control(actor, game_state, target_name)