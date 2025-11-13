
from __future__ import annotations

import queue
import threading
import tkinter as tk
from typing import Callable, Optional

MODE_COLORS = {
    "FREEZE": "#3b3b3b",
    "FLEE": "#2f4f4f",
    "PURSUE": "#0b3d91",
    "WITNESS": "#5a2a83",
}


class DirectorHUD:
    """Small top-level window that exposes quick director controls."""

    def __init__(self, title: str = "Director HUD") -> None:
        self.root = tk.Tk()
        self.root.title(title)
        # The HUD shows multiple stacked rows; ensure the window is tall enough so the
        # Auto/Next controls and help text are visible without manual resizing.
        self.root.geometry("520x360")
        self.root.minsize(520, 320)
        self.root.attributes("-topmost", True)

        self.on_mode_change: Optional[Callable[[str], None]] = None
        self.on_auto_action: Optional[Callable[[], None]] = None
        self.on_reroll: Optional[Callable[[], None]] = None
        self.on_save: Optional[Callable[[], None]] = None
        self.on_load: Optional[Callable[[], None]] = None
        self.on_show_micro: Optional[Callable[[], None]] = None
        self.on_action_select: Optional[Callable[[object], None]] = None
        self.on_toggle_auto: Optional[Callable[[bool], None]] = None
        self.on_ai_step: Optional[Callable[[], None]] = None

        self.mode_var = tk.StringVar(value="")
        self.clock_var = tk.StringVar(value="Day1 00:00")
        self.micro_var = tk.StringVar(value="(MicroGoal 未設定)")
        self.progress_var = tk.StringVar(value="")
        self.auto_var = tk.BooleanVar(value=False)

        self.actions_var: list[tuple[str, str, int]] = []
        self.modes: list[str] = []

        self._last_modes: Optional[tuple[str, ...]] = None
        self._last_mode_value: Optional[str] = None

        self._frame: Optional[tk.Frame] = None
        self._ui_thread = threading.current_thread()
        self._pending_calls: "queue.Queue[Callable[[], None]]" = queue.Queue()

        self._build()
        self._bind_keys()
        self.set_mode("FREEZE")

    def _build(self) -> None:
        pad = {"padx": 8, "pady": 4}

        frame = tk.Frame(self.root, bg=MODE_COLORS["FREEZE"])
        frame.pack(fill="both", expand=True)
        self._frame = frame

        row1 = tk.Frame(frame, bg=frame["bg"])
        row1.pack(fill="x", **pad)
        tk.Label(row1, text="Mode:", fg="white", bg=frame["bg"]).pack(side="left")
        self.mode_menu = tk.OptionMenu(row1, self.mode_var, "")
        self.mode_menu.configure(highlightthickness=0)
        self.mode_menu.pack(side="left")
        tk.Label(row1, text="Clock:", fg="white", bg=frame["bg"]).pack(side="left", padx=12)
        tk.Label(row1, textvariable=self.clock_var, fg="white", bg=frame["bg"]).pack(
            side="left", padx=6
        )

        row2 = tk.Frame(frame, bg=frame["bg"])
        row2.pack(fill="x", **pad)
        tk.Label(row2, text="MicroGoal:", fg="white", bg=frame["bg"]).pack(side="left")
        self.micro_lbl = tk.Label(
            row2,
            textvariable=self.micro_var,
            fg="white",
            bg=frame["bg"],
            wraplength=420,
            justify="left",
        )
        self.micro_lbl.pack(side="left", padx=6)

        rowp = tk.Frame(frame, bg=frame["bg"])
        rowp.pack(fill="x", **pad)
        tk.Label(rowp, text="Progress:", fg="white", bg=frame["bg"]).pack(side="left")
        tk.Label(
            rowp,
            textvariable=self.progress_var,
            fg="white",
            bg=frame["bg"],
            wraplength=420,
            justify="left",
        ).pack(side="left", padx=6)

        row_rec = tk.Frame(frame, bg=frame["bg"])
        row_rec.pack(fill="x", **pad)
        self.rec_btn = tk.Button(row_rec, text="(Recommended)", command=self._click_recommended)
        self.rec_btn.pack(side="left")

        row_actions = tk.Frame(frame, bg=frame["bg"])
        row_actions.pack(fill="both", expand=True, **pad)
        tk.Label(row_actions, text="Actions:", fg="white", bg=frame["bg"]).pack(anchor="w")
        self.listbox = tk.Listbox(row_actions, height=7)
        self.listbox.pack(fill="both", expand=True)
        self.listbox.bind("<<ListboxSelect>>", self._on_list_select)
        self.listbox.bind("<Double-Button-1>", self._on_list_activate)
        self.listbox.bind("<Return>", self._on_list_activate)

        row_auto = tk.Frame(frame, bg=frame["bg"])
        row_auto.pack(fill="x", **pad)
        tk.Checkbutton(
            row_auto,
            text="Auto",
            variable=self.auto_var,
            command=lambda: self.on_toggle_auto
            and self.on_toggle_auto(self.auto_var.get()),
        ).pack(side="left")
        tk.Button(
            row_auto,
            text="Next (AI)",
            command=lambda: self.on_ai_step and self.on_ai_step(),
        ).pack(side="left", padx=8)

        row3 = tk.Frame(frame, bg=frame["bg"])
        row3.pack(fill="x", **pad)
        help_text = (
            "[Keys] Use Mode dropdown | 1..9:Run Action | G:Show Micro | R:Reroll Micro | "
            "A:Next(AI) | S:Save L:Load"
        )
        self.help_text = help_text
        self.help_label = tk.Label(
            row3,
            text=help_text,
            fg="white",
            bg=frame["bg"],
            justify="left",
            wraplength=460,
        )
        self.help_label.pack(side="left")

    def _bind_keys(self) -> None:
        root = self.root
        root.bind("<Key-g>", lambda _: self.on_show_micro and self.on_show_micro())
        root.bind("<Key-G>", lambda _: self.on_show_micro and self.on_show_micro())
        root.bind("<Key-r>", lambda _: self.on_reroll and self.on_reroll())
        root.bind("<Key-R>", lambda _: self.on_reroll and self.on_reroll())
        root.bind("<Key-a>", lambda _: self._trigger_ai_step())
        root.bind("<Key-A>", lambda _: self._trigger_ai_step())
        root.bind("<Key-s>", lambda _: self.on_save and self.on_save())
        root.bind("<Key-S>", lambda _: self.on_save and self.on_save())
        root.bind("<Key-l>", lambda _: self.on_load and self.on_load())
        root.bind("<Key-L>", lambda _: self.on_load and self.on_load())
        for idx, key in enumerate("123456789"):
            root.bind(
                f"<Key-{key}>",
                lambda _evt, index=idx: self._run_index(index),
            )

    def set_mode(self, mode: str) -> None:
        if mode == self._last_mode_value:
            return
        self._last_mode_value = mode

        def apply() -> None:
            self.mode_var.set(mode)
            color = MODE_COLORS.get(mode, MODE_COLORS["FREEZE"])
            if self._frame:
                self._update_widget_bg(self._frame, color)
            self._last_mode_value = self.mode_var.get()

        self._run_or_enqueue(apply)

    def set_modes(self, modes, on_change: Optional[Callable[[str], None]]) -> None:
        modes_list = list(modes or [])
        modes_tuple = tuple(modes_list)
        self.on_mode_change = on_change
        if self._last_modes == modes_tuple:
            return
        self._last_modes = modes_tuple

        def apply() -> None:
            self.modes = modes_list
            self.on_mode_change = on_change
            menu = self.mode_menu["menu"]
            menu.delete(0, "end")
            for mode in self.modes:
                menu.add_command(
                    label=mode,
                    command=lambda value=mode: self._select_mode(value, on_change),
                )
            if self.mode_var.get() not in self.modes:
                if self.modes:
                    self.mode_var.set(self.modes[0])
                else:
                    self.mode_var.set("")
            self._last_mode_value = self.mode_var.get()

        self._run_or_enqueue(apply)

    def _select_mode(
        self, value: str, on_change: Optional[Callable[[str], None]]
    ) -> None:
        def apply() -> None:
            self.mode_var.set(value)
            self._last_mode_value = value
            if on_change:
                on_change(value)

        self._run_or_enqueue(apply)

    def _update_widget_bg(self, widget: tk.Widget, color: str) -> None:
        try:
            widget.configure(bg=color)
        except tk.TclError:
            pass
        for child in widget.winfo_children():
            self._update_widget_bg(child, color)

    def set_clock(self, clock_str: str) -> None:
        self._run_or_enqueue(lambda: self.clock_var.set(clock_str))

    def set_microgoal(self, text: Optional[str]) -> None:
        self._run_or_enqueue(lambda: self.micro_var.set(text or "(MicroGoal なし)"))

    def set_progress(self, text: Optional[str]) -> None:
        self._run_or_enqueue(lambda: self.progress_var.set(text or ""))

    def set_recommended(self, label: Optional[str], *, enabled: bool = True) -> None:
        def apply() -> None:
            state = tk.NORMAL if enabled else tk.DISABLED
            self.rec_btn.configure(text=label or "(Recommended)", state=state)

        self._run_or_enqueue(apply)

    def set_auto_enabled(self, enabled: bool) -> None:
        self._run_or_enqueue(lambda: self.auto_var.set(bool(enabled)))

    def set_actions(self, actions: list[tuple[str, str, int]]) -> None:
        def apply() -> None:
            self.actions_var = actions
            self.listbox.delete(0, tk.END)
            if not actions:
                self.listbox.insert(tk.END, "(no actions)")
                return
            for idx, (_, label, minutes) in enumerate(actions, start=1):
                suffix = f" (+{minutes}m)" if minutes else ""
                self.listbox.insert(tk.END, f"{idx}. {label}{suffix}")

        self._run_or_enqueue(apply)

    def run_async(self) -> None:
        # Tkの内部タイマーで自走。mainloopは使わない（協調ループ）
        # 1度だけ即座にフレーム処理しておくとウインドウが早く表示される。
        try:
            if threading.current_thread() is self._ui_thread:
                self._process_frame()
        except tk.TclError:
            return
        self.root.after(0, self._tick)

    def destroy(self) -> None:
        def tear_down() -> None:
            try:
                self.root.destroy()
            except tk.TclError:
                pass

        self._run_or_enqueue(tear_down)

    def _tick(self) -> None:
        # HUD側の周期処理があればここで実行（軽く保つ）
        if not self._process_frame():
            return
        self.root.after(33, self._tick)

    def pump(self) -> None:
        """メインループ側から1ステップだけイベントを捌く"""
        if threading.current_thread() is not self._ui_thread:
            self.request_update()
            return
        try:
            self._process_frame()
        except (tk.TclError, RuntimeError):
            pass

    def request_update(self) -> None:
        """Ensure the next UI pump runs on the Tk thread."""
        if threading.current_thread() is self._ui_thread:
            try:
                self._process_frame()
            except (tk.TclError, RuntimeError):
                pass
            return
        # 他スレッドからは安全に処理をキューへ投げる
        self._pending_calls.put(lambda: None)

    def _process_frame(self) -> bool:
        self._drain_pending_calls()
        try:
            self.root.update_idletasks()
            self.root.update()
        except tk.TclError:
            return False
        return True

    def _trigger_ai_step(self) -> None:
        if self.on_ai_step:
            self.on_ai_step()
        elif self.on_auto_action:
            self.on_auto_action()

    def _run_or_enqueue(self, func: Callable[[], None]) -> None:
        if threading.current_thread() is self._ui_thread:
            func()
        else:
            self._pending_calls.put(func)

    def _drain_pending_calls(self) -> None:
        while True:
            try:
                func = self._pending_calls.get_nowait()
            except queue.Empty:
                break
            try:
                func()
            except Exception:
                # Avoid crashing the UI loop due to background errors.
                pass

    def _click_recommended(self) -> None:
        if self.on_action_select:
            self.on_action_select("__recommended__")

    def _on_list_select(self, _event: object) -> None:
        selection = self.listbox.curselection()
        if not selection:
            return
        if self.on_action_select:
            self.on_action_select(selection[0])

    def _on_list_activate(self, _event: object) -> None:
        selection = self.listbox.curselection()
        if selection:
            self._run_index(selection[0])

    def _run_index(self, idx: int) -> None:
        if self.on_action_select:
            self.on_action_select(idx)
