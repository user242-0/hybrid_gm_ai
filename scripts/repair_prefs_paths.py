from pathlib import Path
import yaml, sys

def main(find: str, replace: str):
    prefs = sorted(Path("jobs/prefs").glob("preference_*.yml"))
    if not prefs: 
        print("no prefs"); return
    changed=0
    for p in prefs:
        y = yaml.safe_load(p.read_text(encoding="utf-8")) or {}
        for side in ("a","b"):
            root = y.get(side,{}).get("root","")
            if find in root:
                y[side]["root"] = root.replace(find, replace)
                p.write_text(yaml.safe_dump(y, allow_unicode=True, sort_keys=False), encoding="utf-8")
                changed+=1
                print("patched:", p.name, side)
    print("done; entries changed:", changed)

if __name__=="__main__":
    # 使い方: python scripts/repair_prefs_paths.py 20251025_0012 20251026_0012
    main(sys.argv[1], sys.argv[2])
