from pathlib import Path
import yaml

POLICY_PATH = Path("src/datalab/registry/scene_policy.yaml")


def _eq_or_in(rule_v, x):
    if isinstance(rule_v, (list, tuple, set)):
        return x in rule_v
    return x == rule_v

def _score_and_hit(cond, ctx):
    score, hit = 0, True
    for k, v in (cond or {}).items():
        if k == "action":
            ok = (_eq_or_in(v, ctx.get("action")) or _eq_or_in(v, ctx.get("raw_key")))
        elif k == "location":
            ok = _eq_or_in(v, ctx.get("location"))
        elif k == "time":
            ok = _eq_or_in(v, ctx.get("time"))
        elif k == "relation_label":
            ok = v in ctx.get("relation_labels", set())
        elif k == "emotion.red_min":
            ok = ctx["emotion"]["red"] >= float(v)
        elif k == "emotion.blue_max":
            ok = ctx["emotion"]["blue"] <= float(v)
        else:
            ok = True
        if not ok: hit = False
        else: score += 1
    return score, hit

def resolve(ctx, policy_path=Path("src/datalab/registry/scene_policy.yaml")):
    y = yaml.safe_load(policy_path.read_text(encoding="utf-8")) or {}
    defaults = y.get("defaults", {})
    best, best_score = None, -1
    for rule in y.get("rules", []):
        s, ok = _score_and_hit(rule.get("when", {}), ctx)
        if ok:
            s += int(rule.get("priority", 0))   # ← 勝ちやすいルールに傾斜
            if s > best_score:
    out = {**defaults}
    if best:
        out.update({k: v for k, v in best.items() if k != "when"})
    return out
