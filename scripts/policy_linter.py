# scripts/policy_linter.py
from __future__ import annotations
from pathlib import Path
import sys, yaml

from src.datalab.registry.action_registry import normalize_action
from src.action_definitions import actions
from src.choice_definitions import choice_definitions

DEFAULT_POLICY = Path("src/datalab/registry/scene_policy.yaml")
ALLOWED_WHEN_KEYS = {
    "action", "location", "time", "relation_label",
    "emotion.red_min", "emotion.blue_max"
}

# 追加：正規化済みキー集合を用意
NORM_ACTION_KEYS  = { normalize_action(k) for k in actions.keys() }
NORM_CHOICE_KEYS  = { normalize_action(k) for k in choice_definitions.keys() }

def _known_action_canon(canon: str) -> bool:
    return (canon in NORM_ACTION_KEYS) or (canon in NORM_CHOICE_KEYS)


def _iter_actions_from_when(when):
    if not when:
        return
    a = when.get("action")
    if a is None:
        return
    if isinstance(a, (list, tuple, set)):
        for x in a: yield str(x)
    else:
        yield str(a)

def main(argv=None):
    policy_path = Path(sys.argv[1]) if (len(sys.argv) > 1 and sys.argv[1].endswith(".yaml")) else DEFAULT_POLICY
    if not policy_path.exists():
        raise SystemExit(f"policy not found: {policy_path}")

    y = yaml.safe_load(policy_path.read_text(encoding="utf-8")) or {}
    rules = y.get("rules", [])

    unknown_actions = []
    bad_when_keys = []

    for i, rule in enumerate(rules, 1):
        when = rule.get("when") or {}
        # 1) when の未知キー警告
        for k in when.keys():
            if k not in ALLOWED_WHEN_KEYS:
                bad_when_keys.append((i, k))

        # 2) action の正規化→存在チェック
        for raw in _iter_actions_from_when(when):
            canon = normalize_action(raw)
            exists = _known_action_canon(canon)
            if not exists:
                unknown_actions.append((i, raw, canon))

    if bad_when_keys or unknown_actions:
        print("NG: policy lints failed")
        if bad_when_keys:
            print(" - unknown 'when' keys:")
            for i, k in bad_when_keys:
                print(f"    rule#{i}: '{k}'")
        if unknown_actions:
            print(" - unknown/typo actions:")
            for i, raw, canon in unknown_actions:
                print(f"    rule#{i}: '{raw}' -> '{canon}' (not found)")
        raise SystemExit(1)

    print("OK: scene_policy lints passed")

if __name__ == "__main__":
    main()
