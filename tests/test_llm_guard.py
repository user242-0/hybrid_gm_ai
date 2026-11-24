import runpy
import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from src.actions import exploration, npc_interactions, utility
from src.utility import config_loader, llm_guard


ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(autouse=True)
def disable_stub_overrides(monkeypatch):
    monkeypatch.delenv("GM_USE_STUB", raising=False)
    monkeypatch.delenv("CI", raising=False)


@pytest.mark.parametrize(
    "config",
    [
        None, [], {}, {"llm": None}, {"llm": []}, {"llm": {}},
        {"llm": {"mode": None}}, {"llm": {"mode": False}},
        {"llm": {"mode": True}}, {"llm": {"mode": 1}},
        {"llm": {"mode": []}}, {"llm": {"mode": "OFF"}},
        {"llm": {"mode": "dialogue_only "}}, {"llm": {"mode": "unknown"}},
    ],
)
def test_invalid_or_missing_llm_mode_is_denied(monkeypatch, config):
    monkeypatch.setattr(llm_guard, "get_cfg", lambda: config)
    assert llm_guard.can_call_llm("player", "generate_flavor") == (
        False, "invalid_or_missing_llm_mode"
    )


@pytest.mark.parametrize("flag, value", [("GM_USE_STUB", "1"), ("CI", "true")])
def test_forced_stub_does_not_load_config(monkeypatch, flag, value):
    read_config = Mock(side_effect=AssertionError("read config in forced stub mode"))
    monkeypatch.setattr(llm_guard, "get_cfg", read_config)
    monkeypatch.setenv(flag, value)

    assert llm_guard.can_call_llm("player", "generate_flavor") == (False, "forced_stub")
    read_config.assert_not_called()


def test_unexpected_config_read_failure_is_denied(monkeypatch):
    monkeypatch.setattr(llm_guard, "get_cfg", Mock(side_effect=OSError))
    assert llm_guard.can_call_llm("player", "generate_flavor") == (False, "config_unavailable")


@pytest.mark.parametrize("contents", [None, "llm: [", "- off", ""])
def test_unreadable_or_invalid_config_uses_game_defaults(monkeypatch, tmp_path, contents):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(config_loader, "_CFG", None)
    if contents is not None:
        (tmp_path / "config.yml").write_text(contents, encoding="utf-8")

    assert config_loader.get_cfg() == {}
    assert not llm_guard.can_call_llm("player", "generate_flavor")[0]
    simulation_utils = runpy.run_path(str(ROOT / "src/simulation_utils.py"))
    assert simulation_utils["SCENE_EMIT_ON"] is True
    simulation = runpy.run_path(str(ROOT / "src/simulation.py"))
    assert simulation["ctx"].game_state["running"] is True


@pytest.mark.parametrize(
    "yaml_mode, parsed_modes",
    [('"off"', ("off",)), ("false", (False,)), ("off", ("off", False))],
)
def test_yaml_off_and_boolean_are_both_closed(monkeypatch, tmp_path, yaml_mode, parsed_modes):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(config_loader, "_CFG", None)
    (tmp_path / "config.yml").write_text(
        f"llm:\n  mode: {yaml_mode}\ndebug:\n  hud_demo: true\n", encoding="utf-8"
    )

    config = config_loader.get_cfg()
    value = config["llm"]["mode"]
    assert value in parsed_modes
    reason = "llm.mode=off" if value == "off" else "invalid_or_missing_llm_mode"
    assert llm_guard.can_call_llm("player", "generate_flavor") == (False, reason)
    assert config["debug"]["hud_demo"] is True


@pytest.mark.parametrize("allow_actions", [[], None, "generate_flavor", [False], ["generate_flavor"]])
@pytest.mark.parametrize("mode", ["dialogue_only", "player_only", "rc_only", "all"])
def test_allow_list_and_caller_labels_do_not_open_send_paths(monkeypatch, mode, allow_actions):
    monkeypatch.setattr(
        llm_guard, "get_cfg", lambda: {"llm": {"mode": mode, "allow_actions": allow_actions}}
    )

    for caller, action in (
        ("player", "generate_flavor"), ("rc", "generate_flavor"),
        ("HUD Auto", "generate_flavor"), ("RO", None),
        ("player", "dialogue_send"),
    ):
        assert not llm_guard.can_call_llm(caller, action)[0]


@pytest.mark.parametrize("mode", ["off", "dialogue_only", "all"])
def test_game_actions_use_local_responses_without_opening_clients(monkeypatch, mode):
    monkeypatch.setattr(llm_guard, "get_cfg", lambda: {"llm": {"mode": mode}})
    create_client = Mock(side_effect=AssertionError("API client constructed"))
    send = Mock(side_effect=AssertionError("API send attempted"))
    monkeypatch.setattr(utility, "_get_client", create_client)
    monkeypatch.setattr(exploration, "_get_client", create_client)
    monkeypatch.setattr(
        npc_interactions, "openai", SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=send))),
        raising=False,
    )

    assert utility.generate_flavor_text("休む", [], "酒場") == "休む。酒場の空気がわずかに揺れた。"
    assert exploration.generate_dynamic_event("目的", {}) == "空気がわずかに揺れた。"
    assert exploration.generate_location_event("酒場", "会話", "目的", "簡単") == "空気がわずかに揺れた。"
    inputs = iter(("4", "自由入力"))
    monkeypatch.setattr("builtins.input", lambda _prompt: next(inputs))
    game_state = {"current_target": "古代の石像"}
    result = npc_interactions.talk_to_statue_with_cooldown(None, game_state)
    assert result["omni_response"] == "今は語るべきことがない。時を置いて訪れよ。"
    assert game_state["cooldown_status"]["古代の石像"] > 0
    create_client.assert_not_called()
    send.assert_not_called()


def test_legacy_scripts_skip_api_setup_and_key_output(monkeypatch, capsys):
    load_dotenv = Mock(side_effect=AssertionError("attempted to load credentials"))
    monkeypatch.setitem(sys.modules, "dotenv", SimpleNamespace(load_dotenv=load_dotenv))
    monkeypatch.setitem(sys.modules, "openai", None)
    rules_script = runpy.run_path(str(ROOT / "scripts/generate_rules_APItest.py"), run_name="__main__")
    runpy.run_path(str(ROOT / "scripts/loadenv_test.py"), run_name="__main__")

    with pytest.raises(RuntimeError, match="Legacy API experiment is disabled"):
        rules_script["analyze_logs_with_ai"]([])
    assert capsys.readouterr().out.splitlines() == [
        "旧ルール生成API実験は無効です。",
        "旧APIキー診断は無効です。",
    ]
    load_dotenv.assert_not_called()
