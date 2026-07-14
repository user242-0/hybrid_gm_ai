
from __future__ import annotations

import queue
import threading
import tkinter as tk
from dataclasses import dataclass
from tkinter import ttk
from typing import Callable, Optional

from src.utility.config_loader import (
    is_hud_debug_enabled,
    is_hud_demo_enabled,
    is_hud_intelligence_panel_enabled,
)

MODE_COLORS = {
    "FREEZE": "#3b3b3b",
    "FLEE": "#2f4f4f",
    "PURSUE": "#0b3d91",
    "WITNESS": "#5a2a83",
}

MAX_ADVISORY_DISPLAY_ITEMS = 3

HUD_FONT_SIZES = {
    "normal": 9,
    "demo": 14,
    "debug": 9,
}

HUD_WINDOW_SIZES = {
    "normal": (960, 480),
    "demo": (1240, 680),
    "debug": (1120, 720),
}

HUD_PANE_MIN_WIDTHS = {
    "normal": (480, 320),
    "demo": (620, 400),
    "debug": (560, 380),
}

HUD_WRAPLENGTHS = {
    "normal": {"operational": 500, "intelligence": 330},
    "demo": {"operational": 650, "intelligence": 430},
    "debug": {"operational": 590, "intelligence": 390},
}

INTELLIGENCE_COLORS = {
    "header": "#DCEBFF",
    "active": "#80FF80",
    "rc": "#FFCB80",
    "ro": "#FFD700",
    "external": "#9FE7FF",
    "border": "#617080",
    "muted": "#AAB4C0",
    "affect_fallback": "#7A8490",
}


@dataclass(frozen=True)
class HUDDisplayMode:
    name: str
    show_actor_mode_control: bool
    show_demo_controls: bool
    show_wip_controls: bool
    show_debug_controls: bool


def resolve_hud_display_mode(
    *,
    debug_enabled: bool,
    demo_enabled: bool,
) -> HUDDisplayMode:
    """Resolve HUD visibility, with HUD_DEBUG taking precedence over HUD_DEMO."""
    if debug_enabled:
        return HUDDisplayMode(
            name="debug",
            show_actor_mode_control=True,
            show_demo_controls=True,
            show_wip_controls=True,
            show_debug_controls=True,
        )
    if demo_enabled:
        return HUDDisplayMode(
            name="demo",
            show_actor_mode_control=True,
            show_demo_controls=True,
            show_wip_controls=False,
            show_debug_controls=False,
        )
    return HUDDisplayMode(
        name="normal",
        show_actor_mode_control=False,
        show_demo_controls=False,
        show_wip_controls=False,
        show_debug_controls=False,
    )


def format_actor_mode_label(actor_id: object) -> str:
    actor_name = _display_text(actor_id) or "?"
    return f"ActorMode({actor_name}):"


def format_active_rc_summary(actor_id: object, mode: object) -> str:
    actor_name = _display_text(actor_id)
    actor_mode = _display_text(mode)
    if not actor_name:
        return ""
    return f"{actor_name} / {actor_mode or '?'}"


def rc_advisory_initially_expanded(display_mode_name: str) -> bool:
    return display_mode_name in {"demo", "debug"}


def _normalize_affect_rgb(value: object) -> tuple[int, int, int] | None:
    if isinstance(value, dict):
        raw_values = [value.get(axis) for axis in ("R", "G", "B")]
    elif isinstance(value, (list, tuple)) and len(value) >= 3:
        raw_values = list(value[:3])
    else:
        return None

    channels: list[int] = []
    for raw in raw_values:
        if isinstance(raw, bool) or not isinstance(raw, (int, float)):
            return None
        channels.append(max(0, min(255, int(raw))))
    return tuple(channels)


def _format_affect_value(value: object, *, debug: bool) -> str:
    rgb = _normalize_affect_rgb(value)
    if not debug or rgb is None:
        return ""
    return f"RGB({rgb[0]}, {rgb[1]}, {rgb[2]})"


def advisory_heading_for_mode(display_mode_name: str) -> str:
    return "提案候補:" if display_mode_name == "demo" else "AI提案:"


def _display_text(value: object) -> str:
    return "" if value is None else str(value)


