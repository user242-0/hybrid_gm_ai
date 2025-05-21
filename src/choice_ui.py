# --- choice_ui.py などに置く ---------------------------------------------------
from src.event_bus            import log_q          # GUI 側へ表示を送る Queue
from src.choice_definitions   import get_available_choices

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

    if not choices:
        log_q.put(f"\n⚠️ {actor.name} は今実行可能な行動がありません。\n")
        return {}

    # 2) GUI へ番号付きで送る
    header = f"\n🎮 {actor.name} のターン — 行動を選択してください\n"
    body   = "\n".join(
        f"[{i}] {c.action_key:15}  ({c.emotion_axis})"
        for i, c in enumerate(choices, 1)
    )
    log_q.put(header + body)

    # 3) 番号 → Choice の dict を返す
    return {i: c for i, c in enumerate(choices, 1)}