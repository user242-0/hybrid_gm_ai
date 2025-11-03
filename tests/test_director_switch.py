import importlib
import sys

import pytest

from src.utility import config_loader


def _load_simulation(monkeypatch, cfg):
    monkeypatch.setattr(config_loader, "_CFG", cfg, raising=False)
    module_name = "src.simulation"
    sys.modules.pop(module_name, None)
    module = importlib.import_module(module_name)
    return module


@pytest.mark.parametrize(
    "enabled, expected_fragment",
    [
        (True, "[Director] enabled"),
        (False, "[Director] disabled"),
    ],
)
def test_director_switch_logs(monkeypatch, capsys, enabled, expected_fragment):
    cfg = {
        "director": {
            "enabled": enabled,
            "seed": 41,
            "premise_path": "data/director/premise.yml",
        }
    }
    _load_simulation(monkeypatch, cfg)
    captured = capsys.readouterr()
    assert expected_fragment in captured.out
    config_loader.load_config(refresh=True)
    sys.modules.pop("src.simulation", None)


def test_director_enabled_logs_title(monkeypatch, capsys):
    cfg = {
        "director": {
            "enabled": True,
            "seed": 41,
            "premise_path": "data/director/premise.yml",
        }
    }
    _load_simulation(monkeypatch, cfg)
    captured = capsys.readouterr()
    assert "[Director] enabled seed=41" in captured.out
    assert "premise='落魄の刑事 vs 愉快犯'" in captured.out
    config_loader.load_config(refresh=True)
    sys.modules.pop("src.simulation", None)
