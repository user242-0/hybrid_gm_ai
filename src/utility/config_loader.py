# src/utility/

import yaml, datetime as dt
from pathlib import Path

_CFG = None
def get_cfg():
    global _CFG
    if _CFG is None:
        _CFG = yaml.safe_load(Path("config.yml").read_text(encoding="utf-8"))
    return _CFG

def job_root_from_cfg():
    cfg = get_cfg()
    pat = cfg["datalab"].get("job_dir_pattern", "jobs/%Y%m%d_quick")
    return Path(dt.datetime.now().strftime(pat))
