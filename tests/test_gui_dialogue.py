from queue import Queue
from types import SimpleNamespace
import threading

import pytest

tk = pytest.importorskip("tkinter")
from src import gui


@pytest.fixture(scope="module")
def tk_root():
    try:
        root = tk.Tk()
    except tk.TclError as exc:
        pytest.skip(f"Tkinter display not available: {exc}")
    root.withdraw()
    yield root
    root.destroy()


@pytest.fixture
def console(monkeypatch, tk_root):
    """実ウィジェットとQueueを使い、GUIのpollだけ同期的に進める。"""
    root = tk.Toplevel(tk_root)
    root.withdraw()
    callbacks = []
    events, logs = Queue(), Queue()
    monkeypatch.setattr(gui.tk, "Tk", lambda: root)
    monkeypatch.setattr(root, "mainloop", lambda: None)
    monkeypatch.setattr(root, "after", lambda delay, callback: callbacks.append(callback))
    monkeypatch.setattr(gui, "event_q", events)
    monkeypatch.setattr(gui, "log_q", logs)

    class ImmediateThread:
        def __init__(self, *, target, daemon):
            self.target = target

        def start(self):
            self.target()

    monkeypatch.setattr(threading, "Thread", ImmediateThread)
    try:
        gui.start_gui({"running": True})
        root.deiconify()
        root.update()

        def descendants(widget):
            for child in widget.winfo_children():
                yield child
                yield from descendants(child)

        widgets = list(descendants(root))

        def pump(*messages):
            for message in messages:
                logs.put(message)
            callbacks.pop(0)()
            root.update()

        yield SimpleNamespace(
            root=root,
            turn=next(w for w in widgets if w.winfo_name() == "turn_text"),
            dialogue=next(w for w in widgets if w.winfo_name() == "dialogue_text"),
            scroll=next(w for w in widgets if isinstance(w, tk.Scrollbar)),
            entry=next(w for w in widgets if isinstance(w, tk.Entry)),
            events=events,
            pump=pump,
        )
    finally:
        root.destroy()


def contents(widget):
    return widget.get("1.0", "end-1c")


def test_dialogue_accumulates_with_speaker_tags(console):
    console.pump(
        {"mode": "dialogue", "speaker": "証人", "text": "……事故について、ですか？"},
        {"mode": "dialogue", "speaker": "刑事", "text": "はい。\n当時の話を聞かせてください。"},
    )

    assert contents(console.dialogue) == (
        "証人\n……事故について、ですか？\n\n"
        "刑事\nはい。\n当時の話を聞かせてください。\n\n"
    )
    ranges = console.dialogue.tag_ranges("speaker")
    assert [console.dialogue.get(a, b) for a, b in zip(ranges[::2], ranges[1::2])] == [
        "証人\n", "刑事\n",
    ]
    assert str(console.dialogue["state"]) == "disabled"
    assert contents(console.turn) == ""


def test_turn_note_and_character_display_updates_preserve_dialogue(console):
    console.pump(
        {"mode": "dialogue", "speaker": "証人", "text": "会話履歴"},
        {"mode": "turn", "reset": True, "text": "刑事 / MicroGoal: 聞き込み", "tag": "header"},
        {"mode": "note", "text": "補足", "tag": "rgb:10,20,30"},
    )
    history = contents(console.dialogue)
    assert "刑事 / MicroGoal" in contents(console.turn)
    assert console.turn.tag_cget("#0a141e", "foreground") == "#0a141e"
    assert console.turn.tag_ranges("#0a141e")

    console.pump(
        {"mode": "turn", "reset": True, "text": "愉快犯 / Actions: 潜伏", "tag": "green"},
        {"mode": "note", "reset": True, "text": "(red)警戒"},
    )
    assert contents(console.turn) == "愉快犯 / Actions: 潜伏\n\n警戒\n"
    assert console.turn.tag_ranges("green")
    assert console.turn.tag_ranges("red")
    assert str(console.turn["state"]) == "disabled"
    assert contents(console.dialogue) == history

    for mode in ("note_clear", "notes_clear", "turn_clear", "clear", "render"):
        console.pump({"mode": mode})
        assert contents(console.dialogue) == history


def test_dialogue_clear_only_clears_dialogue_and_preserves_queue_order(console):
    console.pump(
        {"mode": "turn", "text": "Action一覧"},
        {"mode": "note", "text": "MicroGoal"},
        {"mode": "dialogue", "speaker": "証人", "text": "古い発言"},
    )
    turn = contents(console.turn)
    console.pump({"mode": "dialogue_clear"})
    assert contents(console.dialogue) == ""
    assert contents(console.turn) == turn
    assert str(console.dialogue["state"]) == "disabled"

    console.pump(
        {"mode": "dialogue", "speaker": "証人", "text": "消える発言"},
        {"mode": "dialogue_clear"},
        {"mode": "dialogue", "speaker": "刑事", "text": "新しい発言"},
    )
    assert contents(console.dialogue) == "刑事\n新しい発言\n\n"
    assert contents(console.turn) == turn


def test_unknown_and_legacy_messages_are_ignored(console):
    console.pump(
        {"mode": "turn", "text": "Action一覧"},
        {"mode": "dialogue", "speaker": "証人", "text": "残す発言"},
    )
    before = contents(console.turn), contents(console.dialogue)
    console.pump(
        "legacy string",
        ("legacy tuple", "red"),
        {"text": "modeなし"},
        {"mode": "unknown", "speaker": "証人", "text": "表示しない"},
        {"mode": "dialogue", "speaker": "証人"},
        {"mode": "dialogue", "speaker": "証人", "text": ["不正な本文"]},
    )
    assert (contents(console.turn), contents(console.dialogue)) == before


def test_dialogue_scrolls_while_left_mousewheel_remains_blocked(console):
    console.pump(
        {"mode": "turn", "text": "\n".join(f"Action {i}" for i in range(100))},
        *({"mode": "dialogue", "speaker": "証人", "text": f"発言 {i}"} for i in range(60)),
    )
    assert console.dialogue.dlineinfo("end-3l") is not None
    assert console.dialogue.yview()[0] > 0.0
    # 実際のScrollbarコマンドを通して過去の発言へ戻る。
    console.root.tk.call(console.scroll["command"], "moveto", 0.0)
    console.root.update_idletasks()
    assert console.dialogue.yview()[0] == 0.0
    assert console.scroll.get()[0] == 0.0
    assert console.dialogue.get("@0,0", "@0,0 lineend") == "証人"

    before = console.turn.yview()
    console.turn.event_generate("<MouseWheel>", delta=120)
    assert console.turn.yview() == before
    assert console.turn.bind("<Button-4>")
    assert console.turn.bind("<Button-5>")
    assert console.dialogue.bind("<MouseWheel>") == ""


def test_entry_still_sends_trimmed_commands(console):
    console.entry.focus_force()
    console.root.update()
    console.entry.insert(0, "   ")
    console.entry.event_generate("<Return>")
    assert console.events.empty()

    console.entry.delete(0, tk.END)
    console.entry.insert(0, "  switch_character 愉快犯  ")
    console.entry.event_generate("<Return>")
    assert console.events.get_nowait() == "switch_character 愉快犯"
    assert console.events.empty()
    assert console.entry.get() == ""
