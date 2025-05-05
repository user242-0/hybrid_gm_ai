def set_emotion_color_action(player, game_state):
    try:
        print("🌌 あなたの心の空を設定しましょう")
        r = int(input("🔴 衝動（赤）0〜255: "))
        g = int(input("🟢 制御（緑）0〜255: "))
        b = int(input("🔵 優しさ（青）0〜255: "))
        player.emotion_color = (r, g, b)
        print(f"あなたの心の色は RGB({r},{g},{b}) に更新されました。")
    except Exception:
        print("無効な入力でした。心の空は変更されませんでした。")
