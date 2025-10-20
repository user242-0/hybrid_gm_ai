from pathlib import Path
import yaml, uuid
from datetime import datetime

def save_preference(job_root_a: Path, job_root_b: Path, winner: str, note: str = ""):
    pair = {
        "pair_id": str(uuid.uuid4()),
        "ts": datetime.now().isoformat(timespec="seconds"),
        "a": {"root": str(job_root_a), "scene": "scene_graph.yml"},
        "b": {"root": str(job_root_b), "scene": "scene_graph.yml"},
        "winner": winner,  # "a" or "b" or "tie"
        "note": note,
    }
    out_dir = Path(job_root_a).parent / "prefs"
    out_dir.mkdir(parents=True, exist_ok=True)
    out = out_dir / f"preference_{pair['pair_id']}.yml"
    out.write_text(yaml.safe_dump(pair, allow_unicode=True, sort_keys=False), encoding="utf-8")
    print("saved:", out)

if __name__ == "__main__":
    import sys
    # 使い方: python scripts/preference_cli.py jobs/20251020_A jobs/20251020_B a "構図Aの方が良い"
    save_preference(Path(sys.argv[1]), Path(sys.argv[2]), sys.argv[3], " ".join(sys.argv[4:]))
