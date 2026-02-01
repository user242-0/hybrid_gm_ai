"""Action definitions for both runtime actions and RC auto actions."""

from __future__ import annotations

from typing import Any, Dict, Iterable, Optional

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
    talk,
    talk_to_statue,
    talk_to_statue_with_cooldown,
)
from src.control_manager import switch_character_action
from src.emotion_manager import set_emotion_color_action
from src.action_model import ActionSpec


# --- UI表示用アクション定義 ---
# label: 表示名（日本語）
# ui_visible: UIに表示するか（デフォルトTrue）
# heart: {axis, value} - 選択肢の色/感情値
# id_aliases: 旧キー互換用（日本語キーなど）

actions = {
    "explore": {
        "label": "探索する",
        "description": "現在のロケーションを探索する。",
        "function": explore_location,
        "args_template": [],
        "requirements": None,
        "available_to": ["player", "npc"],
        "ui_visible": True,
        "heart": {"axis": "blue", "value": 80},
        "id_aliases": ["探索する"],
    },
    "move_forward": {
        "label": "進む",
        "description": "洞窟やダンジョンの奥に進む。",
        "function": move_forward,
        "args_template": [],
        "requirements": None,
        "available_to": ["player", "npc"],
        "ui_visible": True,
        "heart": {"axis": "blue", "value": 100},
        "id_aliases": ["進む"],
    },
    "rest": {
        "label": "休む",
        "description": "体力やスタミナを回復する。",
        "function": rest_with_event,
        "args_template": [],
        "requirements": {"is_tired": True},
        "available_to": ["player", "npc"],
        "ui_visible": True,
        "heart": {"axis": "blue", "value": 100},
        "id_aliases": ["休む"],
    },
    "attack": {
        "label": "攻撃する",
        "description": "敵に対して攻撃を行う。",
        "function": perform_attack,
        "args_template": ["<target_name>"],
        "requirements": {"has_weapon": True},
        "available_to": ["player", "npc"],
        "ui_visible": True,
        "heart": {"axis": "blue", "value": 200},
        "id_aliases": ["攻撃する"],
    },
    "swing_sword": {
        "label": "剣を振る",
        "description": "敵に対して剣を振るう。",
        "function": swing_sword,
        "args_template": ["<target_name>"],
        "requirements": {"equipped_weapon_is": "sword"},
        "available_to": ["player", "npc"],
        "ui_visible": True,
        "heart": {"axis": "blue", "value": 200},
        "id_aliases": [],
    },
    "engage_combat": {
        "label": "戦う",
        "description": "敵との戦闘に突入する。",
        "function": engage_combat,
        "args_template": [],
        "requirements": {"has_enemy": True},
        "available_to": ["player", "npc"],
        "ui_visible": True,
        "heart": {"axis": "red", "value": 250},
        "id_aliases": ["戦う"],
    },
    "avoid_combat": {
        "label": "戦わない",
        "description": "戦闘を避けて逃げる。",
        "function": avoid_combat,
        "args_template": [],
        "requirements": {"has_enemy": True},
        "available_to": ["player"],
        "ui_visible": True,
        "heart": {"axis": "red", "value": 180},
        "id_aliases": ["戦わない"],
    },
    "accept_attack": {
        "label": "ただ、受け入れる",
        "description": "無抵抗で相手の攻撃を受け止める。",
        "function": accept_attack,
        "args_template": [],
        "requirements": {"has_enemy": True},
        "available_to": ["player"],
        "ui_visible": True,
        "heart": {"axis": "red", "value": 180},
        "id_aliases": ["ただ、受け入れる"],
    },
    "talk_to_statue": {
        "label": "石像に話す",
        "description": "古代の石像に語りかけることで何かが起こるかもしれない。",
        "function": talk_to_statue,
        "args_template": [],
        "requirements": {
            "location": "祭壇",
            "target": "古代の石像",
            "time": "night",
        },
        "available_to": ["player"],
        "ui_visible": True,
        "heart": {"axis": "blue", "value": 80},
        "id_aliases": ["石像に話す"],
    },
    "talk_to_statue_cooldown": {
        "label": "石像に話す（クールダウン）",
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
        "ui_visible": True,
        "heart": {"axis": "blue", "value": 100},
        "id_aliases": ["石像に話す（クールダウン）"],
    },
    "npc_speak": {
        "label": "NPCが話す",
        "description": "NPCが固定セリフを喋る。",
        "function": npc_speak_and_log,
        "args_template": ["NPC戦士", "greeting"],
        "requirements": None,
        "available_to": ["npc"],
        "ui_visible": False,  # 内部用
        "heart": {"axis": "green", "value": 100},
        "id_aliases": ["NPCが話す"],
    },
    "generate_card": {
        "label": "カード生成イベント",
        "description": "新しいカードを生成し、印刷指示を出すイベントをトリガー。",
        "function": generate_card_and_print,
        "args_template": ["カード名"],
        "requirements": None,
        "available_to": ["GM_AI"],
        "ui_visible": False,  # GM専用
        "heart": {"axis": "green", "value": 100},
        "id_aliases": ["カード生成イベント"],
    },
    "switch_character": {
        "label": "キャラ切替",
        "description": "操作キャラクターを切り替える",
        "function": switch_character_action,
        "args_template": ["<target_name>"],
        "requirements": ["has_rc_in_party"],
        "available_to": ["player", "npc"],
        "ui_visible": True,
        "heart": {"axis": "green", "value": 255},
        "id_aliases": [],
    },
    "set_emotion": {
        "label": "感情を設定する",
        "description": "RGB値でプレイヤーの心の色を設定する",
        "function": set_emotion_color_action,
        "args_template": [],
        "requirements": None,
        "available_to": ["player", "npc"],
        "ui_visible": True,
        "heart": {"axis": "green", "value": 150},
        "id_aliases": ["感情を設定する"],
    },
    "talk": {
        "label": "話す",
        "description": "ターゲットに話しかける（状況・関係性ベースのフレーバーテキスト）",
        "function": talk,
        "args_template": ["<target_name>"],
        "requirements": {"has_target": True},
        "available_to": ["player", "npc"],
        "ui_visible": True,
        "heart": {"axis": "blue", "value": 120},
        "id_aliases": [],
    },
}


