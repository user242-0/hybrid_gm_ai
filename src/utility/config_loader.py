# src/utility/

import yaml, datetime as dt
from pathlib import Path
from typing import Optional

_CFG = None


def load_config(refresh: bool = False):
    """Load the global YAML configuration as a dict."""
    global _CFG
    if refresh:
        _CFG = None
    return get_cfg()


def get_cfg():
    global _CFG
    if _CFG is None:
        _CFG = yaml.safe_load(Path("config.yml").read_text(encoding="utf-8"))
    return _CFG

def _latest_job_directory(jobs_root: Path) -> Optional[Path]:
    if not jobs_root.exists():
        return None
    candidates = sorted(
        (p for p in jobs_root.iterdir() if p.is_dir()),
        reverse=True,
    )
    return candidates[0] if candidates else None


def job_root_from_cfg():
    cfg = get_cfg()
    datalab_cfg = cfg.get("datalab", {})

    override = datalab_cfg.get("job_dir")
    if override:
        return Path(override).expanduser()

    pat = datalab_cfg.get("job_dir_pattern", "jobs/%Y%m%d_quick")
    dated_path = Path(dt.datetime.now().strftime(pat))
    if dated_path.exists():
        return dated_path

    fallback = _latest_job_directory(Path("jobs"))
    if fallback is not None:
        return fallback

    return dated_path
