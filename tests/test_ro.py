"""RO (Recommendation Officer) Phase A tests."""

import json
import tempfile
from pathlib import Path
from unittest.mock import patch

# --- fixture: temp player log and RO diary ---
_tmp = tempfile.mkdtemp()
_player_log = Path(_tmp) / "player.jsonl"
_ro_diary = Path(_tmp) / "ro_diary.jsonl"


def _write_player_log(entries: list[dict]) -> None:
    _player_log.write_text(
        "\n".join(json.dumps(e, ensure_ascii=False) for e in entries) + "\n",
        encoding="utf-8",
    )


def _read_diary_last() -> dict:
    lines = _ro_diary.read_text(encoding="utf-8").strip().splitlines()
    return json.loads(lines[-1])


def _diary_count() -> int:
    if not _ro_diary.exists():
        return 0
    text = _ro_diary.read_text(encoding="utf-8").strip()
    return len(text.splitlines()) if text else 0


# ---- Tests ----

@patch("src.ro.ro.RO_DIARY_PATH", _ro_diary)
@patch("src.ro.ro.LOG_PATH_PLAYER", _player_log)
@patch("src.ro.ro._ro_cfg", return_value={"enabled": False, "log_window": 50})
def test_disabled_returns_none(_cfg):
    """ro.enabled=false → recommend returns None, no diary."""
    from src.ro.ro import recommend
    _write_player_log([{"action_id": "explore", "source": "GUI", "actor_id": "刑事"}])
    assert recommend("刑事", ["explore", "wait"]) is None


@patch("src.ro.ro.RO_DIARY_PATH", _ro_diary)
@patch("src.ro.ro.LOG_PATH_PLAYER", _player_log)
@patch("src.ro.ro._ro_cfg", return_value={"enabled": True, "log_window": 50})
def test_microgoal_boost(_cfg):
    """Microgoal-matching action should be recommended."""
    from src.ro.ro import recommend
    _write_player_log([{"action_id": "wait", "source": "GUI", "actor_id": "刑事"}])
    rec = recommend("刑事", ["explore", "wait", "observe"], microgoal_action="explore")
    assert rec is not None
    assert rec["action_id"] == "explore"
    assert "why" in rec
    assert "マイクロゴール" in rec["why"]


@patch("src.ro.ro.RO_DIARY_PATH", _ro_diary)
@patch("src.ro.ro.LOG_PATH_PLAYER", _player_log)
@patch("src.ro.ro._ro_cfg", return_value={"enabled": True, "log_window": 50})
def test_anti_spam(_cfg):
    """Last-action should not be top recommendation (anti-spam)."""
    from src.ro.ro import recommend
    _write_player_log([
        {"action_id": "explore", "source": "GUI", "actor_id": "刑事"},
        {"action_id": "explore", "source": "GUI", "actor_id": "刑事"},
        {"action_id": "explore", "source": "GUI", "actor_id": "刑事"},
    ])
    rec = recommend("刑事", ["explore", "wait", "observe"])
    assert rec is not None
    # explore was last 3 times → should be penalised, something else picked
    assert rec["action_id"] != "explore"


@patch("src.ro.ro.RO_DIARY_PATH", _ro_diary)
@patch("src.ro.ro.LOG_PATH_PLAYER", _player_log)
@patch("src.ro.ro._ro_cfg", return_value={"enabled": True, "log_window": 50})
def test_diary_written(_cfg):
    """RO must write a diary line with controller_id and required fields."""
    from src.ro.ro import recommend
    before = _diary_count()
    _write_player_log([{"action_id": "wait", "source": "GUI", "actor_id": "刑事"}])
    rec = recommend("刑事", ["explore", "wait"])
    assert rec is not None
    after = _diary_count()
    assert after == before + 1
    entry = _read_diary_last()
    assert entry["source"] == "RO"
    assert entry["controller_id"] == "RO:刑事"
    assert entry["actor_rc_id"] == "刑事"
    assert entry["ro_type"] == "recommendation"
    assert "why" in entry


@patch("src.ro.ro.RO_DIARY_PATH", _ro_diary)
@patch("src.ro.ro.LOG_PATH_PLAYER", _player_log)
@patch("src.ro.ro._ro_cfg", return_value={"enabled": True, "log_window": 50})
def test_empty_candidates(_cfg):
    """No candidates → None."""
    from src.ro.ro import recommend
    assert recommend("刑事", []) is None


@patch("src.ro.ro.RO_DIARY_PATH", _ro_diary)
@patch("src.ro.ro.LOG_PATH_PLAYER", _player_log)
@patch("src.ro.ro._ro_cfg", return_value={"enabled": True, "log_window": 50})
def test_plan_b_present(_cfg):
    """When multiple candidates exist, plan_b should be set."""
    from src.ro.ro import recommend
    _write_player_log([{"action_id": "wait", "source": "GUI", "actor_id": "刑事"}])
    rec = recommend("刑事", ["explore", "wait", "observe"])
    assert rec is not None
    assert "plan_b" in rec


@patch("src.ro.ro.RO_DIARY_PATH", _ro_diary)
@patch("src.ro.ro.LOG_PATH_PLAYER", _player_log)
@patch("src.ro.ro._ro_cfg", return_value={"enabled": True, "log_window": 50})
def test_empty_log(_cfg):
    """No player log → still returns a recommendation from candidates."""
    from src.ro.ro import recommend
    if _player_log.exists():
        _player_log.unlink()
    rec = recommend("刑事", ["explore", "wait"])
    assert rec is not None
    assert rec["action_id"] in ("explore", "wait")
