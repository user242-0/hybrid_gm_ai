"""log_action に controller_id / actor_rc_id が自動付与されることを検証する"""
import json, tempfile, os
from pathlib import Path
from unittest.mock import patch

# log_action の書き込み先を一時ディレクトリに差し替える
_tmp = tempfile.mkdtemp()
_full = Path(_tmp) / "full.jsonl"
_player = Path(_tmp) / "player.jsonl"


def _read_last(path: Path) -> dict:
    """最終行を dict で返す"""
    lines = path.read_text(encoding="utf-8").strip().splitlines()
    return json.loads(lines[-1])


@patch("src.logger.LOG_PATH_FULL", _full)
@patch("src.logger.LOG_PATH_PLAYER", _player)
@patch("src.logger._get_logging_config", return_value={"full_enabled": True, "full_exclude_actions": []})
def test_rc_ai_controller_id(_mock_cfg):
    """source=RC_AI, actor_id=刑事 → controller_id='RC_AI:刑事', actor_rc_id='刑事'"""
    from src.logger import log_action
    log_action(source="RC_AI", actor_id="刑事", action_id="patrol")
    entry = _read_last(_full)
    assert entry["controller_id"] == "RC_AI:刑事"
    assert entry["actor_rc_id"] == "刑事"
    # 既存フィールドも残っている
    assert entry["source"] == "RC_AI"
    assert entry["actor_id"] == "刑事"


@patch("src.logger.LOG_PATH_FULL", _full)
@patch("src.logger.LOG_PATH_PLAYER", _player)
@patch("src.logger._get_logging_config", return_value={"full_enabled": True, "full_exclude_actions": []})
def test_gui_controller_id(_mock_cfg):
    """source=GUI, actor_id=愉快犯 → controller_id='PLAYER:GUI', actor_rc_id='愉快犯'"""
    from src.logger import log_action
    log_action(source="GUI", actor_id="愉快犯", action_id="talk")
    entry = _read_last(_player)
    assert entry["controller_id"] == "PLAYER:GUI"
    assert entry["actor_rc_id"] == "愉快犯"


@patch("src.logger.LOG_PATH_FULL", _full)
@patch("src.logger.LOG_PATH_PLAYER", _player)
@patch("src.logger._get_logging_config", return_value={"full_enabled": True, "full_exclude_actions": []})
def test_hud_controller_id(_mock_cfg):
    """source=HUD → controller_id='PLAYER:HUD'"""
    from src.logger import log_action
    log_action(source="HUD", actor_id="刑事", action_id="rest")
    entry = _read_last(_player)
    assert entry["controller_id"] == "PLAYER:HUD"


@patch("src.logger.LOG_PATH_FULL", _full)
@patch("src.logger.LOG_PATH_PLAYER", _player)
@patch("src.logger._get_logging_config", return_value={"full_enabled": True, "full_exclude_actions": []})
def test_legacy_actor_field_fallback(_mock_cfg):
    """actor_id が無く actor だけある旧形式でも actor_rc_id が付く"""
    from src.logger import log_action
    log_action(source="RC_AI", actor="刑事", action="patrol")
    entry = _read_last(_full)
    assert entry["controller_id"] == "RC_AI:刑事"
    assert entry["actor_rc_id"] == "刑事"


@patch("src.logger.LOG_PATH_FULL", _full)
@patch("src.logger.LOG_PATH_PLAYER", _player)
@patch("src.logger._get_logging_config", return_value={"full_enabled": True, "full_exclude_actions": []})
def test_explicit_controller_id_not_overwritten(_mock_cfg):
    """呼び出し側が明示的に controller_id を渡した場合は上書きしない"""
    from src.logger import log_action
    log_action(source="RC_AI", actor_id="刑事", action_id="x", controller_id="RO:刑事")
    entry = _read_last(_full)
    assert entry["controller_id"] == "RO:刑事"


@patch("src.logger.LOG_PATH_FULL", _full)
@patch("src.logger.LOG_PATH_PLAYER", _player)
@patch("src.logger._get_logging_config", return_value={"full_enabled": True, "full_exclude_actions": []})
def test_no_source_no_controller_id(_mock_cfg):
    """source も actor_id も無い行 → controller_id / actor_rc_id は付かない"""
    from src.logger import log_action
    log_action(action_id="noop")
    entry = _read_last(_full)
    assert "controller_id" not in entry
    assert "actor_rc_id" not in entry
