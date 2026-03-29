"""Affordance Bridge: GUI結果 → 中間状態 → HUD候補/ラベル変化の汎用ブリッジ。

Pack YAML の affordances セクション (discovery_rules / label_rules) を読み取り、
アクション実行後に新しい HUD 候補を生成したり、ラベルを文脈に応じて差し替える。
"""

from __future__ import annotations

import random
from typing import Any


def _match_trigger(
    trigger: dict, action_id: str, game_state: dict, world: dict, mode: str | None
) -> bool:
    """trigger 辞書の全キーが現在の状態と一致するか判定。"""
    if trigger.get("action") and trigger["action"] != action_id:
        return False
    if "location" in trigger:
        if trigger["location"] != game_state.get("current_location"):
            return False
    if "mode" in trigger:
        if trigger["mode"] != mode:
            return False
    if "has_flag" in trigger:
        flags = world.get("flags", {})
        if not flags.get(trigger["has_flag"]):
            return False
    return True


def _match_label_rule(
    match: dict, action_id: str, game_state: dict, mode: str | None
) -> bool:
    """label_rules の match 辞書が現在の状態と一致するか判定。"""
    if match.get("action") and match["action"] != action_id:
        return False
    if "mode" in match:
        if match["mode"] != mode:
            return False
    if "location" in match:
        if match["location"] != game_state.get("current_location"):
            return False
    return True


def evaluate_discoveries(
    world: dict, game_state: dict, action_id: str,
    rules: list[dict], rng: random.Random,
    mode: str | None = None,
) -> list[dict]:
    """action実行後に呼ぶ。trigger条件マッチ→discoveries追加。追加分を返す。"""
    aff = world.setdefault("affordances", {"discoveries": [], "spent": set()})
    discoveries = aff.setdefault("discoveries", [])
    spent = aff.setdefault("spent", set())
    existing_ids = {d["id"] for d in discoveries} | spent
    added: list[dict] = []

    for rule in rules:
        trigger = rule.get("trigger", {})
        if not _match_trigger(trigger, action_id, game_state, world, mode):
            continue
        publish = rule.get("publish", {})
        disc_id = publish.get("id")
        if not disc_id or disc_id in existing_ids:
            continue
        chance = rule.get("chance", 1.0)
        if rng.random() > chance:
            continue
        entry = {
            "id": disc_id,
            "action": publish.get("action", disc_id),
            "label": publish.get("label", disc_id),
            "time_min": publish.get("time_min", 5),
        }
        discoveries.append(entry)
        existing_ids.add(disc_id)
        added.append(entry)

    return added


def get_pending_discoveries(world: dict | None) -> list[tuple[str, str, int]]:
    """HUD用。未消費のdiscoveriesを (action_id, label, time_min) で返す。"""
    if not isinstance(world, dict):
        return []
    aff = world.get("affordances")
    if not isinstance(aff, dict):
        return []
    discoveries = aff.get("discoveries", [])
    spent = aff.get("spent", set())
    result: list[tuple[str, str, int]] = []
    for d in discoveries:
        if d.get("id") in spent:
            continue
        result.append((d.get("action", ""), d.get("label", ""), d.get("time_min", 5)))
    return result


def apply_label_overrides(
    actions: list[tuple[str, str, int | None]],
    world: dict, game_state: dict,
    rules: list[dict],
    mode: str | None = None,
) -> list[tuple[str, str, int | None]]:
    """label_rulesに基づきアクションラベルを差し替えた新リストを返す。"""
    result: list[tuple[str, str, int | None]] = []
    for action_id, label, time_min in actions:
        new_label = label
        for rule in rules:
            match = rule.get("match", {})
            if _match_label_rule(match, action_id, game_state, mode):
                new_label = rule.get("label", label)
                break
        result.append((action_id, new_label, time_min))
    return result


def consume_discovery(world: dict | None, action_id: str) -> None:
    """discovery由来アクションを実行したら消費済みにする。"""
    if not isinstance(world, dict):
        return
    aff = world.get("affordances")
    if not isinstance(aff, dict):
        return
    discoveries = aff.get("discoveries", [])
    spent = aff.setdefault("spent", set())
    for d in discoveries:
        if d.get("action") == action_id and d.get("id") not in spent:
            spent.add(d["id"])
            break
