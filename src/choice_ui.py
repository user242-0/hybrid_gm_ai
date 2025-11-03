# --- choice_ui.py などに置く ---------------------------------------------------
from src.event_bus import log_q  # GUI 側へ表示を送る Queue
from src.choice_definitions import get_available_choices


def present_choices(actor, game_state):
    """
    現在操作キャラクター actor に対して実行可能な Choice を列挙し、
    GUI ログ（log_q）に番号付きで出力する。

    Returns
    -------
    dict  {int: Choice}
        キー：入力受付番号 1,2,3...   値：Choice オブジェクト
    """
    # 1) Choice 列挙
    choices = get_available_choices(actor, game_state)  # 既存 util を想定
    num_choice_map = {}

    if not choices:
        log_q.put(f"\n⚠️ {actor.name} は今実行可能な行動がありません。\n")
        return {}

    # ★ まず新しい手番開始を宣言（過去を消す）
    log_q.put({"mode": "turn", "reset": True})
    log_q.put({"mode": "note", "reset": True})

    # 見出し
    log_q.put({"mode": "turn", "text": f"=== {actor.name} の手番 ===", "tag": "header"})

    # 各選択肢を「心×コマンドの強さ」で発色
    player_color = getattr(actor, "emotion_color", (127, 127, 255))
    for i, ch in enumerate(choices, start=1):
        r, g, b = ch.get_emotion_x_player_scaled_color(player_color)
        log_q.put(
            {
                "mode": "turn",
                "text": f"{i}. {ch.label}",
                "tag": f"rgb:{r},{g},{b}",
            }
        )
        num_choice_map[i] = ch

    # 補足（色なし）
    log_q.put({"text": "番号を入力して決定（例: 1）", "mode": "turn"})

    micro_goal = game_state.get("director_micro_goal")
    if micro_goal:
        log_q.put({"mode": "note", "text": f"Micro Goal: {micro_goal}", "tag": "yellow"})

    note = game_state.get("last_action_note")
    if note:
        # 例: {"text":"[PLY] Hero ▶ switch_character Luna", "tag":"green"}
        log_q.put({"mode": "note", **note})

    return num_choice_map