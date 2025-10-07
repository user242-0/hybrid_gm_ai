from random import randint
from src.quit_helper import handle_quit                # ← 追加
from src.event_bus import event_q, log_q

def set_emotion_color_action(player, game_state):
    # NPC はランダム値を即時セットして終了
    if player.is_npc:
        r, g, b = randint(0, 255), randint(0, 255), randint(0, 255)
        # LC を直接設定しつつ、内部で NLC も更新（既存互換の emotion_color も同期される想定）
        try:
            player.set_emotion_linear((r, g, b))
        except AttributeError:
            # 後方互換：万一メソッド未導入なら従来プロパティだけ更新
            player.emotion_color = (r, g, b)
        return
    
    if game_state["use_gui"]:
        log_q.put((
            "❓ 感情値入力: LCは `rgb 200 160 120` / NLCは `nlc 200 160 120`（任意: `conf=0.8`）",
            "YELLOW"
        ))
        cmd = event_q.get()       # ブロックは GUI 側だけ
        try:
            tokens = cmd.split()
            mode = tokens[0].lower() if tokens else "rgb"
            # 例: "rgb 200 160 120" / "nlc 200 160 120 conf=0.8"
            r, g, b = map(int, tokens[1:4])
            conf = None
            for t in tokens[4:]:
                if t.startswith("conf="):
                    conf = float(t.split("=", 1)[1])
                    break
            if mode in ("rgb", "lc"):
                player.set_emotion_linear((r, g, b), confidence=conf if conf is not None else player.emotion.confidence)
            elif mode in ("nlc", "rgbn"):
                player.set_emotion_nonlinear((r, g, b), confidence=conf if conf is not None else player.emotion.confidence)
            else:
                # 不明なモードは LC として解釈
                player.set_emotion_linear((r, g, b), confidence=conf if conf is not None else player.emotion.confidence)
        except Exception:
            # 失敗時は何もしない
            log_q.put(("⚠ 入力を解釈できませんでした。変更は行われません。", "RED"))
    else:
        try:
            print(f"🌌 {player.name}の心の空を設定しましょう")
            mode = input("入力モードを選択 [lc/nlc]（Enterでlc）: ").strip().lower() or "lc"
            handle_quit(mode, game_state)
            raw = input("🔴 衝動（赤）0〜255: ")        # ① 最初の入力
            handle_quit(raw, game_state)               # ★ ← ここ
            r = int(raw)

            raw = input("🟢 制御（緑）0〜255: ")
            handle_quit(raw, game_state)               # ★
            g = int(raw)

            raw = input("🔵 優しさ（青）0〜255: ")
            handle_quit(raw, game_state)               # ★
            b = int(raw)

            if mode == "nlc":
                player.set_emotion_nonlinear((r, g, b))
                shown = player.emotion.linear if hasattr(player, "emotion") else (r, g, b)
                print(f"{player.name}のNLCを設定しました（UI表示LC=RGB{shown}）")
            else:
                player.set_emotion_linear((r, g, b))
                print(f"{player.name}の心の色（LC）は RGB({r},{g},{b}) に更新されました。")
 

        except KeyboardInterrupt:                      # Ctrl-C でも安全終了
            handle_quit("quit", game_state)

        except (ValueError, TypeError):
            print("無効な入力でした。心の空は変更されませんでした。")