# scripts/ab_pipeline.py
from __future__ import annotations
import argparse, subprocess, sys
from pathlib import Path
from datetime import datetime

def run(cmd: list[str]):
    print(">", " ".join(cmd))
    subprocess.run(cmd, check=True)

def strftime(s: str) -> str:
    try: return datetime.now().strftime(s)
    except Exception: return s

def _case_job_glob(case_glob: str) -> str:
    # "data/eval_set/cases/p2_01_*.yml" -> "p2_01_*"
    name = Path(case_glob).name
    return name[:-4] if name.endswith(".yml") else name

def main():
    ap = argparse.ArgumentParser(description="Run A/B from two case globs → snapshot → prompt → render.")
    ap.add_argument("--case-a", required=True, help='e.g., data/eval_set/cases/p2_01_*.yml')
    ap.add_argument("--case-b", required=True, help='e.g., data/eval_set/cases/p2_05_*.yml')
    ap.add_argument("--label-a", default="A")
    ap.add_argument("--label-b", default="B")
    ap.add_argument("--suite-out-a", default="jobs/%Y%m%d_%H%M_ab_A")
    ap.add_argument("--suite-out-b", default="jobs/%Y%m%d_%H%M_ab_B")
    ap.add_argument("--run-id-a",  default=None, help="subdir under label (default: now)")
    ap.add_argument("--run-id-b",  default=None)
    ap.add_argument("--style",     default="realistic")
    ap.add_argument("--model",     default="stabilityai/sdxl-turbo")
    ap.add_argument("--steps",     type=int, default=4)
    ap.add_argument("--guidance",  type=float, default=0.0)
    ap.add_argument("--size",      default="512x512")
    ap.add_argument("--no-render", action="store_true")
    args = ap.parse_args()

    py = sys.executable

    suite_a = strftime(args.suite_out_a)  # run_eval_suite.py は --out をそのまま使う想定（strftime可）
    suite_b = strftime(args.suite_out_b)

    # 1) A/B それぞれ再エミット（ケースごと）
    run([py, "scripts/run_eval_suite.py", "--glob", args.case_a, "--out", suite_a])
    run([py, "scripts/run_eval_suite.py", "--glob", args.case_b, "--out", suite_b])

    # 2) スナップショット（jobs/snapshots/<label>/<run-id>/<case>/…）
    rid_a = args.run_id_a or datetime.now().strftime("%Y%m%d_%H%M%S")
    rid_b = args.run_id_b or datetime.now().strftime("%Y%m%d_%H%M%S")
    jobs_glob_a = str(Path(suite_a) / _case_job_glob(args.case_a))
    jobs_glob_b = str(Path(suite_b) / _case_job_glob(args.case_b))

    run([py, "scripts/snapshot_job.py", "--label", args.label_a, "--jobs", jobs_glob_a, "--run-id", rid_a])
    run([py, "scripts/snapshot_job.py", "--label", args.label_b, "--jobs", jobs_glob_b, "--run-id", rid_b])

    # 3) SG → プロンプト
    snap_a_glob = f"jobs/snapshots/{args.label_a}/{rid_a}/*"
    snap_b_glob = f"jobs/snapshots/{args.label_b}/{rid_b}/*"
    run([py, "scripts/sg_to_prompt.py", "--jobs", snap_a_glob, "--style", args.style])
    run([py, "scripts/sg_to_prompt.py", "--jobs", snap_b_glob, "--style", args.style])

    # 4) レンダ（省略可）
    if not args.no_render:
        run([py, "scripts/render_with_diffusers.py", "--jobs", snap_a_glob,
             "--model", args.model, "--steps", str(args.steps),
             "--guidance", str(args.guidance), "--size", args.size])
        run([py, "scripts/render_with_diffusers.py", "--jobs", snap_b_glob,
             "--model", args.model, "--steps", str(args.steps),
             "--guidance", str(args.guidance), "--size", args.size])

    print("\nNext:")
    print(f"  python scripts/preference_cli.py jobs/snapshots/{args.label_a}/{rid_a} jobs/snapshots/{args.label_b}/{rid_b} <a|b|tie> \"<note>\"")

if __name__ == "__main__":
    main()
