"""Action definitions for both runtime actions and RC auto actions."""

from typing import Any, Dict

from src.actions import (
    accept_attack,
    avoid_combat,
    engage_combat,
    explore_location,
    generate_card_and_print,
    move_forward,
    npc_speak_and_log,
    perform_attack,
    rest_with_event,
    swing_sword,
    talk_to_statue,
    talk_to_statue_with_cooldown,
)
from src.control_manager import switch_character_action
from src.emotion_manager import set_emotion_color_action


actions = {
    "探索する": {
        "description": "現在のロケーションを探索する。",
        "function": explore_location,
        "args_template": [],
        "requirements": None,
        "available_to": ["player", "npc"],
    },
    "進む": {
        "description": "洞窟やダンジョンの奥に進む。",
        "function": move_forward,
        "args_template": [],
        "requirements": None,
        "available_to": ["player", "npc"],
    },
    "休む": {
        "description": "体力やスタミナを回復する。",
        "function": rest_with_event,
        "args_template": [],
        "requirements": {"is_tired": True},
        "available_to": ["player", "npc"],
    },
    "攻撃する": {
        "description": "敵に対して攻撃を行う。",
        "function": perform_attack,
        "args_template": ["<target_name>"],
        "requirements": {"has_weapon": True},
        "available_to": ["player", "npc"],
    },
    "swing_sword": {
        "description": "敵に対して剣を振るう。",
        "function": swing_sword,
        "args_template": ["<target_name>"],
        "requirements": {"equipped_weapon_is": "sword"},
        "available_to": ["player", "npc"],
    },
    "戦う": {
        "description": "敵との戦闘に突入する。",
        "function": engage_combat,
        "args_template": [],
        "requirements": {"has_enemy": True},  # has_weaponを削除
        "available_to": ["player", "npc"],
    },
    "戦わない": {
        "description": "戦闘を避けて逃げる。",
        "function": avoid_combat,
        "args_template": [],
        "requirements": {"has_enemy": True},
        "available_to": ["player"],
    },
    "ただ、受け入れる": {
        "description": "無抵抗で相手の攻撃を受け止める。",
        "function": accept_attack,
        "args_template": [],
        "requirements": {"has_enemy": True},
        "available_to": ["player"],
    },
    "石像に話す": {
        "description": "古代の石像に語りかけることで何かが起こるかもしれない。",
        "function": talk_to_statue,
        "args_template": [],
        "requirements": {
            "location": "祭壇",
            "target": "古代の石像",
            "time": "night",
        },
        "available_to": ["player"],
    },
    "石像に話す（クールダウン）": {
        "description": "古代の石像に語りかける。連続での使用にはクールダウンが必要。",
        "function": talk_to_statue_with_cooldown,
        "args_template": [],
        "requirements": {
            "location": "祭壇",
            "target": "古代の石像",
            "time": "night",
            "weather_is": "clear",
        },
        "available_to": ["player"],
    },
    "NPCが話す": {
        "description": "NPCが固定セリフを喋る。",
        "function": npc_speak_and_log,
        "args_template": ["NPC戦士", "greeting"],
        "requirements": None,
        "available_to": ["npc"],
    },
    "カード生成イベント": {
        "description": "新しいカードを生成し、印刷指示を出すイベントをトリガー。",
        "function": generate_card_and_print,
        "args_template": ["カード名"],
        "requirements": None,
        "available_to": ["GM_AI"],
    },
    "switch_character": {
        "description": "操作キャラクターを切り替える",
        "function": switch_character_action,  # ← ルート直下にく
        "args_template": ["<target_name>"],  # ← parse_args() が読むキー名
        "requirements": ["has_rc_in_party"],
        "available_to": ["player", "npc"],
    },
    "感情を設定する": {
        "description": "RGB値でプレイヤーの心の色を設定する",
        "function": set_emotion_color_action,
        "args_template": [],
        "requirements": None,
        "available_to": ["player", "npc"],
    },
}


# NOTE: ここに「本格的」に育てていく
ACTIONS: Dict[str, Dict[str, Any]] = {
    "limit_drink": {
        "label": "酒量を抑える",
        "time_min": 10,
        # R=衝動, G=自己制御, B=優しさ
        "emotion_delta": {"R": -10, "G": +7, "B": 0},
    },
    "check_tip": {
        "label": "未読の通報を1件だけ確認",
        "time_min": 5,
        "emotion_delta": {"R": -2, "G": +5, "B": +2},
    },
    "log_victim": {
        "label": "被害者の名前をノートに1人追記",
        "time_min": 3,
        "emotion_delta": {"R": 0, "G": +3, "B": +5},
    },
    "collect_fiber": {
        "label": "現場で青い繊維を1点採取",
        "time_min": 15,
        "emotion_delta": {"R": +2, "G": +5, "B": +2},
    },
    "fix_cam_clock": {
        "label": "監視カメラの時刻ズレを補正",
        "time_min": 12,
        "emotion_delta": {"R": 0, "G": +5, "B": +5},
    },
    "call_partner": {
        "label": "元相棒に5分だけ電話",
        "time_min": 5,
        "emotion_delta": {"R": -2, "G": 0, "B": +7},
    },
    "move_low_profile": {
        "label": "目立たず移動する",
        "time_min": 8,
        "emotion_delta": {"R": -2, "G": +5, "B": 0},
    },
    "mark_avoid_shop": {
        "label": "立ち寄り危険な店を避けるタグを付ける",
        "time_min": 4,
        "emotion_delta": {"R": -2, "G": +2, "B": +2},
    },
    "file_report": {
        "label": "報告書を提出する",
        "time_min": 20,
        "emotion_delta": {"R": -5, "G": +7, "B": +5},
    },
}


def get_action_def(action_id: str) -> Dict[str, Any]:
    return ACTIONS.get(action_id, {})
