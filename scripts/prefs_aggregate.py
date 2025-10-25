# scripts/prefs_aggregate.py
from __future__ import annotations
from pathlib import Path
import yaml, glob, collections

def _load_sg(job_root: Path) -> dict:
    try: return yaml.safe_load((job_root/"scene_graph.yml").read_text(encoding="utf-8")) or {}
    except Exception: return {}

def _key_from_sg(sg: dict) -> str:
    meta = sg.get("meta",{}) or {}
    tpo  = meta.get("tpo_ctx",{}) or {}
    # 代表キー： action/location/time
    action = (sg.get("objects") or [{}])[0].get("action","")
    return f"{action}|{tpo.get('location','')}" + f"|{tpo.get('time','')}"

def main():
    prefs = list(Path("jobs/prefs").glob("preference_*.yml"))
    if not prefs: return print("no prefs")
    score = collections.Counter()
    for p in prefs:
        y = yaml.safe_load(p.read_text(encoding="utf-8")) or {}
        a = Path(y["a"]["root"]); b = Path(y["b"]["root"]); w = (y.get("winner") or "tie").lower()
        kA = _key_from_sg(_load_sg(a)); kB = _key_from_sg(_load_sg(b))
        if w=="a": score[kA]+=1; score[kB]-=1
        elif w=="b": score[kB]+=1; score[kA]-=1
    # 提案：priority に落とす
    out = {"suggest_priority": [{"selector": k, "priority": max(1,min(3,v))} for k,v in score.most_common() if v>0]}
    Path("jobs/prefs/priority_suggestions.yaml").write_text(yaml.safe_dump(out, allow_unicode=True, sort_keys=False), encoding="utf-8")
    print("wrote: jobs/prefs/priority_suggestions.yaml")

if __name__=="__main__":
    main()
