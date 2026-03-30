"""Affordance Bridge v2: discovery / opportunity / label の3層ブリッジ。

Pack YAML の affordances セクション (discovery_rules / opportunity_rules / label_rules)
を読み取り:
  1. action 実行後に discovery_rules を評価し、discovery を記録する
  2. HUD 更新時に opportunity_rules を評価し、可視 opportunity を返す
  3. label_rules でラベル差し替えを行う
  4. Director 既定候補と affordance 候補の action_id 重複を統合する

Discovery は記録されたら残り続ける。
Spent 管理は opportunity 側で行う（action_id ベース）。
"""

from __future__ import annotations

from typing import Any


# ------------------------------------------------------------------
# Internal helpers
# ------------------------------------------------------------------

def _check_facts(world: dict, required_facts: list[str]) -> bool:
    """requires_facts の全キーが world["flags"] に truthy で存在するか。"""
    flags = world.get("flags", {})
    for fact in required_facts:
        if not flags.get(fact):
            return False
    return True


# ------------------------------------------------------------------
# Discovery layer
# ------------------------------------------------------------------

def evaluate_discoveries(
    world: dict,
    game_state: dict,
    action_id: str,
    rules: list[dict],
    mode: str | None = None,
) -> list[str]:
    """action 実行後に呼ぶ。discovery_rules を評価し、新規 discovery を記録。

    trigger_type ごとの挙動:
      - action_result: last_action_id (= 引数 action_id) が trigger_action と一致
      - passive_or_time: requires_facts が満たされていれば自動発火
      - director_inject: ここでは発火しない。inject_discovery() で外部注入

    Returns: 新たに追加された discovery ID のリスト。
    """
    aff = world.setdefault("affordances", {"discoveries": [], "spent_opportunities": set()})
    discoveries: list[str] = aff.setdefault("discoveries", [])
    aff.setdefault("spent_opportunities", set())
    existing = set(discoveries)
    added: list[str] = []

    for rule in rules:
        disc_id = rule.get("creates_discovery")
        if not disc_id or disc_id in existing:
            continue

        # requires_facts チェック
        required_facts = rule.get("requires_facts", [])
        if required_facts and not _check_facts(world, required_facts):
            continue

        trigger_type = rule.get("trigger_type", "action_result")

        if trigger_type == "action_result":
            trigger_action = rule.get("trigger_action")
            if not trigger_action or trigger_action != action_id:
                continue

        elif trigger_type == "director_inject":
            # director_inject は evaluate_discoveries では発火しない。
            # inject_discovery() を使って直接注入する。
            continue

        elif trigger_type == "passive_or_time":
            # canonical facts が存在すれば自動発火
            # （requires_facts チェックは上で済んでいる）
            pass

        else:
            continue

        discoveries.append(disc_id)
        existing.add(disc_id)
        added.append(disc_id)

    return added


def inject_discovery(world: dict, discovery_id: str) -> bool:
    """Director が外部から discovery を注入する（director_inject 用）。

    Returns: 新規追加された場合 True。
    """
    aff = world.setdefault("affordances", {"discoveries": [], "spent_opportunities": set()})
    discoveries: list[str] = aff.setdefault("discoveries", [])
    if discovery_id in discoveries:
        return False
    discoveries.append(discovery_id)
    return True


# ------------------------------------------------------------------
# Opportunity layer
# ------------------------------------------------------------------

def evaluate_opportunities(
    world: dict,
    game_state: dict,
    rules: list[dict],
    mode: str | None = None,
) -> list[dict]:
    """HUD 更新時に呼ぶ。記録済み discovery + visible_when から可視 opportunity を返す。

    visible_when のキー省略 = 制約なし（any）。

    Returns: 可視な opportunity のリスト。各要素は
        {"action_id": str, "label": str,
         "opportunity_kind": str, "location_updates": bool}
    """
    aff = world.get("affordances", {})
    discoveries = set(aff.get("discoveries", []))
    spent = aff.get("spent_opportunities", set())
    current_location = game_state.get("current_location")

    result: list[dict] = []

    for rule in rules:
        action_id = rule.get("action_id")
        if not action_id:
            continue

        # spent チェック
        if action_id in spent:
            continue

        # requires_discoveries チェック
        required = rule.get("requires_discoveries", [])
        if not all(d in discoveries for d in required):
            continue

        # visible_when チェック（キー省略 = 制約なし）
        visible_when = rule.get("visible_when") or {}

        loc_constraint = visible_when.get("current_location")
        if loc_constraint is not None and loc_constraint != current_location:
            continue

        mode_constraint = visible_when.get("director_mode")
        if mode_constraint is not None and mode_constraint != mode:
            continue

        result.append({
            "action_id": action_id,
            "label": rule.get("label", action_id),
            "opportunity_kind": rule.get("opportunity_kind", "standard"),
            "location_updates": bool(rule.get("location_updates", False)),
        })

    return result


def mark_opportunity_spent(world: dict, action_id: str) -> None:
    """opportunity を実行したら spent にする。"""
    aff = world.get("affordances")
    if not isinstance(aff, dict):
        return
    spent: set = aff.setdefault("spent_opportunities", set())
    spent.add(action_id)


# ------------------------------------------------------------------
# Director 候補との統合
# ------------------------------------------------------------------

def merge_with_director_actions(
    director_actions: list[tuple[str, str, int | None]],
    opportunities: list[dict],
    governed_action_ids: set[str] | None = None,
) -> list[tuple[str, str, int | None]]:
    """Director 既定候補と opportunity 候補を action_id ベースで統合。

    governed_action_ids: opportunity_rule が存在する action_id の集合。
    この集合に含まれる action_id は、visible opportunity がない限り
    Director 側の候補からも抑制される。
    governed_action_ids に含まれない action_id は従来通り無条件表示。
    """
    visible_opp_ids = {opp["action_id"] for opp in opportunities}
    governed = governed_action_ids or set()

    # Director actions をフィルタ: governed なら visible opportunity が必要
    merged: list[tuple[str, str, int | None]] = []
    merged_ids: set[str] = set()
    for action in director_actions:
        aid = action[0]
        if aid in governed and aid not in visible_opp_ids:
            continue
        merged.append(action)
        merged_ids.add(aid)

    # Director にない visible opportunity を追加
    for opp in opportunities:
        aid = opp["action_id"]
        if aid not in merged_ids:
            merged.append((aid, opp["label"], None))
            merged_ids.add(aid)

    return merged


# ------------------------------------------------------------------
# Label overrides
# ------------------------------------------------------------------

def apply_label_overrides(
    actions: list[tuple[str, str, int | None]],
    game_state: dict,
    rules: list[dict],
    mode: str | None = None,
) -> list[tuple[str, str, int | None]]:
    """label_rules に基づきアクションラベルを差し替えた新リストを返す。"""
    current_location = game_state.get("current_location")
    result: list[tuple[str, str, int | None]] = []

    for action_id, label, time_min in actions:
        new_label = label
        for rule in rules:
            match = rule.get("match", {})
            if match.get("action") and match["action"] != action_id:
                continue
            if "mode" in match and match["mode"] != mode:
                continue
            if "location" in match and match["location"] != current_location:
                continue
            # label は rule 直下 or match 内部（カスタム YAML パーサ対応）
            new_label = rule.get("label") or match.get("label") or label
            break
        result.append((action_id, new_label, time_min))

    return result
