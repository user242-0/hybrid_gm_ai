from __future__ import annotations

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
        self.root.geometry("420x180")
        self.root.attributes("-topmost", True)

        self.on_mode_change: Optional[Callable[[str], None]] = None
        self.on_auto_action: Optional[Callable[[], None]] = None
        self.on_save: Optional[Callable[[], None]] = None
        self.on_load: Optional[Callable[[], None]] = None
        self.on_show_micro: Optional[Callable[[], None]] = None

        self.mode_var = tk.StringVar(value="FREEZE")
        self.clock_var = tk.StringVar(value="Day1 08:00")
        self.micro_var = tk.StringVar(value="(MicroGoal 未設定)")

        self._frame: Optional[tk.Frame] = None
        self._running = False

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
        tk.Label(
            row1,
            textvariable=self.mode_var,
            fg="white",
            bg=frame["bg"],
            font=("Segoe UI", 12, "bold"),
        ).pack(side="left", padx=6)
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
            wraplength=380,
            justify="left",
        )
        self.micro_lbl.pack(side="left", padx=6)

        row3 = tk.Frame(frame, bg=frame["bg"])
        row3.pack(fill="x", **pad)
        tk.Label(
            row3,
            text="[Keys] 1:FREEZE 2:FLEE 3:PURSUE 4:WITNESS | G:Show Micro | A:Auto | S:Save L:Load",
            fg="white",
            bg=frame["bg"],
        ).pack(side="left")

    def _bind_keys(self) -> None:
        root = self.root
        root.bind("<Key-g>", lambda _: self.on_show_micro and self.on_show_micro())
        root.bind("<Key-G>", lambda _: self.on_show_micro and self.on_show_micro())
        root.bind("<Key-1>", lambda _: self._emit_mode("FREEZE"))
        root.bind("<Key-2>", lambda _: self._emit_mode("FLEE"))
        root.bind("<Key-3>", lambda _: self._emit_mode("PURSUE"))
        root.bind("<Key-4>", lambda _: self._emit_mode("WITNESS"))
        root.bind("<Key-a>", lambda _: self.on_auto_action and self.on_auto_action())
        root.bind("<Key-A>", lambda _: self.on_auto_action and self.on_auto_action())
        root.bind("<Key-s>", lambda _: self.on_save and self.on_save())
        root.bind("<Key-S>", lambda _: self.on_save and self.on_save())
        root.bind("<Key-l>", lambda _: self.on_load and self.on_load())
        root.bind("<Key-L>", lambda _: self.on_load and self.on_load())

    def _emit_mode(self, mode: str) -> None:
        if self.on_mode_change:
            self.on_mode_change(mode)
        self.set_mode(mode)

    def set_mode(self, mode: str) -> None:
        self.mode_var.set(mode)
        color = MODE_COLORS.get(mode, MODE_COLORS["FREEZE"])
        if not self._frame:
            return
        self._update_widget_bg(self._frame, color)

    def _update_widget_bg(self, widget: tk.Widget, color: str) -> None:
        try:
            widget.configure(bg=color)
        except tk.TclError:
            pass
        for child in widget.winfo_children():
            self._update_widget_bg(child, color)

    def set_clock(self, clock_str: str) -> None:
        self.clock_var.set(clock_str)

    def set_microgoal(self, text: Optional[str]) -> None:
        self.micro_var.set(text or "(MicroGoal なし)")

    def run_async(self) -> None:
        """Start polling tkinter in the background."""
        if self._running:
            return
        self._running = True
        self._tick()

    def destroy(self) -> None:
        self._running = False
        try:
            self.root.destroy()
        except tk.TclError:
            pass

    def _tick(self) -> None:
        if not self._running:
            return
        try:
            self.root.update_idletasks()
            self.root.update()
        except tk.TclError:
            self._running = False
            return
        self.root.after(33, self._tick)