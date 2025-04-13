# actions.py のサンプル（整理版）
from action_functions import move_forward, rest_with_event, perform_attack, generate_card_and_print

actions = {
    "進む": {
        "description": "洞窟やダンジョンの奥に進む。",
        "requirements": None,
        "effects": {"function": move_forward, "args": []},
        "available_to": ["player", "npc"],
    },
    "休む": {
        "description": "体力やスタミナを回復する。",
        "requirements": {"is_tired": True},
        "effects": {"function": rest_with_event, "args": []},
        "available_to": ["player", "npc"],
    },
    "攻撃する": {
        "description": "敵に対して攻撃を行う。",
        "requirements": {"has_weapon": True},
        "effects": {"function": perform_attack, "args": ["target"]},
        "available_to": ["player", "npc"],
    },
    "カード生成イベント": {
        "description": "新しいカードを生成し、印刷指示を出すイベントをトリガー。",
        "requirements": None,
        "effects": {"function": generate_card_and_print, "args": ["カード名"]},
        "available_to": ["GM_AI"],
    }
}
