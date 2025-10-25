# scripts/snapshot_job.py  — label/<run-id>/case で保存（FIX: args.from_suite）
from __future__ import annotations
import argparse, csv, glob, shutil
from pathlib import Path
import yaml
from datetime import datetime

KEEP_DEFAULT = [
    "scene_graph.yml","emotion_eval.yml","story.yml","seed_ledger.csv",
    "*.png","*.jpg","*.jpeg","*.webp",
]

def _expand_jobs(job_patterns: list[str]) -> list[Path]:
    out=[]
    for pat in job_patterns:
        for h in glob.glob(pat):
            p=Path(h)
            p = p.parent if p.is_file() else p
            if p.is_dir():
                out.append(p.resolve())
    uniq=sorted({p for p in out})
    if not uniq:
        raise SystemExit(f"no jobs matched: {job_patterns}")
    return uniq

def _expand_from_suite(suite: str, case_globs: list[str] | None) -> list[Path]:
    sp = Path(suite).resolve()
    if not sp.is_dir():
        raise SystemExit(f"--from-suite not a dir: {suite}")
    pats = [str(sp / g) for g in (case_globs or ["*"])]
    return _expand_jobs(pats)

def _ensure_label_dir(root: Path, label: str) -> Path:
    d = root/label
    d.mkdir(parents=True, exist_ok=True)
    return d

def _mk_run_dir(label_dir: Path, run_id: str | None) -> Path:
    rid = run_id or datetime.now().strftime("%Y%m%d_%H%M%S")
    dst = label_dir / rid
    dst.mkdir(parents=True, exist_ok=True)
    (label_dir/"LATEST").write_text(rid, encoding="utf-8")
    return dst

def _copy_filtered(src: Path, dst: Path, only):
    pats = only or KEEP_DEFAULT
    copied=[]
    for pat in pats:
        for f in src.glob(pat):
            if f.is_file():
                shutil.copy2(f, dst/f.name)
                copied.append(f)
    return copied

def _safe_yml(p: Path) -> dict:
    try: return yaml.safe_load(p.read_text(encoding="utf-8")) or {}
    except Exception: return {}

def _append_index(index_csv: Path, *, label: str, run_id: str, src: Path, dst: Path):
    sg=_safe_yml(dst/"scene_graph.yml"); story=_safe_yml(dst/"story.yml"); eva=_safe_yml(dst/"emotion_eval.yml")
    meta=sg.get("meta",{}) if isinstance(sg,dict) else {}; tpo=meta.get("tpo_ctx",{}) if isinstance(meta,dict) else {}
    outputs=sg.get("outputs",{}) if isinstance(sg,dict) else {}; img=(outputs.get("image") or {}) if isinstance(outputs,dict) else {}
    beats=(story.get("beats") or []) if isinstance(story,dict) else []; first=beats[0].get("summary","") if beats and isinstance(beats[0],dict) else ""
    row = {
        "label":label,"run_id":run_id,"src_job":str(src),"dst_dir":str(dst),
        "seed":img.get("seed",""),"commit":meta.get("commit",""),"profile":meta.get("profile",""),
        "why_now":meta.get("why_now",""),"location":tpo.get("location",""),"time":tpo.get("time",""),
        "relation_labels":"|".join(tpo.get("relation_labels",[]) or []),"story_first_beat":first,
        "eval_id":(eva.get("eval_id") if isinstance(eva,dict) else ""), "salience":(eva.get("signals",{}) or {}).get("salience",""),
    }
    new = not index_csv.exists()
    with index_csv.open("a", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(row.keys()))
        if new: w.writeheader()
        w.writerow(row)

def main():
    ap=argparse.ArgumentParser(description="Snapshot jobs into jobs/snapshots/<label>/<run-id>/")
    g=ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--jobs", nargs="+")
    g.add_argument("--from-suite", dest="from_suite")
    ap.add_argument("--cases", nargs="+")
    ap.add_argument("--label", required=True)
    ap.add_argument("--run-id", default=None, help="subdir name (default: now in %Y%m%d_%H%M%S)")
    ap.add_argument("--out", default="jobs/snapshots")
    ap.add_argument("--only", nargs="*", default=None)
    ap.add_argument("--dry-run", action="store_true")
    args=ap.parse_args()

    sources = _expand_jobs(args.jobs) if args.jobs else _expand_from_suite(args.from_suite, args.cases)
    label_dir = _ensure_label_dir(Path(args.out), args.label)
    run_dir   = _mk_run_dir(label_dir, args.run_id)
    index_csv = label_dir / "_index.csv"

    print(f"[snapshot] {len(sources)} job(s) -> {run_dir}  (label root: {label_dir})")
    for src in sources:
        dst = run_dir / src.name
        print(" -", src, "=>", dst)
        if args.dry_run: 
            continue
        # ★ 宛先ディレクトリを必ず作成（これが無くて FileNotFoundError が出ていました）
        dst.mkdir(parents=True, exist_ok=True)
        copied = _copy_filtered(src, dst, args.only)
        if not copied:
            print(f"  ! warn: no files matched in {src.name} (patterns={args.only or 'DEFAULT'})")
        _append_index(index_csv, label=args.label, run_id=run_dir.name, src=src, dst=dst)

if __name__=="__main__":
    main()



# A を jobs/snapshots/A/20251025_205002/… に
#python scripts/snapshot_job.py --label A --jobs "jobs/20251025_205002_p2_suite_rerun/p2_04_*" --run-id "20251025_205002"

# B を jobs/snapshots/B/20251025_205022/… に
#python scripts/snapshot_job.py --label B --jobs "jobs/20251025_205022_p2_suite_rerun/p2_06_*" --run-id "20251025_205022"

# あるいはスイート直下からケース名でまとめて
# python scripts/snapshot_job.py --from-suite "jobs/20251025_143711_p2_suite"  --cases p2_04_* p2_06_* --label AB