def _format_advisory_items(items: list[dict] | None) -> str:
    if not items:
        return ""

    lines: list[str] = []
    for item in items[:MAX_ADVISORY_DISPLAY_ITEMS]:
        if not isinstance(item, dict):
            continue
        title = _display_text(item.get("title"))
        subtitle = _display_text(item.get("subtitle"))
        detail = _display_text(item.get("detail"))

        first_line = f"• {title}"
        if subtitle:
            first_line = f"{first_line} — {subtitle}"
        lines.append(first_line)
        if detail:
            lines.append(f"  {detail}")

    return "\n".join(lines)


def _format_rc_advisory(
    display_item: dict | None,
    *,
    debug: bool = False,
) -> str:
    if not isinstance(display_item, dict):
        return ""

    actor_label = _display_text(display_item.get("actor_label"))
    intent_label = _display_text(display_item.get("intent_label"))
    action_label = _display_text(display_item.get("action_label"))
    reason = _display_text(display_item.get("reason"))
    if not actor_label or not intent_label or not action_label:
        return ""

    lines = [
        f"（{actor_label}）",
        f"意図: {intent_label}",
        f"候補: {action_label}",
    ]
    if reason:
        lines.append(f"理由: {reason}")

    debug_data = display_item.get("debug")
    if debug and isinstance(debug_data, dict):
        lines.append("[DEBUG]")
        for key in (
            "selected_intent",
            "preferred_action_id",
            "preferred_action_layer",
            "preferred_params",
            "confidence",
            "auto_execute",
        ):
            lines.append(f"{key}: {_display_text(debug_data.get(key))}")

    return "\n".join(lines)


