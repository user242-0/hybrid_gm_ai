# logger.py
import json, datetime, os
from pathlib import Path
from src.character_status import CharacterStatus
from src.utility.config_loader import get_cfg

LOG_DIR = Path("data/logs")
LOG_DIR.mkdir(parents=True, exist_ok=True)
LOG_PATH_FULL = LOG_DIR / "gameplay_log_latest.jsonl"   # full ログ（全source）
LOG_PATH_PLAYER = LOG_DIR / "gameplay_player_latest.jsonl"   # player ログ（GUI/HUD/CLIのみ）

def _encode(obj):
    if isinstance(obj, CharacterStatus):
        return {"name": obj.name, "hp": obj.hp, "is_npc": obj.is_npc}
    raise TypeError(f"{type(obj)} is not JSON serializable")

def _get_logging_config():
    """Get logging configuration from config.yml with safe defaults"""
    try:
        cfg = get_cfg()
        logging_cfg = cfg.get("logging", {})
    except Exception:
        # configが読めない場合は安全側のデフォルト
        logging_cfg = {}
    
    # full_enabled: デフォルトは false（書かない）
    full_enabled = logging_cfg.get("full_enabled", False)
    
    # full_exclude_actions: デフォルトは ["switch_character"]（除外する）
    full_exclude_actions = logging_cfg.get("full_exclude_actions", ["switch_character"])
    if not isinstance(full_exclude_actions, list):
        full_exclude_actions = ["switch_character"]
    
    return {
        "full_enabled": full_enabled,
        "full_exclude_actions": full_exclude_actions,
    }

def log_action(**fields):
    """
    timestamp, actor, action, target, location, result, ... を kwargs で受け取る想定。
    追加フィールドがあってもそのまま書き出す。
    
    ログは2系統に分離：
    - full ログ (gameplay_log_latest.jsonl): config.logging.full_enabled=true のときのみ全sourceを出力
      ただし、config.logging.full_exclude_actions に含まれる action_id は除外可能（default: switch_character）
    - player ログ (gameplay_player_latest.jsonl): 常に出力、source が "GUI", "HUD", "CLI" のみ
      ただし、action_id=="switch_character" かつ source=="RC_AI" の行は player 側には出さない
    """
    fields["ts"] = datetime.datetime.now().isoformat(timespec="seconds")
    json_line = json.dumps(fields, ensure_ascii=False, default=_encode) + "\n"
    
    source = fields.get("source", "")
    action_id = fields.get("action_id", "")
    
    # full ログへの書き込み判定
    logging_cfg = _get_logging_config()
    if logging_cfg["full_enabled"]:
        # full_exclude_actions に含まれる action_id は除外
        if action_id not in logging_cfg["full_exclude_actions"]:
            with LOG_PATH_FULL.open("a", encoding="utf-8") as f:
                f.write(json_line)
                f.flush()
    
    # player ログへの書き込み判定（常に判定、既存の挙動を維持）
    # player ログに書き込む条件：
    # 1. source が "GUI", "HUD", "CLI" のいずれか
    # 2. かつ、action_id=="switch_character" かつ source=="RC_AI" ではない
    is_player_source = source in ("GUI", "HUD", "CLI")
    is_excluded = (action_id == "switch_character" and source == "RC_AI")
    
    if is_player_source and not is_excluded:
        with LOG_PATH_PLAYER.open("a", encoding="utf-8") as f:
            f.write(json_line)
            f.flush()
