# B〜E: emotion変換・知覚・要件ゲートの統合テスト
# 実行例:  pytest -q tests/test_emotion_system.py

import os, sys, types
import pytest

# プロジェクトルートを import path に追加
sys.path.insert(0, os.path.abspath("."))

# --- 被検モジュール ---
import src.emotion_math as emath
from src.emotion_math import project_nlc_to_lc, expand_lc_to_nlc, hadamard
from src.emotion_state import EmotionState
import src.emotion_perception as eperc
from src.emotion_perception import perceived_color
from src.requirements_checker import RequirementsChecker  # 辞書型要件の評価仕様に準拠（B〜Eで使用）


# ==== ヘルパ（最小限のキャラ/関係スタブ） ====

class DummyChar:
    """perceived_color が参照する最小限の属性を持つスタブ"""
    def __init__(self, name: str, nlc=(127,127,255), confidence=1.0):
        self.name = name
        # EmotionState (NLC主) を用意し、LCは射影で更新
        self.emotion = EmotionState(confidence=confidence)
        self.emotion.set_nonlinear(tuple(nlc), update_linear=True, source="inferred")
        # A→B専用: 任意の相手 name -> Relationship相当（trustだけ持つ）を格納
        self.relationships = {}
        # 後方互換のための fallback
        self.rel_to_player = types.SimpleNamespace(trust=0)
        # 旧互換: UI表示LC（要らなければ未使用）
        self.emotion_color = self.emotion.linear

    def set_trust_to(self, target_name: str, trust: int):
        self.relationships[target_name] = types.SimpleNamespace(trust=int(trust))

def make_game_state(**kwargs):
    """RequirementsChecker に渡す最小の game_state スタブ"""
    state = {
        "party": {},           # name -> char
        "party_map": {},
        "enemy": None,
        "current_target": None,
    }
    state.update(kwargs)
    return state


# =========================
# B) 変換の性質（NLC↔LC）
# =========================

@pytest.mark.parametrize("nlc", [
    (10, 200, 50),
    (180, 60, 90),
    (255, 0, 255),
    (0, 0, 0),
    (254, 253, 252),
])
def test_project_nlc_to_lc_is_monotonic(nlc):
    """NLC→LC後は R≥G≥B を必ず満たす"""
    lc = project_nlc_to_lc(nlc, confidence=1.0)   # conf=1.0 でノイズ0
    assert lc[0] >= lc[1] >= lc[2], f"NLC={nlc} -> LC={lc} が単調順になっていない"


def test_lc_to_nlc_roundtrip_stability(monkeypatch):
    """
    LC→NLC→LC の往復で LC が大きく崩れないこと。
    ノイズは monkeypatch で 0 に固定して厳密比較。
    """
    # expand/project 内の乱数を 0 に固定
    monkeypatch.setattr(emath.random, "randint", lambda a, b: 0)
    lc_cases = [(220, 160, 120), (200, 200, 200), (255, 128, 64)]
    for lc0 in lc_cases:
        nlc = expand_lc_to_nlc(lc0, confidence=1.0)     # ノイズ0
        lc1 = project_nlc_to_lc(nlc, confidence=1.0)    # ノイズ0
        assert lc1 == lc0, f"往復でLCが変化: {lc0} -> {nlc} -> {lc1}"


# =========================
# C) A→B の知覚色（perceived_color）
# =========================

def test_perceived_color_with_high_trust_equals_truth(monkeypatch):
    """trust=100 のとき、A→B は Bの真のLC（NLC射影）と一致する"""
    # 乱数ノイズ（noise_sigma）は trust=100 で 0 だが、念のため固定
    monkeypatch.setattr(eperc.random, "randint", lambda a, b: 0)
    A = DummyChar("A", nlc=(60, 120, 200), confidence=1.0)
    B = DummyChar("B", nlc=(180, 100, 40), confidence=1.0)
    A.set_trust_to("B", 100)

    truth = project_nlc_to_lc(B.emotion.nonlinear, B.emotion.confidence)
    c = perceived_color(A, B)
    assert c == truth, f"trust=100 でも真のLCに一致しない: truth={truth}, got={c}"


def test_perceived_color_with_low_trust_skews_to_lens(monkeypatch):
    """
    trust=0 のとき、Aの主観で歪んだ lens=hadamard(A_lc, truth) に一致する
    （ノイズは0に固定）
    """
    monkeypatch.setattr(eperc.random, "randint", lambda a, b: 0)
    A = DummyChar("A", nlc=(255, 50, 50), confidence=1.0)
    B = DummyChar("B", nlc=(50, 200, 200), confidence=1.0)
    A.set_trust_to("B", 0)

    a_lc  = project_nlc_to_lc(A.emotion.nonlinear, A.emotion.confidence)
    truth = project_nlc_to_lc(B.emotion.nonlinear, B.emotion.confidence)
    lens  = hadamard(a_lc, truth)
    c = perceived_color(A, B)
    assert c == lens, f"trust=0 で lens に一致しない: lens={lens}, got={c}"


def test_perceived_color_uses_rel_to_player_fallback(monkeypatch):
    """relationships に B が無い場合は rel_to_player.trust をフォールバック参照"""
    monkeypatch.setattr(eperc.random, "randint", lambda a, b: 0)
    A = DummyChar("A", nlc=(20, 220, 100), confidence=1.0)
    B = DummyChar("B", nlc=(200, 80, 60), confidence=1.0)
    # relationships は空のまま
    A.rel_to_player.trust = 100  # フォールバック

    truth = project_nlc_to_lc(B.emotion.nonlinear, B.emotion.confidence)
    c = perceived_color(A, B)
    assert c == truth


# =========================
# D) 要件ゲート（emotion_*）
# =========================

def test_requirements_emotion_thresholds_with_lc(monkeypatch):
    """
    RequirementsChecker の emotion_* キーで LC 閾値が効くこと。
    - emotion_b_at_least: B成分でゲート
    """
    # プレイヤースタブ（EmotionState優先で参照される）
    player = types.SimpleNamespace(name="主人公")
    player.emotion = EmotionState(confidence=1.0)
    # まず B=100 （未達）
    player.emotion.set_nonlinear((10, 10, 10), update_linear=True)  # 初期化
    player.emotion.linear = (50, 50, 100)

    checker = RequirementsChecker(game_state={}, player_status=player)

    assert checker.check_all({"emotion_b_at_least": 180}) is False, "B=100で通ってしまう"
    # 閾値を超える LC に更新
    player.emotion.linear = (50, 50, 200)
    assert checker.check_all({"emotion_b_at_least": 180}) is True, "B=200で通らない"


# =========================
# E) 関係ラベル要件
# =========================

def test_has_relation_label_to_target_true_then_false():
    """
    current_target に対して『主人公→target』の関係ラベルがあるときのみ True。
    付与→判定→ラベル外し→再判定の順で確認。
    """
    # 対象キャラ（B）とプレイヤー
    B = DummyChar("B")
    player = DummyChar("主人公")
    # B に「主人公から見て: 友人」ラベルを付与（実装は set で十分）
    B.relationship_tags_from = {player.name: {"友人"}}

    gs = make_game_state(current_target="B", party={"B": B})
    checker = RequirementsChecker(game_state=gs, player_status=player)

    assert checker.check_all({"has_relation_label_to_target": "友人"}) is True
    assert checker.check_all({"has_relation_label_to_target": "恋人候補"}) is False

    # ラベルを外して False になることを確認
    B.relationship_tags_from[player.name].remove("友人")
    assert checker.check_all({"has_relation_label_to_target": "友人"}) is False
