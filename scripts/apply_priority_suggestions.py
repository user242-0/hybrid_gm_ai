# scripts/apply_priority_suggestions.py  — robust matching (list & normalize)
from pathlib import Path
import yaml
from src.datalab.registry.action_registry import normalize_action  # 正規化
POLICY = Path("src/datalab/registry/scene_policy.yaml")
SUGG   = Path("jobs/prefs/priority_suggestions.yaml")

def _as_list(x):
    if x is None: return []
    return x if isinstance(x, (list, tuple, set)) else [x]

def _action_matches(rule_actions, selector_action) -> bool:
    sel = normalize_action(selector_action)
    for a in _as_list(rule_actions):
        if normalize_action(a) == sel:
            return True
    return False

def main():
    if not POLICY.exists() or not SUGG.exists():
        raise SystemExit("missing policy or suggestions")
    pol = yaml.safe_load(POLICY.read_text(encoding="utf-8")) or {}
    sug = yaml.safe_load(SUGG.read_text(encoding="utf-8")) or {}
    rules = pol.get("rules", [])
    applied = 0
    missed  = []

    for item in (sug.get("suggest_priority") or []):
        action, loc, tim = item["selector"].split("|")
        prio = int(item["priority"])
        hit_any = False
        for r in rules:
            w = r.get("when", {})
            if (w.get("location") == loc and w.get("time") == tim
                and _action_matches(w.get("action"), action)):
                r["priority"] = prio
                hit_any = True
                applied += 1
        if not hit_any:
            missed.append(item)

    POLICY.write_text(yaml.safe_dump(pol, allow_unicode=True, sort_keys=False), encoding="utf-8")
    print(f"applied priority to {applied} rules")
    if missed:
        print("unmatched suggestions (no such rule):")
        for m in missed:
            print(" -", m)

if __name__ == "__main__":
    main()