# NOTE: Director自動実行用アクション（UIには表示しない）
ACTIONS: Dict[str, Dict[str, Any]] = {
    "limit_drink": {
        "label": "酒量を抑える",
        "time_min": 10,
        "emotion_delta": {"R": -10, "G": +7, "B": 0},
        "effects": [
            {"op": "add", "path": "sobriety_days", "value": 1},
            {"op": "add", "path": "entropy.value", "value": -1, "min": 0},
        ],
        "ui_visible": False,
        "heart": {"axis": "green", "value": 100},
    },
    "check_tip": {
        "label": "未読の通報を1件だけ確認",
        "time_min": 5,
        "emotion_delta": {"R": -2, "G": +5, "B": +2},
        "effects": [{"op": "add", "path": "tips_checked", "value": 1}],
        "ui_visible": False,
        "heart": {"axis": "green", "value": 80},
    },
    "log_victim": {
        "label": "被害者の名前をノートに1人追記",
        "time_min": 3,
        "emotion_delta": {"R": 0, "G": +3, "B": +5},
        "ui_visible": False,
        "heart": {"axis": "blue", "value": 100},
    },
    "collect_fiber": {
        "label": "現場で青い繊維を1点採取",
        "time_min": 15,
        "emotion_delta": {"R": +2, "G": +5, "B": +2},
        "effects": [{"op": "add", "path": "evidence_score", "value": 10}],
        "ui_visible": False,
        "heart": {"axis": "green", "value": 120},
    },
    "fix_cam_clock": {
        "label": "監視カメラの時刻ズレを補正",
        "time_min": 12,
        "emotion_delta": {"R": 0, "G": +5, "B": +5},
        "ui_visible": False,
        "heart": {"axis": "green", "value": 100},
    },
    "call_partner": {
        "label": "元相棒に5分だけ電話",
        "time_min": 5,
        "emotion_delta": {"R": -2, "G": 0, "B": +7},
        "effects": [{"op": "add", "path": "partner_calls", "value": 1}],
        "ui_visible": False,
        "heart": {"axis": "blue", "value": 120},
    },
    "move_low_profile": {
        "label": "目立たず移動する",
        "time_min": 8,
        "emotion_delta": {"R": -2, "G": +5, "B": 0},
        "effects": {"op": "add", "path": "suspicion.value", "value": -1, "min": 0},
        "ui_visible": False,
        "heart": {"axis": "green", "value": 80},
    },
    "mark_avoid_shop": {
        "label": "立ち寄り危険な店を避けるタグを付ける",
        "time_min": 4,
        "emotion_delta": {"R": -2, "G": +2, "B": +2},
        "ui_visible": False,
        "heart": {"axis": "green", "value": 60},
    },
    "file_report": {
        "label": "報告書を提出する",
        "time_min": 20,
        "emotion_delta": {"R": -5, "G": +7, "B": +5},
        "ui_visible": False,
        "heart": {"axis": "green", "value": 150},
    },
    "share_meal": {
        "label": "食事を分け合う",
        "time_min": 10,
        "emotion_delta": {"B": +10},
        "effects": [
            {"op": "add", "path": "meals_shared", "value": 1},
            {"op": "add", "path": "respect", "value": 5},
        ],
        "ui_visible": False,
        "heart": {"axis": "blue", "value": 150},
    },
    "admit_fault": {
        "label": "失敗を告白する",
        "time_min": 5,
        "emotion_delta": {"G": +8},
        "effects": [
            {"op": "add", "path": "confessions", "value": 1},
            {"op": "add", "path": "respect", "value": 3},
            {"op": "add", "path": "trace_level", "value": -1, "min": 0},
        ],
        "ui_visible": False,
        "heart": {"axis": "green", "value": 120},
    },
    "do_small_quest": {
        "label": "小さな依頼をこなす",
        "time_min": 15,
        "emotion_delta": {"R": +6, "B": +6},
        "effects": [
            {"op": "add", "path": "shared_tasks_completed", "value": 1},
            {"op": "add", "path": "respect", "value": 7},
        ],
        "ui_visible": False,
        "heart": {"axis": "red", "value": 100},
    },
    "travel_waypoints": {
        "label": "道標を辿って移動",
        "time_min": 12,
        "emotion_delta": {"R": +4},
        "effects": [
            {"op": "add", "path": "distance_from_castle", "value": 1},
            {"op": "add", "path": "trace_level", "value": 1},
        ],
        "ui_visible": False,
        "heart": {"axis": "red", "value": 80},
    },
    "shake_tail": {
        "label": "追手を撒く",
        "time_min": 8,
        "emotion_delta": {"G": +4},
        "effects": [
            {"op": "add", "path": "trace_level", "value": -2, "min": 0},
            {"op": "add", "path": "respect", "value": 1},
        ],
        "ui_visible": False,
        "heart": {"axis": "green", "value": 80},
    },
}

