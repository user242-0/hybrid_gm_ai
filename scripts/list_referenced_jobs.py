# scripts/list_referenced_jobs.py #参照されているジョブを一覧する（消す前の点検）
from pathlib import Path
import yaml

def all_pref_paths():
    prefs = list(Path("jobs/prefs").glob("preference_*.yml"))
    roots = set()
    for p in prefs:
        y = yaml.safe_load(p.read_text(encoding="utf-8")) or {}
        for side in ("a","b"):
            r = ((y.get(side) or {}).get("root") or "").strip()
            if r: roots.add(str(Path(r).resolve()))
    return roots

def main():
    refs = all_pref_paths()
    print("# referenced roots in prefs:")
    for r in sorted(refs):
        print(" -", r)
    # 旧スタイル（jobs直下の A_... / B_...）も検出
    print("\n# legacy snapshot dirs that exist but not referenced:")
    for d in Path("jobs").glob("[AB]_*"):
        if d.is_dir() and str(d.resolve()) not in refs:
            print(" -", d)

if __name__=="__main__":
    main()
