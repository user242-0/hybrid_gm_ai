from src.quit_helper import handle_quit                # ← 追加

def set_emotion_color_action(player, game_state):
    try:
        print(f"🌌 {player.name}の心の空を設定しましょう")
        raw = input("🔴 衝動（赤）0〜255: ")        # ① 最初の入力
        handle_quit(raw, game_state)               # ★ ← ここ
        r = int(raw)

        raw = input("🟢 制御（緑）0〜255: ")
        handle_quit(raw, game_state)               # ★
        g = int(raw)

        raw = input("🔵 優しさ（青）0〜255: ")
        handle_quit(raw, game_state)               # ★
        b = int(raw)

        player.emotion_color = (r, g, b)
        print(f"{player.name}の心の色は RGB({r},{g},{b}) に更新されました。")

    except KeyboardInterrupt:                      # Ctrl-C でも安全終了
        handle_quit("quit", game_state)

    except (ValueError, TypeError):
        print("無効な入力でした。心の空は変更されませんでした。")