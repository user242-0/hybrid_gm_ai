"""戦闘交換の解決 — pick_combat_log を呼び、gs に結果を記録する。"""

from datetime import datetime

from src.combat.log_dict import pick_combat_log


def _get_weapon_type(char) -> str:
    """CharacterStatus から weapon_type を取得。無ければ "unarmed"。"""
    wp = getattr(char, "equipped_weapon", None)
    if wp and isinstance(wp, dict):
        return wp.get("weapon_type", "unarmed")
    return "unarmed"


def _get_role(char) -> str:
    """CharacterStatus から簡易ロールを返す。

    将来はパック定義から引くが、当面は:
      faction=="player" → "cop"
      is_npc==True      → "trickster"
      fallback          → "any"
    """
    if getattr(char, "faction", "") == "player":
        return "cop"
    if getattr(char, "is_npc", False):
        return "trickster"
    return "any"


def resolve_exchange(
    gs: dict,
    attacker_id: str,
    defender_id: str,
    range_: str = "near",
    outcome: str = "miss",
    subtype: str = "evade",
) -> dict:
    """仮の戦闘解決器。

    1. attacker/defender の CharacterStatus から weapon, role を取得
    2. pick_combat_log() でテキストを引く
    3. exchange_record を組み立て
    4. gs["combat"]["last_exchange"] / gs["combat"]["log"] に記録
    5. exchange_record を返す
    """
    # gs["combat"] 初期化
    if "combat" not in gs:
        gs["combat"] = {"log": [], "last_exchange": None}
    combat = gs["combat"]
    if "log" not in combat:
        combat["log"] = []

    # キャラ取得
    party = gs.get("party", {})
    attacker = party.get(attacker_id)
    defender = party.get(defender_id)

    attacker_weapon = _get_weapon_type(attacker) if attacker else "unarmed"
    defender_weapon = _get_weapon_type(defender) if defender else "unarmed"
    attacker_role = _get_role(attacker) if attacker else "any"
    defender_role = _get_role(defender) if defender else "any"

    # テキスト引き当て
    log_entry = pick_combat_log(
        range_=range_,
        attacker_weapon=attacker_weapon,
        outcome=outcome,
        subtype=subtype,
        attacker_role=attacker_role,
        defender_role=defender_role,
    )

    text = log_entry["text"] if log_entry else ""
    tags = log_entry["tags"] if log_entry else []

    # exchange record 組み立て
    record = {
        "attacker": attacker_id,
        "defender": defender_id,
        "range": range_,
        "outcome": outcome,
        "subtype": subtype,
        "attacker_weapon": attacker_weapon,
        "defender_weapon": defender_weapon,
        "text": text,
        "tags": tags,
        "ts": datetime.now().isoformat(),
    }

    combat["last_exchange"] = record
    combat["log"].append(record)

    return record
