# scripts/preference_cli.py
from __future__ import annotations
from pathlib import Path
import argparse, yaml, uuid, glob
from datetime import datetime

def _resolve_job_root(p_like: str) -> Path:
    # グロブ→単一パスへ
    matches = sorted(glob.glob(p_like))
    if not matches:
        raise SystemExit(f"no match: {p_like}")
    if len(matches) > 1:
        raise SystemExit(f"ambiguous path (use a more specific glob): {p_like} -> {matches}")
    p = Path(matches[0]).resolve()
    if (p / "scene_graph.yml").exists():
        return p
    # ラベル直下が渡された場合（子に1つだけ job があるなら自動解決）
    sub = [d for d in p.iterdir() if d.is_dir() and (d / "scene_graph.yml").exists()]
    if len(sub) == 1:
        return sub[0]
    raise SystemExit(f"could not resolve a job root under: {p}")

def save_preference(job_root_a: Path, job_root_b: Path, winner: str, note: str, out_dir: Path):
    pair = {
        "pair_id": str(uuid.uuid4()),
        "ts": datetime.now().isoformat(timespec="seconds"),
        "a": {"root": str(job_root_a), "scene": "scene_graph.yml"},
        "b": {"root": str(job_root_b), "scene": "scene_graph.yml"},
        "winner": winner.lower(),  # "a" | "b" | "tie"
        "note": note,
    }
    out_dir.mkdir(parents=True, exist_ok=True)
    out = out_dir / f"preference_{pair['pair_id']}.yml"
    out.write_text(yaml.safe_dump(pair, allow_unicode=True, sort_keys=False), encoding="utf-8")
    print("saved:", out)

def main(argv=None):
    ap = argparse.ArgumentParser(description="Save A/B preference to jobs/prefs")
    ap.add_argument("a", help="path or glob to snapshot A job dir (must contain scene_graph.yml)")
    ap.add_argument("b", help="path or glob to snapshot B job dir")
    ap.add_argument("winner", choices=["a","b","tie","A","B","TIE"])
    ap.add_argument("note", nargs="*", default=[], help="free text comment")
    ap.add_argument("--out", default="jobs/prefs", help="output dir (default: jobs/prefs)")
    args = ap.parse_args(argv)

    job_root_a = _resolve_job_root(args.a)
    job_root_b = _resolve_job_root(args.b)
    note = " ".join(args.note)

    save_preference(job_root_a, job_root_b, args.winner, note, Path(args.out))

if __name__ == "__main__":
    main()
# ラベル直下を渡す（A/B それぞれ1件だけ含まれている場合）
# python scripts/preference_cli.py jobs/snapshots/A jobs/snapshots/B b "構図Bの方が良い"

# もしくは個別のケースディレクトリを明示
# python scripts/preference_cli.py \
#  "jobs/snapshots/A/p2_04_*" \
#  "jobs/snapshots/B/p2_06_*" \
#  b "構図Bの方が良い"
