# src/datalab/registry/action_registry.py
# src/datalab/registry/action_registry.py
from __future__ import annotations
import unicodedata, re, difflib
from pathlib import Path

try:
    import yaml  # 任意（外部YAMLから増補したい場合）
except Exception:
    yaml = None

def _nfkc_lower(s: str) -> str:
    return unicodedata.normalize("NFKC", s or "").strip().lower()

def _slug(s: str) -> str:
    s = _nfkc_lower(s)
    s = re.sub(r"\s+", " ", s)          # 連続空白を1つに
    s = s.replace("　", " ")            # 全角空白→半角
    return s

# 1) 正規化先（canonical） → エイリアス群
_CANON = {
    "swing_sword": [
        "swing_sword","swing sword","slash",
        "斬る","斬りつける","剣を振る","剣をふる","剣で斬る","剣を振り下ろす"
    ],
    "attack": [
        "attack","atk","attk","atack","hit","strike",
        "攻撃","攻撃する","たたかう","戦う","殴る","打つ"
    ],
    "talk_to_statue": [
        "talk_to_statue","talk to statue","speak to statue",
        "石像に話す","石像と話す","像に話す","石像へ話す"
    ],
    "switch_character": [
        "switch_character","switch","switch hero","switch character",
        "交代","キャラ交代","キャラを交代","切替","切り替える"
    ],
    "crouch_ready": [
        "crouch_ready","crouch","ready","身構える","構える"
    ],
}

# 2) 逆引き（alias → canonical）を作る
_ALIAS: dict[str, str] = {}
for canon, aliases in _CANON.items():
    for a in aliases:
        _ALIAS[_slug(a)] = canon

# 3) 任意：外部YAMLで増補（例: src/datalab/registry/action_aliases.yaml）
_ALIASES_PATH = Path("src/datalab/registry/action_aliases.yaml")
if yaml and _ALIASES_PATH.exists():
    try:
        y = yaml.safe_load(_ALIASES_PATH.read_text(encoding="utf-8")) or {}
        for canon, aliases in (y.get("aliases") or {}).items():
            for a in aliases or []:
                _ALIAS[_slug(a)] = canon
    except Exception:
        pass

def normalize_action(key: str, args=None) -> str:
    """
    1) NFKC+lower+空白統一 → 2) 辞書照合 → 3) ファジー吸収（typo対策）
    未知語は素通し（元の表記を返す）して上位で raw_key と併用できます。
    """
    s = _slug(key or "")
    if s in _ALIAS:
        return _ALIAS[s]

    # 軽微なtypo吸収（例: "atack" → "attack"）
    # cutoffは0.88程度が無難。誤爆が気になるなら0.9に上げる
    m = difflib.get_close_matches(s, list(_ALIAS.keys()), n=1, cutoff=0.88)
    if m:
        return _ALIAS[m[0]]

    return s  # 未知語は素通し（resolver側で raw_key と併用）
