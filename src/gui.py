# gui.py -----------------------------------------------------------
from src.event_bus import event_q, log_q
from src.quit_helper import handle_quit
import tkinter as tk
from queue import Empty

def start_gui(gs):              # ★ 引数で受け取る
    def ui_loop():              # ★ 閉じ込めて参照させる
        root = tk.Tk()
        root.title("Hybrid GM – Console")
        # ---- ログ表示エリア ----
        txt = tk.Text(root, width=80, height=24, state="disabled", bg="#222", fg="#DDD")
        txt.pack()

        # ---- 入力エリア ----
        entry = tk.Entry(root, width=80)
        entry.pack()
        def on_enter(event=None):
            cmd = entry.get().strip()
            if not cmd:
                return
            handle_quit(cmd, gs)     # ← 参照できる
            event_q.put(cmd)
            entry.delete(0, tk.END)
        entry.bind("<Return>", on_enter)
        # ---- 50 ms ごとにログを吸い上げて表示 ----
        def pump_logs():
            try:
                while True:
                    item = log_q.get_nowait()
                    # ❶ タプルか文字列か判定
                    if isinstance(item, tuple):
                        msg, tag = item           # (message, tag)
                    else:
                        msg, tag = item, None     # 旧形式は tag=None

                    txt.config(state="normal")
                    if tag:
                        txt.insert(tk.END, msg + "\n", tag)
                    else:
                        txt.insert(tk.END, msg + "\n")
                    txt.see(tk.END)
                    txt.config(state="disabled")
            except Empty:
                pass
            root.after(50, pump_logs)
        pump_logs()
        root.mainloop()

    # サブスレッドで GUI を起動
    import threading
    threading.Thread(target=ui_loop, daemon=True).start()

