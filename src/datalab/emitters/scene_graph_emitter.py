# src/datalab/emitters/scene_graph_emitter.py
from pathlib import Path
from datetime import datetime
import secrets
import yaml
from schemas.scene_graph import SceneGraph, ObjectSpec, Pose

from src.utility.git_info import get_commit_hash
from src.utility.seed_ledger import append_seed_ledger
from src.utility.config_loader import get_cfg  # P0(1)で導入済みの想定


def emit_scene_graph(*, job_root: Path, theme: str, background: str, objects: list,
                     loras: list[str] = None,
                     seed: int | None = None,
                     why_now: str | None = None,
                     profile: str | None = None,
                     actor: str | None = None,
                     action: str | None = None,
                     args: list[str] | None = None,
                     extra_meta: dict | None = None):
    job_root = Path(job_root)
    job_root.mkdir(parents=True, exist_ok=True)

    cfg = get_cfg()
    profile = profile or cfg.get("profile", "prod")
    commit_hash = get_commit_hash()
    seed = seed if seed is not None else secrets.randbits(32)

    doc = {
        "theme": theme,
        "background": background,
        "objects": [o.dict() if hasattr(o, "dict") else o for o in objects],
        "loras": loras or [],
        "outputs": {"image": {"seed": int(seed)}},
        "meta": {
            "commit": commit_hash,
            "profile": profile,
        }
    }
    if why_now:
        doc["meta"]["why_now"] = why_now
    if extra_meta:
        doc["meta"].update(extra_meta)

    out = job_root / "scene_graph.yml"
    out.write_text(yaml.safe_dump(doc, allow_unicode=True, sort_keys=False), encoding="utf-8")

    # ここで seed_ledger を追記
    append_seed_ledger(
        job_root,
        scene_file=out,
        seed=seed,
        commit_hash=commit_hash,
        profile=profile,
        actor=actor or "",
        action=action or "",
        args=args or [],
    )
    return out