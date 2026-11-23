# gui.py -----------------------------------------------------------
from src.event_bus import event_q, log_q
from src.quit_helper import handle_quit
import tkinter as tk
from queue import Empty
import re

def start_gui(gs):
    def ui_loop():
        root = tk.Tk()
        root.title("Hybrid GM – Console")
        root.geometry("1100x700")
        root.rowconfigure(0, weight=1)
        root.columnconfigure(0, weight=1)

        # 左は既存の操作表示、右はScene / Dialogue。境界はドラッグで調整可能。
        panes = tk.PanedWindow(root, orient=tk.HORIZONTAL, sashwidth=6)
        panes.grid(row=0, column=0, sticky="nsew")
        actions_view = tk.LabelFrame(panes, text="Actions / Status")
        right_panes = tk.PanedWindow(panes, orient=tk.VERTICAL, sashwidth=6)
        panes.add(actions_view, width=360, minsize=240, stretch="always")
        panes.add(right_panes, width=730, minsize=320, stretch="always")

        # Sceneの子ウィジェットを将来の描画コンポーネントへ置換する。
        scene_view = tk.LabelFrame(right_panes, text="Scene View")
        tk.Label(
            scene_view, text="ここにシーンを表示します", bg="#191d24", fg="#AAA"
        ).pack(fill="both", expand=True)
        right_panes.add(scene_view, height=310, minsize=120, stretch="always")

        dialogue_view = tk.LabelFrame(right_panes, text="Dialogue View")
        dialogue_scroll = tk.Scrollbar(dialogue_view, orient=tk.VERTICAL)
        dialogue_scroll.pack(side="right", fill="y")
        dialogue_txt = tk.Text(
            dialogue_view, name="dialogue_text", width=1, height=1,
            state="disabled", bg="#222", fg="#DDD", wrap="word",
            yscrollcommand=dialogue_scroll.set,
        )
        dialogue_txt.pack(side="left", fill="both", expand=True)
        dialogue_scroll.config(command=dialogue_txt.yview)
        dialogue_txt.tag_config("speaker", foreground="#fadb14")
        right_panes.add(dialogue_view, height=340, minsize=120, stretch="always")

        def _append_dialogue(speaker: str, text: str):
            # GUI表示だけの一時履歴。turn/noteの再描画とは独立させる。
            dialogue_txt.config(state="normal")
            dialogue_txt.insert(tk.END, speaker + "\n", "speaker")
            dialogue_txt.insert(tk.END, text + "\n\n")
            dialogue_txt.see(tk.END)
            dialogue_txt.config(state="disabled")

        def _clear_dialogue():
            dialogue_txt.config(state="normal")
            dialogue_txt.delete("1.0", tk.END)
            dialogue_txt.config(state="disabled")

        # 表示エリア：常に「最新の手番＋補足」しか置かない
        txt = tk.Text(actions_view, name="turn_text", width=1, height=1, state="disabled", bg="#222", fg="#DDD", wrap="word")
        txt.pack(fill="both", expand=True)

        # マウスホイールでの過去スクロールを無効化（過去自体ありませんが視覚的にも固定）
        def _block_scroll(event): return "break"
        txt.bind("<MouseWheel>", _block_scroll)     # Windows
        txt.bind("<Button-4>", _block_scroll)       # Linux
        txt.bind("<Button-5>", _block_scroll)

        # 代表色
        predefined = {
            "red":   "#ff4d4f",
            "green": "#52c41a",
            "blue":  "#1890ff",
            "yellow":"#fadb14",
            "header":"#ffffff",
        }
        for name, color in predefined.items():
            txt.tag_config(name, foreground=color)

        def _ensure_rgb_tag(tag: str):
            """'rgb:R,G,B' / '#RRGGBB' / 既知色名 を Text タグ化して返す。"""
            if not tag:
                return None
            if isinstance(tag, str) and tag.startswith("rgb:"):
                try:
                    r, g, b = [int(x) for x in tag.split(":", 1)[1].split(",")]
                    hx = f"#{r:02x}{g:02x}{b:02x}"
                    if hx not in txt.tag_names():
                        txt.tag_config(hx, foreground=hx)
                    return hx
                except Exception:
                    return None
            if isinstance(tag, str) and tag.startswith("#") and len(tag) == 7:
                if tag not in txt.tag_names():
                    txt.tag_config(tag, foreground=tag)
                return tag
            try:
                if tag not in txt.tag_names():
                    txt.tag_config(tag, foreground=tag)
            except tk.TclError:
                return None
            return tag

        # バッファ（最新手番と補足だけを保持）
        turn_lines = []   # list[(text, tag)]
        note_lines = []   # list[(text, tag)]
        last_snapshot = None

        def _insert_line(line: str, tag: str | None):
            """1行挿入（色名/HEX/RGBに対応。レガシー '(red)' 先頭も吸収）"""
            resolved = _ensure_rgb_tag(tag)
            if resolved:
                txt.insert(tk.END, line + "\n", resolved)
            else:
                m = re.match(r"^\((red|green|blue|yellow)\)\s*", line)
                if m:
                    color_tag = m.group(1)
                    stripped = line[m.end():]
                    txt.insert(tk.END, stripped + "\n", color_tag)
                else:
                    txt.insert(tk.END, line + "\n")

        def _render():
            nonlocal last_snapshot
            snapshot = (tuple(turn_lines), tuple(note_lines))
            if snapshot == last_snapshot:
                return
            txt.config(state="normal")
            txt.delete("1.0", tk.END)
            # 手番本体
            for line, tag in turn_lines:
                _insert_line(line, tag)
            # 補足（α）
            if note_lines:
                txt.insert(tk.END, "\n")
                for line, tag in note_lines:
                    _insert_line(line, tag)
            txt.see(tk.END)
            txt.config(state="disabled")
            last_snapshot = snapshot

        # 入力欄
        entry = tk.Entry(root, width=80)
        entry.grid(row=1, column=0, sticky="ew", padx=6, pady=6)
        def on_enter(event=None):
            cmd = entry.get().strip()
            if not cmd:
                return
            handle_quit(cmd, gs)
            event_q.put(cmd)
            entry.delete(0, tk.END)
        entry.bind("<Return>", on_enter)

        # ログ取り込み（mode 指定の辞書だけを扱う “厳格モード”）
        def pump_logs():
            nonlocal turn_lines, note_lines
            changed = False
            try:
                while True:
                    item = log_q.get_nowait()

                    if isinstance(item, dict):
                        mode = item.get("mode")
                        if mode == "turn":
                            if item.get("reset"):
                                turn_lines = []
                                note_lines = []     # 手番が変わったら補足もリセット
                                changed = True
                            text = item.get("text")
                            tag  = item.get("tag")
                            if text is not None:
                                turn_lines.append((text, tag))
                                changed = True
                        elif mode == "note":
                            if item.get("reset"):
                                note_lines = []
                                changed = True
                            text = item.get("text")
                            tag  = item.get("tag")
                            if text is not None:
                                note_lines.append((text, tag))
                                changed = True
                        elif mode in ("note_clear", "notes_clear"):
                            note_lines = []
                            changed = True
                        elif mode in ("turn_clear", "clear"):
                            turn_lines = []
                            changed = True
                        elif mode == "render":
                            changed = True  # 明示リフレッシュ
                        elif mode == "dialogue":
                            text = item.get("text")
                            if isinstance(text, str):
                                speaker = str(item.get("speaker") or "?")
                                _append_dialogue(speaker, text)
                        elif mode == "dialogue_clear":
                            _clear_dialogue()
                        # 不明 mode は無視（厳格モード）
                    else:
                        # レガシー（str / (msg, tag)）は完全に無視
                        pass
            except Empty:
                pass

            if changed:
                _render()
            root.after(50, pump_logs)

        pump_logs()
        root.mainloop()

    import threading
    threading.Thread(target=ui_loop, daemon=True).start()
