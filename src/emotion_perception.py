## src/emotion_perception.py
from typing import Optional, Dict, Any
import random
from .emotion_math import project_nlc_to_lc, hadamard, mix, clip_rgb

def perceived_color(observer, target, context: Optional[Dict[str, Any]] = None):
    """
    A(=observer) から見た B(=target) の “心の空色”(LC) を生成。
    trust が高いほど B の真に近づき、低いほど A の主観で歪む。
    - observer/target は CharacterStatus ライク（.emotion, .relationships, .rel_to_player, .name を持つ）
    - 戻り値は LC (R,G,B) 0..255
    """
    truth = project_nlc_to_lc(target.emotion.nonlinear, target.emotion.confidence)
    a_lc  = project_nlc_to_lc(observer.emotion.nonlinear, observer.emotion.confidence)

    # trust の取得（observer.relationships[target.name] 優先、後方互換で rel_to_player も参照）
    rel = getattr(observer, "relationships", {}).get(target.name) if hasattr(observer, "relationships") else None
    trust_val = rel.trust if rel and hasattr(rel, "trust") else getattr(observer, "rel_to_player", None).trust if hasattr(observer, "rel_to_player") else 0
    trust = max(0.0, min(1.0, trust_val / 100.0))

    lens = hadamard(a_lc, truth)              # Aの色でねじれた観測
    base = mix(truth, lens, 1.0 - trust)      # 信頼で補間

    # コンテキスト：色味のティント＆ノイズ
    tint = None
    noise_sigma = int((1.0 - trust) * 8)
    if isinstance(context, dict):
        tint = context.get("tint")
        noise_sigma = int(context.get("noise_sigma", noise_sigma))
    if tint:
        base = clip_rgb((base[0] + tint[0], base[1] + tint[1], base[2] + tint[2]))
    if noise_sigma > 0:
        base = clip_rgb((
            base[0] + random.randint(-noise_sigma, noise_sigma),
            base[1] + random.randint(-noise_sigma, noise_sigma),
            base[2] + random.randint(-noise_sigma, noise_sigma),
        ))
    return base
