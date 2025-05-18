# actions.py のサンプル（整理版）
from src.actions import explore_location, move_forward, rest_with_event, perform_attack, engage_combat, avoid_combat, accept_attack,\
 talk_to_statue, talk_to_statue_with_cooldown, generate_card_and_print, npc_speak_and_log
from src.control_manager import switch_character_action
from src.emotion_manager import set_emotion_color_action

actions = {
    "探索する": {
        "description": "現在のロケーションを探索する。",
        "function": explore_location,
        "args_template": [],
        "requirements": None,
        "available_to": ["player", "npc"]
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
        "args_template": ["target"],
        "requirements": {"has_weapon": True},
        "available_to": ["player", "npc"],
    },
    "戦う": {
        "description": "敵との戦闘に突入する。",
        "function": engage_combat,
        "args_template": [],        
        "requirements": {"has_enemy": True},  # has_weaponを削除
        "available_to": ["player", "npc"]
    },
    "戦わない": {
        "description": "戦闘を避けて逃げる。",
        "function": accept_attack,
        "args_template": [], 
        "requirements": {"has_enemy": True},
        "available_to": ["player"]
    },
    "ただ、受け入れる": {
        "description": "無抵抗で相手の攻撃を受け止める。",
        "function": accept_attack,
        "args_template": [],          
        "requirements": {"has_enemy": True},
        "available_to": ["player"]
    },
    "石像に話す": {
        "description": "古代の石像に語りかけることで何かが起こるかもしれない。",
        "function": talk_to_statue,
        "args_template": [],  
        "requirements": {"location": "祭壇","target": "古代の石像"},
        "available_to": ["player"]
    },
    "石像に話す（クールダウン）": {
        "description": "古代の石像に語りかける。連続での使用にはクールダウンが必要。",
        "function": talk_to_statue_with_cooldown, 
        "args_template": [],         
        "requirements": {"location": "祭壇","target": "古代の石像"},
        "available_to": ["player"],
    },
    "NPCが話す": {
        "description": "NPCが固定セリフを喋る。",
        "function": npc_speak_and_log, 
        "args_template": ["NPC戦士", "greeting"], 
        "requirements": None,
        "available_to": ["npc"]
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
        "function": switch_character_action,       # ← ルート直下に置く
        "args_template": ["<target_name>"],        # ← parse_args() が読むキー名
        "requirements": ["has_rc_in_party"],
        "available_to": ["player", "npc"]
    },
    "感情を設定する": {
        "description": "RGB値でプレイヤーの心の色を設定する",
        "function": set_emotion_color_action,       
        "args_template": [],        
        "requirements": None,
        "available_to": ["player", "npc"]
    }
}

