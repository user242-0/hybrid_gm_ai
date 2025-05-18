from src.choice_model import Choice

choice_definitions = {
    # 戦闘系コマンド
    "戦う":            {"axis": "red", "value": 250},
    "戦わない":        {"axis": "red","value": 180},
    "ただ、受け入れる": {"axis": "red","value": 180},
    "攻撃する":        {"axis": "blue",  "value": 200},
    "switch_character": {"axis": "green", "value": 150},
    "石像に話す":      {"axis": "blue",  "value": 80},
    "探索する":        {"axis": "blue",  "value": 80},
    "石像に話す（クールダウン）":{"axis": "blue",  "value": 100},
    "進む":             {"axis": "blue",  "value": 100},
    "休む":             {"axis": "blue",  "value": 100},
    "感情を設定する":   {"axis": "green", "value": 200},  # 新規追加：プレイヤーの心を設定する緑コマンド
}

def get_available_choices(actor, game_state):
    from src.requirements_checker import RequirementsChecker
    
    checker = RequirementsChecker(game_state, actor)

    available = []
    from src.action_definitions import actions
    for key, meta in choice_definitions.items():
        act_meta = actions.get(key, {})

        # NPC／プレイヤーの区分をチェック
        available_to = act_meta.get("available_to")
        if actor.is_npc and available_to and "npc" not in available_to:
            continue
        if not actor.is_npc and available_to and "player" not in available_to:
            continue

        
        
        # Choice インスタンスを生成
        choice = Choice(
            label=key,
            action_key=key,
            emotion_axis=meta.get("emotion_axis", meta.get("axis")),  # "red"|"green"|"blue"
            emotion_value=meta.get("emotion_value", meta.get("value", 128)),
            requirement_keys=act_meta.get("requirements")
        )

        # 実行条件を満たすか
        if choice.is_available(checker):
            available.append(choice)

    return available