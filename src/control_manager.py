def switch_control(game_state: dict, target_name: str) -> bool:
    """
    主人公 <-> 任意 RC の操作権を入れ替える。
    成功時 True, 失敗時 False
    """
    current = game_state["active_char"]
    party   = game_state["party"]

    if target_name not in party:
        return False                       # そもそも存在しない
    target = party[target_name]

    if not target.is_rc or target is current:
        return False                       # RCでない／同一キャラ

    current.is_active = False
    target.is_active  = True
    game_state["active_char"] = target
    return True
