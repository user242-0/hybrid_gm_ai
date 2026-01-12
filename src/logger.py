# logger.py
import json, datetime, os
from pathlib import Path
from src.character_status import CharacterStatus

LOG_DIR = Path("data/logs")
LOG_DIR.mkdir(parents=True, exist_ok=True)
LOG_PATH_FULL = LOG_DIR / "gameplay_log_latest.jsonl"   # full ログ（全source）
LOG_PATH_PLAYER = LOG_DIR / "gameplay_player_latest.jsonl"   # player ログ（GUI/HUD/CLIのみ）

def _encode(obj):
    if isinstance(obj, CharacterStatus):
        return {"name": obj.name, "hp": obj.hp, "is_npc": obj.is_npc}
    raise TypeError(f"{type(obj)} is not JSON serializable")

def log_action(**fields):
    """
    timestamp, actor, action, target, location, result, ... を kwargs で受け取る想定。
    追加フィールドがあってもそのまま書き出す。
    
    ログは2系統に分離：
    - full ログ (gameplay_log_latest.jsonl): 全sourceを出力
    - player ログ (gameplay_player_latest.jsonl): source が "GUI", "HUD", "CLI" のみ
      ただし、action_id=="switch_character" かつ source=="RC_AI" の行は player 側には出さない
    """
    fields["ts"] = datetime.datetime.now().isoformat(timespec="seconds")
    json_line = json.dumps(fields, ensure_ascii=False, default=_encode) + "\n"
    
    # full ログには常に書き込む
    with LOG_PATH_FULL.open("a", encoding="utf-8") as f:
        f.write(json_line)
        f.flush()
    
    # player ログへの書き込み判定
    source = fields.get("source", "")
    action_id = fields.get("action_id", "")
    
    # player ログに書き込む条件：
    # 1. source が "GUI", "HUD", "CLI" のいずれか
    # 2. かつ、action_id=="switch_character" かつ source=="RC_AI" ではない
    is_player_source = source in ("GUI", "HUD", "CLI")
    is_excluded = (action_id == "switch_character" and source == "RC_AI")
    
    if is_player_source and not is_excluded:
        with LOG_PATH_PLAYER.open("a", encoding="utf-8") as f:
            f.write(json_line)
            f.flush()
