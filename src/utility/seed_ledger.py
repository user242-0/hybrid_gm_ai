# src/utility/seed_ledger.py
from pathlib import Path
from datetime import datetime
import csv

LEDGER_FILENAME = "seed_ledger.csv"
LEDGER_HEADER = ["ts", "scene_file", "seed", "commit_hash", "profile", "actor", "action", "args"]

def append_seed_ledger(job_root: Path, *, scene_file: Path, seed: int,
                       commit_hash: str, profile: str, actor: str, action: str, args: list[str]):
    job_root.mkdir(parents=True, exist_ok=True)
    ledger = job_root / LEDGER_FILENAME
    new_file = not ledger.exists()
    with ledger.open("a", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        if new_file:
            w.writerow(LEDGER_HEADER)
        w.writerow([
            datetime.now().isoformat(timespec="seconds"),
            str(scene_file.relative_to(job_root)) if scene_file.is_absolute() else str(scene_file),
            seed, commit_hash, profile, actor, action, " ".join(args or [])
        ])
