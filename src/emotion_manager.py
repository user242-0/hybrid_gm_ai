from random import randint
from src.quit_helper import handle_quit                # ← 追加
from src.event_bus import event_q, log_q
# GUIは「mode」付き辞書だけを描画する（厳格モード）


def _sync_emotions_by_actor(player, game_state):
    """actor別emotionをplayer.emotion_colorから同期する"""
    emotions_by_actor = game_state.get("emotions_by_actor")
    if emotions_by_actor is not None and hasattr(player, "emotion_color"):
        r, g, b = player.emotion_color
        emotions_by_actor.setdefault(player.name, {})
        emotions_by_actor[player.name]["R"] = r
        emotions_by_actor[player.name]["G"] = g
        emotions_by_actor[player.name]["B"] = b

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

        # actor別emotion更新
        _sync_emotions_by_actor(player, game_state)

        # 後方互換: world.emotion は更新しない（グローバル汚染を防ぐ）
        # ただし、プレイヤーのemotionでworld.emotionを初期化していない場合に備えてfallback
        world = game_state.get("director_world") or game_state.get("world") or game_state
        if world.get("emotion") is None:
            world["emotion"] = {}

        # HUD再描画をトリガー
        game_state["hud_cache_rev"] = game_state.get("hud_cache_rev", 0) + 1

        # 実行ログ
        print(f"[set_emotion] {player.name}: RGB({r}, {g}, {b})")
        return
    
    if game_state["use_gui"]:
        # 既存の補足を一旦クリアしてから、ガイダンスを補足モードで表示
        log_q.put({"mode":"note_clear"})
        log_q.put({
            "mode":"note",
            "text":"❓ 感情値入力: LCは `rgb 200 160 120` / NLCは `nlc 200 160 120`（任意: `conf=0.8`）",
            "tag":"yellow"
        })
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
            # actor別emotion同期
            _sync_emotions_by_actor(player, game_state)
            # HUD再描画をトリガー
            game_state["hud_cache_rev"] = game_state.get("hud_cache_rev", 0) + 1
            print(f"[set_emotion] {player.name}: RGB({r}, {g}, {b})")
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
            # actor別emotion同期
            _sync_emotions_by_actor(player, game_state)
            # HUD再描画をトリガー
            game_state["hud_cache_rev"] = game_state.get("hud_cache_rev", 0) + 1

        except KeyboardInterrupt:                      # Ctrl-C でも安全終了
            handle_quit("quit", game_state)

        except (ValueError, TypeError):
            print("無効な入力でした。心の空は変更されませんでした。")