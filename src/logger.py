# logger.py
import json, datetime, os
from pathlib import Path
from src.character_status import CharacterStatus

LOG_DIR = Path("data/logs")
LOG_DIR.mkdir(parents=True, exist_ok=True)
LOG_PATH = LOG_DIR / "gameplay_log_latest.jsonl"   # 拡張子を .jsonl にするとIDEが扱いやすい

def _encode(obj):
    if isinstance(obj, CharacterStatus):
        return {"name": obj.name, "hp": obj.hp, "is_npc": obj.is_npc}
    raise TypeError(f"{type(obj)} is not JSON serializable")

def log_action(**fields):
    """
    timestamp, actor, action, target, location, result, ... を kwargs で受け取る想定。
    追加フィールドがあってもそのまま書き出す。
    """
    fields["ts"] = datetime.datetime.now().isoformat(timespec="seconds")
    with LOG_PATH.open("a", encoding="utf-8") as f:
        f.write(json.dumps(fields, ensure_ascii=False, default=_encode) + "\n")
        f.flush()
