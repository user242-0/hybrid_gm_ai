import pytest
from datalab.registry.action_registry import normalize_action

@pytest.mark.parametrize("raw,canon", [
    # 攻撃系
    ("攻撃する", "attack"),
    ("attack", "attack"),
    ("atack", "attack"),            # typo吸収
    ("ATK", "attack"),              # 大文字/略号
    ("戦う", "attack"),
    # 剣を振る系
    ("剣を振る", "swing_sword"),
    ("slash", "swing_sword"),
    ("swing sword", "swing_sword"),
    ("剣をふる", "swing_sword"),    # 揺れ
    # 石像に話す
    ("石像に話す", "talk_to_statue"),
    ("talk to statue", "talk_to_statue"),
    # 交代
    ("交代", "switch_character"),
    ("switch", "switch_character"),
])
def test_normalize_expected(raw, canon):
    assert normalize_action(raw) == canon

def test_normalize_passthrough_for_unknown():
    # 未知語は素通し（上位で raw_key と併用可能）
    assert normalize_action("dance") == "dance"