_ACTION_SPECS_CACHE: Dict[str, Dict[str, ActionSpec]] = {}
_LATEST_PACK_KEY = "none"


def _pack_key(pack: Optional[Dict[str, Any]]) -> str:
    if not isinstance(pack, dict):
        return "none"
    return str(pack.get("id") or pack.get("title") or "pack")


def _iter_pack_actions(pack: Optional[Dict[str, Any]]) -> Iterable[tuple[str, Dict[str, Any]]]:
    if not isinstance(pack, dict):
        return []
    actions_data = pack.get("actions") or pack.get("action_specs")
    if isinstance(actions_data, dict):
        return list(actions_data.items())
    if isinstance(actions_data, list):
        pairs = []
        for item in actions_data:
            if isinstance(item, dict) and item.get("id"):
                pairs.append((item["id"], item))
        return pairs
    return []


def _spec_from_new(action_id: str, data: Dict[str, Any]) -> ActionSpec:
    # heartが未設定の場合はデフォルト値を使用して警告
    heart = data.get("heart")
    if heart is None:
        heart = {"axis": "green", "value": 50}
        print(f"[WARN] action '{action_id}' has no heart, using default")
    return ActionSpec(
        id=action_id,
        label=str(data.get("label") or action_id),
        description=data.get("description"),
        time_min=int(data.get("time_min") or 0),
        emotion_delta=data.get("emotion_delta"),
        tags=data.get("tags"),
        requirements=data.get("requirements"),
        args_template=data.get("args_template"),
        available_to=data.get("available_to") or ["player", "npc"],
        effects=data.get("effects"),
        function=data.get("function"),
        id_aliases=list(data.get("id_aliases") or []),
        ui_visible=data.get("ui_visible", True),
        heart=heart,
    )


