# actions.py のサンプル（整理版）
from action_functions import explore_location, move_forward, rest_with_event, perform_attack, engage_combat, avoid_combat, accept_attack ,generate_card_and_print, talk_to_statue, talk_to_statue_with_cooldown

actions = {
    "探索する": {
        "description": "現在のロケーションを探索する。",
        "requirements": None,
        "effects": {"function": explore_location, "args": []},
        "available_to": ["player", "npc"]
    },
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
    "戦う": {
        "description": "敵との戦闘に突入する。",
        "requirements": {"has_enemy": True},  # has_weaponを削除
        "effects": {"function": engage_combat, "args": []},
        "available_to": ["player", "npc"]
    },
    "戦わない": {
        "description": "戦闘を避けて逃げる。",
        "requirements": None,
        "effects": {"function": avoid_combat, "args": []},
        "available_to": ["player"]
    },
    "ただ、受け入れる": {
        "description": "無抵抗で相手の攻撃を受け止める。",
        "requirements": {"has_enemy": True},
        "effects": {"function": accept_attack, "args": []},
        "available_to": ["player"]
    },
    "石像に話す": {
        "description": "古代の石像に語りかけることで何かが起こるかもしれない。",
        "requirements": {
            "location": "祭壇",
            "target": "古代の石像"
        },
        "effects": {
            "function": talk_to_statue,
            "args": []
        },
        "available_to": ["player"]
    },

    "石像に話す（クールダウン）": {
        "description": "古代の石像に語りかける。連続での使用にはクールダウンが必要。",
        "requirements": {
            "location": "祭壇",
            "target": "古代の石像"
        },
        "effects": {
            "function": talk_to_statue_with_cooldown,
            "args": []
        },
        "available_to": ["player"],
    },
    
    "カード生成イベント": {
        "description": "新しいカードを生成し、印刷指示を出すイベントをトリガー。",
        "requirements": None,
        "effects": {"function": generate_card_and_print, "args": ["カード名"]},
        "available_to": ["GM_AI"],
    }
}