class DirectorHUD:
    """Small top-level window that exposes quick director controls."""

    def __init__(self, title: str = "Director HUD") -> None:
        self.display_mode = resolve_hud_display_mode(
            debug_enabled=is_hud_debug_enabled(),
            demo_enabled=is_hud_demo_enabled(),
        )
        self._debug = self.display_mode.show_debug_controls
        self.show_actor_mode_control = self.display_mode.show_actor_mode_control
        self.show_demo_controls = self.display_mode.show_demo_controls
        self.show_wip_controls = self.display_mode.show_wip_controls
        self.show_debug_controls = self.display_mode.show_debug_controls
        self.show_intelligence_panel = is_hud_intelligence_panel_enabled()
        self._rc_advisory_expanded = rc_advisory_initially_expanded(
            self.display_mode.name
        )
        self._rc_advisory_available = False

        self.root = tk.Tk()
        self.root.title(title)
        self._set_initial_geometry()
        min_width, min_height = HUD_WINDOW_SIZES[self.display_mode.name]
        self.root.minsize(min_width, min_height)
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
        self.on_inject_discovery: Optional[Callable[[str], None]] = None
        self.on_actor_mode_change: Optional[Callable[[str], None]] = None

        self.mode_var = tk.StringVar(value="")
        self.actor_mode_label_var = tk.StringVar(value=format_actor_mode_label(None))
        self.actor_mode_var = tk.StringVar(value="")
        self.clock_var = tk.StringVar(value="Day1 00:00")
        self.micro_var = tk.StringVar(value="(MicroGoal 未設定)")
        self.operation_var = tk.StringVar(value="Operation(?): なし")
        self.perceived_world_var = tk.StringVar(value="")
        self.progress_var = tk.StringVar(value="")
        self.ro_var = tk.StringVar(value="")
        self.advisory_var = tk.StringVar(value="")
        self.rc_advisory_var = tk.StringVar(value="")
        self.rc_advisory_status_var = tk.StringVar(value="")
        self.active_rc_var = tk.StringVar(value="")
        self.affect_value_var = tk.StringVar(value="")
        self.auto_var = tk.BooleanVar(value=False)
        self.location_var = tk.StringVar(value="")

        self._on_location_change_cb: Optional[Callable[[str], None]] = None

        self.actions_var: list[tuple[str, str, int]] = []
        self.modes: list[str] = []

        self._last_modes: Optional[tuple[str, ...]] = None
        self._last_mode_value: Optional[str] = None

        self._frame: Optional[tk.Frame] = None
        self.main_paned: Optional[tk.PanedWindow] = None
        self.operational_pane: Optional[tk.Frame] = None
        self.intelligence_pane: Optional[tk.Frame] = None
        self.rc_advisory_content_frame: Optional[tk.Frame] = None
        self.rc_advisory_toggle_button: Optional[tk.Button] = None
        self.affect_indicator_label: Optional[tk.Label] = None
        self._ui_thread = threading.current_thread()
        self._pending_calls: "queue.Queue[Callable[[], None]]" = queue.Queue()

        self._build()
        self._bind_keys()
        self.set_mode("FREEZE")

    def _set_initial_geometry(self) -> None:
        """Set the initial size once; refresh paths must not reset user positioning."""
        width, height = HUD_WINDOW_SIZES[self.display_mode.name]
        self.root.geometry(f"{width}x{height}")

    def _build(self) -> None:
        font_size = HUD_FONT_SIZES[self.display_mode.name]
        normal_font = ("TkDefaultFont", font_size)
        bold_font = ("TkDefaultFont", font_size, "bold")
        wraplengths = HUD_WRAPLENGTHS[self.display_mode.name]
        operational_wrap = wraplengths["operational"]
        intelligence_wrap = wraplengths["intelligence"]
        pad = (
            {"padx": 12, "pady": 6}
            if self.display_mode.name == "demo"
            else {"padx": 8, "pady": 4}
        )

        frame = tk.Frame(self.root, bg=MODE_COLORS["FREEZE"])
        frame.pack(fill="both", expand=True)
        self._frame = frame

        self.main_paned = tk.PanedWindow(
            frame,
            orient=tk.HORIZONTAL,
            bd=0,
            relief=tk.FLAT,
            sashwidth=6,
            sashrelief=tk.RAISED,
            opaqueresize=True,
            showhandle=False,
            bg=frame["bg"],
        )
        self.main_paned.pack(fill="both", expand=True)
        self.operational_pane = tk.Frame(self.main_paned, bg=frame["bg"])
        window_width, _window_height = HUD_WINDOW_SIZES[self.display_mode.name]
        left_width = int(window_width * 0.60)
        right_width = window_width - left_width
        left_min_width, right_min_width = HUD_PANE_MIN_WIDTHS[
            self.display_mode.name
        ]
        self.main_paned.add(
            self.operational_pane,
            width=left_width,
            minsize=left_min_width,
            stretch="always",
        )
        operational = self.operational_pane

        if self.show_intelligence_panel:
            self.intelligence_pane = tk.Frame(self.main_paned, bg=frame["bg"])
            self.main_paned.add(
                self.intelligence_pane,
                width=right_width,
                minsize=right_min_width,
                stretch="always",
            )

        row1 = tk.Frame(operational, bg=frame["bg"])
        row1.pack(fill="x", **pad)
        tk.Label(
            row1,
            text="DirectorMode:",
            fg="white",
            bg=frame["bg"],
            font=bold_font,
        ).pack(side="left")
        self.mode_menu = tk.OptionMenu(row1, self.mode_var, "")
        self.mode_menu.configure(highlightthickness=0, font=normal_font)
        self.mode_menu["menu"].configure(font=normal_font)
        self.mode_menu.pack(side="left")
        tk.Label(
            row1,
            text="Clock:",
            fg="white",
            bg=frame["bg"],
            font=bold_font,
        ).pack(side="left", padx=12)
        tk.Label(
            row1,
            textvariable=self.clock_var,
            fg="white",
            bg=frame["bg"],
            font=normal_font,
        ).pack(side="left", padx=6)

        row_actor_mode = tk.Frame(operational, bg=frame["bg"])
        row_actor_mode.pack(fill="x", **pad)
        tk.Label(
            row_actor_mode,
            textvariable=self.actor_mode_label_var,
            fg="#80FF80" if self._debug else "white",
            bg=frame["bg"],
            font=bold_font,
        ).pack(side="left")
        if self.show_actor_mode_control:
            self.actor_mode_combo = ttk.Combobox(
                row_actor_mode,
                textvariable=self.actor_mode_var,
                state="readonly",
                width=14,
                font=normal_font,
            )
            self.actor_mode_combo.pack(side="left", padx=4)
            self.actor_mode_combo.bind(
                "<<ComboboxSelected>>",
                self._on_actor_mode_change,
            )
        else:
            self.actor_mode_combo = None
            tk.Label(
                row_actor_mode,
                textvariable=self.actor_mode_var,
                fg="white",
                bg=frame["bg"],
                font=normal_font,
            ).pack(side="left", padx=4)

        # --- Debug: location controls ---
        if self.show_debug_controls:
            row_loc = tk.Frame(operational, bg=frame["bg"])
            row_loc.pack(fill="x", **pad)
            tk.Label(row_loc, text="\U0001f4cd", fg="white", bg=frame["bg"]).pack(side="left")
            self.location_combo = ttk.Combobox(
                row_loc, textvariable=self.location_var, state="readonly", width=24,
            )
            self.location_combo.pack(side="left", padx=4)
            self.location_combo.bind("<<ComboboxSelected>>", self._on_location_change)
        else:
            self.location_combo = None

        # --- Debug: discovery injection ---
        if self.show_debug_controls:
            row_disc = tk.Frame(operational, bg=frame["bg"])
            row_disc.pack(fill="x", **pad)
            tk.Label(row_disc, text="\U0001f50d Disc:", fg="#80FF80", bg=frame["bg"]).pack(side="left")
            self._disc_var = tk.StringVar(value="")
            self._disc_combo = ttk.Combobox(
                row_disc, textvariable=self._disc_var, state="readonly", width=30,
            )
            self._disc_combo.pack(side="left", padx=4)
            tk.Button(
                row_disc, text="Inject", command=self._on_inject_click,
            ).pack(side="left", padx=4)

        row2 = tk.Frame(operational, bg=frame["bg"])
        row2.pack(fill="x", **pad)
        tk.Label(
            row2,
            text="MicroGoal:",
            fg="white",
            bg=frame["bg"],
            font=bold_font,
        ).pack(side="left")
        self.micro_lbl = tk.Label(
            row2,
            textvariable=self.micro_var,
            fg="white",
            bg=frame["bg"],
            wraplength=operational_wrap,
            justify="left",
            font=normal_font,
        )
        self.micro_lbl.pack(side="left", padx=6)

        row_operation = tk.Frame(operational, bg=frame["bg"])
        row_operation.pack(fill="x", **pad)
        self.operation_lbl = tk.Label(
            row_operation,
            textvariable=self.operation_var,
            fg="white",
            bg=frame["bg"],
            wraplength=operational_wrap,
            justify="left",
            font=normal_font,
        )
        self.operation_lbl.pack(side="left", padx=6)

        if self.show_debug_controls:
            row_perceived = tk.Frame(operational, bg=frame["bg"])
            row_perceived.pack(fill="x", **pad)
            self.perceived_world_lbl = tk.Label(
                row_perceived,
                textvariable=self.perceived_world_var,
                fg="#CDEB8B",
                bg=frame["bg"],
                wraplength=operational_wrap,
                justify="left",
                font=normal_font,
            )
            self.perceived_world_lbl.pack(side="left", padx=6)
        else:
            self.perceived_world_lbl = None

        if self.show_wip_controls:
            rowp = tk.Frame(operational, bg=frame["bg"])
            rowp.pack(fill="x", **pad)
            tk.Label(
                rowp,
                text="Progress:",
                fg="white",
                bg=frame["bg"],
                font=bold_font,
            ).pack(side="left")
            tk.Label(
                rowp,
                textvariable=self.progress_var,
                fg="white",
                bg=frame["bg"],
                wraplength=operational_wrap,
                justify="left",
                font=normal_font,
            ).pack(side="left", padx=6)

            row_rec = tk.Frame(operational, bg=frame["bg"])
            row_rec.pack(fill="x", **pad)
            self.rec_btn = tk.Button(
                row_rec,
                text="(Recommended)",
                command=self._click_recommended,
            )
            self.rec_btn.pack(side="left")

        else:
            self.rec_btn = None

        row_actions = tk.Frame(operational, bg=frame["bg"])
        row_actions.pack(fill="both", expand=True, **pad)
        tk.Label(
            row_actions,
            text="Actions:",
            fg="white",
            bg=frame["bg"],
            font=bold_font,
        ).pack(anchor="w")
        self.listbox = tk.Listbox(
            row_actions,
            height=8 if self.display_mode.name == "demo" else 7,
            font=normal_font,
        )
        self.listbox.pack(fill="both", expand=True)
        self.listbox.bind("<<ListboxSelect>>", self._on_list_select)
        self.listbox.bind("<Double-Button-1>", self._on_list_activate)
        self.listbox.bind("<Return>", self._on_list_activate)

        help_text = (
            "[Keys] Use Mode dropdown | 1..9:Run Action | G:Show Micro | R:Reroll Micro | "
            "A:Next(AI) | S:Save L:Load"
        )
        self.help_text = help_text
        if self._debug:
            row_auto = tk.Frame(operational, bg=frame["bg"])
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

            row3 = tk.Frame(operational, bg=frame["bg"])
            row3.pack(fill="x", **pad)
            self.help_label = tk.Label(
                row3,
                text=help_text,
                fg="white",
                bg=frame["bg"],
                justify="left",
                wraplength=operational_wrap,
            )
            self.help_label.pack(side="left")
        else:
            self.help_label = None

        if not self.show_intelligence_panel or self.intelligence_pane is None:
            self.intelligence_heading_label = None
            self.active_rc_heading_label = None
            self.rc_advisory_heading_label = None
            self.ro_heading_label = None
            self.external_heading_label = None
            self.ro_label = None
            self.advisory_label = None
            self.rc_advisory_label = None
            return

        intelligence = self.intelligence_pane
        section_pad = 10 if self.display_mode.name == "demo" else 7
        self.intelligence_heading_label = tk.Label(
            intelligence,
            text="INTELLIGENCE PANEL",
            fg=INTELLIGENCE_COLORS["header"],
            bg=frame["bg"],
            font=bold_font,
            anchor="w",
        )
        self.intelligence_heading_label.pack(
            fill="x", padx=section_pad, pady=(section_pad, 4)
        )

        def section_frame() -> tk.Frame:
            section = tk.Frame(
                intelligence,
                bg=frame["bg"],
                highlightthickness=1,
                highlightbackground=INTELLIGENCE_COLORS["border"],
            )
            section.pack(fill="x", padx=section_pad, pady=(3, 5))
            return section

        active_section = section_frame()
        self.active_rc_heading_label = tk.Label(
            active_section,
            text="ACTIVE RC",
            fg=INTELLIGENCE_COLORS["active"],
            bg=frame["bg"],
            font=bold_font,
            anchor="w",
        )
        self.active_rc_heading_label.pack(fill="x", padx=6, pady=(5, 1))
        tk.Label(
            active_section,
            textvariable=self.active_rc_var,
            fg="white",
            bg=frame["bg"],
            font=normal_font,
            anchor="w",
        ).pack(fill="x", padx=6, pady=(0, 3))
        affect_row = tk.Frame(active_section, bg=frame["bg"])
        affect_row.pack(fill="x", padx=6, pady=(1, 6))
        tk.Label(
            affect_row,
            text="AFFECT",
            fg=INTELLIGENCE_COLORS["muted"],
            bg=frame["bg"],
            font=bold_font,
        ).pack(side="left")
        self.affect_indicator_label = tk.Label(
            affect_row,
            text="●",
            fg=INTELLIGENCE_COLORS["affect_fallback"],
            bg=frame["bg"],
            bd=1,
            relief=tk.SOLID,
            highlightthickness=1,
            highlightbackground=INTELLIGENCE_COLORS["border"],
            font=normal_font,
            padx=2,
        )
        self.affect_indicator_label.pack(side="left", padx=(6, 4))
        tk.Label(
            affect_row,
            textvariable=self.affect_value_var,
            fg=INTELLIGENCE_COLORS["muted"],
            bg=frame["bg"],
            font=normal_font,
        ).pack(side="left")

        rc_section = section_frame()
        self.rc_advisory_toggle_button = tk.Button(
            rc_section,
            text=self._rc_advisory_toggle_text(),
            command=self._toggle_rc_advisory,
            fg=INTELLIGENCE_COLORS["rc"],
            bg=frame["bg"],
            activeforeground=INTELLIGENCE_COLORS["rc"],
            activebackground=frame["bg"],
            font=bold_font,
            relief=tk.FLAT,
            bd=0,
            anchor="w",
            justify="left",
            wraplength=intelligence_wrap,
        )
        self.rc_advisory_toggle_button.pack(fill="x", padx=4, pady=(3, 0))
        self.rc_advisory_heading_label = self.rc_advisory_toggle_button
        tk.Label(
            rc_section,
            text="現在文脈から生成された潜在意図・継続候補",
            fg=INTELLIGENCE_COLORS["muted"],
            bg=frame["bg"],
            font=normal_font,
            wraplength=intelligence_wrap,
            justify="left",
            anchor="w",
        ).pack(fill="x", padx=6, pady=(0, 2))
        tk.Label(
            rc_section,
            textvariable=self.rc_advisory_status_var,
            fg=INTELLIGENCE_COLORS["rc"],
            bg=frame["bg"],
            font=normal_font,
            anchor="w",
        ).pack(fill="x", padx=6)
        self.rc_advisory_content_frame = tk.Frame(rc_section, bg=frame["bg"])
        self.rc_advisory_label = tk.Label(
            self.rc_advisory_content_frame,
            textvariable=self.rc_advisory_var,
            fg=INTELLIGENCE_COLORS["rc"],
            bg=frame["bg"],
            wraplength=intelligence_wrap,
            justify="left",
            anchor="w",
            font=normal_font,
        )
        self.rc_advisory_label.pack(fill="x", padx=6, pady=(2, 6))
        if self._rc_advisory_expanded:
            self.rc_advisory_content_frame.pack(fill="x")

        ro_section = section_frame()
        self.ro_heading_label = tk.Label(
            ro_section,
            text="[RO] RO STRATEGY",
            fg=INTELLIGENCE_COLORS["ro"],
            bg=frame["bg"],
            font=bold_font,
            anchor="w",
        )
        self.ro_heading_label.pack(fill="x", padx=6, pady=(5, 1))
        self.ro_label = tk.Label(
            ro_section,
            textvariable=self.ro_var,
            fg=INTELLIGENCE_COLORS["ro"],
            bg=frame["bg"],
            wraplength=intelligence_wrap,
            justify="left",
            anchor="w",
            font=normal_font,
        )
        self.ro_label.pack(fill="x", padx=6, pady=(0, 6))

        external_section = section_frame()
        self.external_heading_label = tk.Label(
            external_section,
            text="[EXT] EXTERNAL PROPOSALS",
            fg=INTELLIGENCE_COLORS["external"],
            bg=frame["bg"],
            font=bold_font,
            anchor="w",
        )
        self.external_heading_label.pack(fill="x", padx=6, pady=(5, 1))
        self.advisory_label = tk.Label(
            external_section,
            textvariable=self.advisory_var,
            fg=INTELLIGENCE_COLORS["external"],
            bg=frame["bg"],
            wraplength=intelligence_wrap,
            justify="left",
            anchor="w",
            font=normal_font,
        )
        self.advisory_label.pack(fill="x", padx=6, pady=(0, 6))

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

    def set_actor_modes(
        self,
        modes,
        on_change: Optional[Callable[[str], None]],
    ) -> None:
        self.on_actor_mode_change = on_change
        if not self.show_actor_mode_control or self.actor_mode_combo is None:
            return
        modes_list = list(modes or [])

        def apply() -> None:
            self.on_actor_mode_change = on_change
            self.actor_mode_combo["values"] = modes_list

        self._run_or_enqueue(apply)

    def set_actor_mode(self, actor_id: Optional[str], mode: str) -> None:
        def apply() -> None:
            self.actor_mode_label_var.set(format_actor_mode_label(actor_id))
            self.actor_mode_var.set(mode or "")
            self.active_rc_var.set(format_active_rc_summary(actor_id, mode))

        self._run_or_enqueue(apply)

    def _rc_advisory_toggle_text(self) -> str:
        marker = "▼" if self._rc_advisory_expanded else "▶"
        return f"{marker} [RC] RC_AI判断 / INTERPRETATION"

    def _sync_rc_advisory_status(self) -> None:
        status = (
            "● 潜在意図あり"
            if getattr(self, "_rc_advisory_available", False)
            and not getattr(self, "_rc_advisory_expanded", True)
            else ""
        )
        status_var = getattr(self, "rc_advisory_status_var", None)
        if status_var is not None:
            status_var.set(status)

    def _toggle_rc_advisory(self) -> None:
        def apply() -> None:
            self._rc_advisory_expanded = not self._rc_advisory_expanded
            if self.rc_advisory_toggle_button is not None:
                self.rc_advisory_toggle_button.configure(
                    text=self._rc_advisory_toggle_text()
                )
            content = self.rc_advisory_content_frame
            if content is not None:
                if self._rc_advisory_expanded:
                    if not content.winfo_manager():
                        content.pack(fill="x")
                else:
                    content.pack_forget()
            self._sync_rc_advisory_status()

        self._run_or_enqueue(apply)

    def _on_actor_mode_change(self, _event: object) -> None:
        value = self.actor_mode_var.get()
        if value and self.on_actor_mode_change:
            self.on_actor_mode_change(value)

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

    def set_operation_summary(self, text: Optional[str]) -> None:
        self._run_or_enqueue(lambda: self.operation_var.set(text or "Operation(?): なし"))

    def set_perceived_world_summary(self, text: Optional[str]) -> None:
        if not self.show_debug_controls:
            return
        self._run_or_enqueue(lambda: self.perceived_world_var.set(text or ""))

    def set_progress(self, text: Optional[str]) -> None:
        self._run_or_enqueue(lambda: self.progress_var.set(text or ""))

    def set_ro_recommendation(self, text: Optional[str]) -> None:
        self._run_or_enqueue(lambda: self.ro_var.set(text or ""))

    def set_advisory_items(self, items: list[dict] | None) -> None:
        text = _format_advisory_items(items)
        self._run_or_enqueue(lambda: self.advisory_var.set(text))

    def set_rc_advisory(self, display_item: dict | None) -> None:
        text = _format_rc_advisory(
            display_item,
            debug=bool(getattr(self, "show_debug_controls", False)),
        )

        def apply() -> None:
            self.rc_advisory_var.set(text)
            self._rc_advisory_available = bool(text)
            DirectorHUD._sync_rc_advisory_status(self)

        self._run_or_enqueue(apply)

    def set_affect(self, emotion: object | None) -> None:
        rgb = _normalize_affect_rgb(emotion)
        color = (
            f"#{rgb[0]:02X}{rgb[1]:02X}{rgb[2]:02X}"
            if rgb is not None
            else INTELLIGENCE_COLORS["affect_fallback"]
        )
        value_text = _format_affect_value(
            emotion,
            debug=bool(getattr(self, "show_debug_controls", False)),
        )

        def apply() -> None:
            self.affect_value_var.set(value_text)
            if self.affect_indicator_label is not None:
                self.affect_indicator_label.configure(fg=color)

        self._run_or_enqueue(apply)

    def set_location(self, text: str) -> None:
        def apply() -> None:
            self.location_var.set(text)
        self._run_or_enqueue(apply)

    def set_location_options(self, options: list[str]) -> None:
        if not self.show_debug_controls or self.location_combo is None:
            return
        def apply() -> None:
            self.location_combo["values"] = options
        self._run_or_enqueue(apply)

    def set_location_change_callback(self, fn: Callable[[str], None]) -> None:
        self._on_location_change_cb = fn

    def _on_location_change(self, _event: object) -> None:
        value = self.location_var.get()
        if self._on_location_change_cb:
            self._on_location_change_cb(value)

    def set_recommended(self, label: Optional[str], *, enabled: bool = True) -> None:
        if self.rec_btn is None:
            return

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
        # mainloopは使わず、simulation側の協調ループからpump()する。
        # 初回だけ即座に処理して、ウインドウを早く表示する。
        try:
            if threading.current_thread() is self._ui_thread:
                self._process_frame()
        except tk.TclError:
            return

    def destroy(self) -> None:
        def tear_down() -> None:
            try:
                self.root.destroy()
            except tk.TclError:
                pass

        self._run_or_enqueue(tear_down)

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

    # --- Debug: discovery injection ---

    def set_discovery_options(self, options: list[str]) -> None:
        if not self.show_debug_controls or not hasattr(self, "_disc_combo"):
            return
        def apply() -> None:
            self._disc_combo["values"] = options
        self._run_or_enqueue(apply)

    def _on_inject_click(self) -> None:
        disc_id = self._disc_var.get()
        if disc_id and self.on_inject_discovery:
            self.on_inject_discovery(disc_id)
