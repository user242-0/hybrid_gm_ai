# scripts/snapshot_job.py
from pathlib import Path
import shutil, sys
from utility.config_loader import job_root_from_cfg

def main(tag: str):
    src = job_root_from_cfg()
    dst = src.parent / tag
    if dst.exists():
        print("exists:", dst); return
    shutil.copytree(src, dst)
    print("copied:", src, "->", dst)

if __name__ == "__main__":
    main(sys.argv[1])  # 例: python scripts/old_snapshot_job.py 20251020_A
