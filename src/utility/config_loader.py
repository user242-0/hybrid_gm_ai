# src/utility/

import os
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


def get_rc_excluded_actions() -> list:
    """
    RCが選択候補から除外するアクションのリストを取得。
    config.yml の rc.excluded_actions を参照。
    """
    cfg = get_cfg()
    rc_cfg = cfg.get("rc", {})
    return rc_cfg.get("excluded_actions", [])


def get_rc_decision_interval_sec() -> float:
    """RC意思決定の最短間隔（秒）"""
    cfg = get_cfg()
    rc_cfg = cfg.get("rc", {})
    return float(rc_cfg.get("decision_interval_sec", 1.0))


def get_rc_max_advance_minutes() -> int:
    """入力待ち中にRCが進められる累積時間の上限（ゲーム内分）"""
    cfg = get_cfg()
    rc_cfg = cfg.get("rc", {})
    return int(rc_cfg.get("max_advance_minutes_while_input_pending", 10))


def is_hud_debug_enabled() -> bool:
    """
    HUD_DEBUGログを有効にするかどうか。
    優先順位: 環境変数 HUD_DEBUG > config.yml の debug.hud_debug
    """
    # 環境変数でオーバーライド
    env_val = os.environ.get("HUD_DEBUG", "").lower()
    if env_val in ("1", "true", "yes", "on"):
        return True
    if env_val in ("0", "false", "no", "off"):
        return False

    # config.yml から取得
    cfg = get_cfg()
    debug_cfg = cfg.get("debug", {})
    return bool(debug_cfg.get("hud_debug", False))


def is_hud_demo_enabled() -> bool:
    """
    Return whether the capture-oriented Director HUD controls are enabled.

    Priority: HUD_DEMO environment variable > config.yml debug.hud_demo.
    """
    env_val = os.environ.get("HUD_DEMO", "").lower()
    if env_val in ("1", "true", "yes", "on"):
        return True
    if env_val in ("0", "false", "no", "off"):
        return False

    cfg = get_cfg()
    debug_cfg = cfg.get("debug", {})
    return bool(debug_cfg.get("hud_demo", False))


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

    pat = datalab_cfg.get("job_dir_pattern")
    if pat:
        try:
            return Path(dt.datetime.now().strftime(pat))
        except ValueError:
            # 無効な strftime パターン → 後段のデフォルト処理にフォールバック
            pass

    # パターンが未指定 or 無効な場合は旧仕様（jobs 配下の最新 or 既定パターン）に従う
    fallback = _latest_job_directory(Path("jobs"))
    if fallback is not None:
        return fallback

    default_path = Path(dt.datetime.now().strftime("jobs/%Y%m%d_quick"))
    return default_path
