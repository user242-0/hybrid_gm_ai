"""戦闘ログ辞書 — CSV から戦闘描写テキストを読み込み、条件で引き当てる。"""

import csv
import glob
import os
import random

_cache: list[dict] | None = None

_DATA_DIR = os.path.join(os.path.dirname(__file__), os.pardir, os.pardir, "data", "combat")


def _load_all() -> list[dict]:
    """data/combat/*.csv を全部読み、行 dict のリストを返す。"""
    global _cache
    if _cache is not None:
        return _cache

    rows: list[dict] = []
    pattern = os.path.join(os.path.normpath(_DATA_DIR), "*.csv")
    for path in glob.glob(pattern):
        with open(path, encoding="utf-8-sig", newline="") as f:
            reader = csv.DictReader(f)
            for row in reader:
                # 空行スキップ
                if not row.get("text", "").strip():
                    continue
                # tags 列: カンマ区切りでリスト化（空なら空リスト）
                raw_tags = row.get("tags", "").strip()
                row["tags"] = [t.strip() for t in raw_tags.split(",") if t.strip()] if raw_tags else []
                # 各フィールドを strip
                for key in ("range", "attacker_weapon", "outcome", "subtype",
                            "attacker_role", "defender_role", "text"):
                    if key in row:
                        row[key] = row[key].strip()
                rows.append(row)

    _cache = rows
    return _cache


def _match(rows: list[dict], *, range_: str, attacker_weapon: str,
           outcome: str, subtype: str | None,
           attacker_role: str | None, defender_role: str | None) -> list[dict]:
    """条件に合致する行を返す。"""
    result = []
    for r in rows:
        if r["range"] != range_:
            continue
        if r["attacker_weapon"] != attacker_weapon:
            continue
        if r["outcome"] != outcome:
            continue
        if subtype is not None and r.get("subtype", "") != subtype:
            continue
        if attacker_role is not None and r.get("attacker_role", "") not in (attacker_role, "any"):
            continue
        if defender_role is not None and r.get("defender_role", "") not in (defender_role, "any"):
            continue
        result.append(r)
    return result


def pick_combat_log(
    range_: str,
    attacker_weapon: str,
    outcome: str,
    subtype: str = "",
    attacker_role: str = "",
    defender_role: str = "",
    tags: list[str] | None = None,
) -> dict | None:
    """フォールバック付きマッチで戦闘描写テキストを1行選ぶ。

    フォールバック戦略（段階的緩和）:
      1. 完全一致 (range, weapon, outcome, subtype, attacker_role, defender_role)
      2. attacker_role / defender_role を緩和 (any)
      3. subtype を無視
      4. subtype 無視 + role 緩和
    range / weapon / outcome は常に必須（緩和しない）。
    マッチからランダム 1 行選び dict を返す。0 件なら None。
    """
    rows = _load_all()

    # Step 1: 完全一致
    hits = _match(rows, range_=range_, attacker_weapon=attacker_weapon,
                  outcome=outcome, subtype=subtype,
                  attacker_role=attacker_role, defender_role=defender_role)
    if hits:
        return random.choice(hits)

    # Step 2: role を緩和
    hits = _match(rows, range_=range_, attacker_weapon=attacker_weapon,
                  outcome=outcome, subtype=subtype,
                  attacker_role=None, defender_role=None)
    if hits:
        return random.choice(hits)

    # Step 3: subtype を無視
    hits = _match(rows, range_=range_, attacker_weapon=attacker_weapon,
                  outcome=outcome, subtype=None,
                  attacker_role=attacker_role, defender_role=defender_role)
    if hits:
        return random.choice(hits)

    # Step 4: subtype 無視 + role 緩和
    hits = _match(rows, range_=range_, attacker_weapon=attacker_weapon,
                  outcome=outcome, subtype=None,
                  attacker_role=None, defender_role=None)
    if hits:
        return random.choice(hits)

    return None
