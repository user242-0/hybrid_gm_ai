from random import randint
from src.quit_helper import handle_quit                # ← 追加
from src.event_bus import event_q, log_q

def set_emotion_color_action(player, game_state):
    # NPC はランダム値を即時セットして終了
    if player.is_npc:
        r, g, b = randint(0, 255), randint(0, 255), randint(0, 255)
        player.emotion_color = (r, g, b)
        return
    
    if game_state["use_gui"]:
        log_q.put(("❓ 感情値入力は GUI の Entry で `rgb 0 0 0` の形式で入れてください", "YELLOW"))
        cmd = event_q.get()       # ブロックは GUI 側だけ
        try:
            _, r, g, b = cmd.split()
        except ValueError:
            # トークン不足 → デフォルト 0,0,0 を入れる or ランダム
            r, g, b = 0, 0, 0
    else:
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