def _spec_from_legacy(action_id: str, data: Dict[str, Any]) -> ActionSpec:
    # heartが未設定の場合はデフォルト値を使用して警告
    heart = data.get("heart")
    if heart is None:
        heart = {"axis": "green", "value": 50}
        print(f"[WARN] action '{action_id}' has no heart, using default")
    return ActionSpec(
        id=action_id,
        label=str(data.get("label") or action_id),
        description=data.get("description"),
        time_min=int(data.get("time_min") or 0),
        emotion_delta=data.get("emotion_delta"),
        tags=data.get("tags"),
        requirements=data.get("requirements"),
        args_template=data.get("args_template") or [],
        available_to=data.get("available_to"),
        effects=data.get("effects"),
        function=data.get("function"),
        id_aliases=list(data.get("id_aliases") or []),
        ui_visible=data.get("ui_visible", True),
        heart=heart,
    )


def get_action_specs(pack: Dict[str, Any] | None = None) -> Dict[str, ActionSpec]:
    global _LATEST_PACK_KEY
    pack_key = _pack_key(pack)
    _LATEST_PACK_KEY = pack_key
    if pack_key in _ACTION_SPECS_CACHE:
        return _ACTION_SPECS_CACHE[pack_key]

    specs: Dict[str, ActionSpec] = {}
    legacy_count = 0
    pack_count = 0
    for action_id, data in actions.items():
        if isinstance(data, dict):
            specs[action_id] = _spec_from_legacy(action_id, data)
            legacy_count += 1
    for action_id, data in ACTIONS.items():
        if isinstance(data, dict):
            specs[action_id] = _spec_from_new(action_id, data)
    for action_id, data in _iter_pack_actions(pack):
        if isinstance(data, dict):
            specs[action_id] = _spec_from_new(action_id, data)
            pack_count += 1

    _ACTION_SPECS_CACHE[pack_key] = specs
    pack_name = pack_key if pack_key != "none" else "none"
    print(f"[ACTIONS] loaded specs={len(specs)} legacy={legacy_count} pack={pack_name}")
    return specs


def get_action_spec(action_id: str) -> ActionSpec | None:
    if not action_id:
        return None
    specs = _ACTION_SPECS_CACHE.get(_LATEST_PACK_KEY) or get_action_specs()
    spec = specs.get(action_id)
    if spec:
        return spec
    for candidate in specs.values():
        if action_id in (candidate.id_aliases or []):
            return candidate
    return None


def get_action_def(action_id: str) -> Dict[str, Any]:
    spec = get_action_spec(action_id)
    return spec.to_dict() if spec else {}
