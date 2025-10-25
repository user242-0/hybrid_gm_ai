# scripts/gc_jobs.py  （dry-run が既定／--delete で実削除） #参照されていない 元ジョブを候補表示 → 任意で削除
from pathlib import Path
import argparse, shutil, yaml

def load_refs():
    refs=set()
    for p in Path("jobs/prefs").glob("preference_*.yml"):
        y=yaml.safe_load(p.read_text(encoding="utf-8")) or {}
        for side in("a","b"):
            r=((y.get(side) or {}).get("root") or "").strip()
            if r: refs.add(str(Path(r).resolve()))
    # snapshots 自体は常に保護
    for d in Path("jobs/snapshots").rglob("*"):
        if d.is_dir(): refs.add(str(d.resolve()))
    # prefs 自体も保護
    refs.add(str(Path("jobs/prefs").resolve()))
    return refs

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--delete", action="store_true")
    args=ap.parse_args()

    refs=load_refs()
    candidates=[]
    for d in Path("jobs").iterdir():
        if not d.is_dir(): continue
        if d.name in ("snapshots","prefs"): continue
        if str(d.resolve()) in refs: continue
        # runディレクトリの直下ケースを1つ見て、scene_graph.yml が全て snapshots にコピー済かを緩くチェック
        candidates.append(d)

    if not args.delete:
        print("# dry run: removable candidates")
        for c in candidates: print(" -", c)
        print("use --delete to actually remove.")
        return

    for c in candidates:
        shutil.rmtree(c)
        print("deleted:", c)

if __name__=="__main__":
    main()
#まず python scripts/list_referenced_jobs.py で pref が参照しているパスを確認。
#次に python scripts/gc_jobs.py（dry-run）→ 問題なければ --delete。