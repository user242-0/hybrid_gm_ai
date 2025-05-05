# ui_emotion_mapper.py
# キャラクターの emotion_color を UI 表示用の RGB に変換するユーティリティ

def map_emotion_to_ui_color(emotion_color: tuple[int, int, int]) -> tuple[int, int, int]:
    """
    キャラクターの感情値(R,G,B)を、UI上の色表示（警戒色）に変換する。
    赤：緊迫（衝動 + 冷たさ + 発散）
    緑：通常
    青：落ち着き（静寂 + 優しさ + 収束）
    """
    r, g, b = emotion_color

    # 各成分の割合に基づく緊迫度（0〜1）
    tension = (
        (r / 255) * 0.4 +              # 衝動（高いほど緊迫）
        ((255 - g) / 255) * 0.3 +      # 可制御性（低いほど緊迫）
        ((255 - b) / 255) * 0.3        # 優しさ（低いほど緊迫）
    )

    # 緊迫度に基づいてUI色を生成
    red   = int(min(255, tension * 2 * 255))         # 高緊迫度ほど赤
    green = int(255 - abs(tension - 0.5) * 2 * 255)  # 中間緊迫度ほど緑
    blue  = int(min(255, (1 - tension) * 2 * 255))   # 低緊迫度ほど青

    return (red, green, blue)
