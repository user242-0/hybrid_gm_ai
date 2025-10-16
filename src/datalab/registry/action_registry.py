# src/datalab/registry/action_registry.py
SWING_KEYS  = {"swing_sword", "攻撃する", "剣を振るう"}
CROUCH_KEYS = {"crouch_ready", "中腰で構える", "ready"}

def normalize_action(key: str, args: list[str]) -> str | None:
    k = (key or "").strip()
    if k in SWING_KEYS:
        return "swing_sword"
    if k in CROUCH_KEYS:
        return "crouch_ready"
    # 英語系の古いログにも一応対応
    if k == "attack" and args and args[0] in {"slash", "swing"}:
        return "swing_sword"
    return None
