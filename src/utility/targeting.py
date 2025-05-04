def get_contextual_target(action_key, actor, game_state, *args):
    """
    action_key に応じてログ用 'target' を決める。
    - switch_character → 切替先
    - 戦闘系          → game_state['enemy'] の名前
    - それ以外        → game_state['current_target'] を維持
    """
    if action_key == "switch_character" and args:
        return args[0]            # <target_name>
    if action_key in ["戦う", "戦わない", "ただ、受け入れる"]and game_state.get("enemy"):
        return game_state["enemy"].name
    return game_state.get("current_target")

def prompt_target_rc(game_state):
    candidates = [
        m.name for m in game_state["party"].values()
        if m.is_rc and not m.is_active
    ]
    if not candidates:
        return None
    if len(candidates) == 1:
        return candidates[0]

    print("切り替え先を選んでください:")
    for i, name in enumerate(candidates, 1):
        print(f"[{i}] {name}")
    while True:
        sel = input("> ")
        if sel.isdigit() and 1 <= int(sel) <= len(candidates):
            return candidates[int(sel) - 1]
