from typing import Dict, Tuple


def derived_traits(world: Dict) -> Tuple[float, float, float]:
    """
    Emotion(R,G,B)から簡易的な性格指標を算出する。

    boldness: 衝動が高く自己制御が低いほど大きい（大胆さ）
    kindness: Bそのもの（対外への優しさ）
    guilt:    優しさが高いのに世界の被害(harm)が高いほど大きい（罪悪感の芽）
    """
    emo = world.get("emotion", {})
    r = emo.get("R", 127) / 255.0
    g = emo.get("G", 127) / 255.0
    b = emo.get("B", 127) / 255.0

    boldness = r * (1.0 - g * 0.5)  # 衝動高 & 制御低 で大きくなる
    kindness = b
    harm_cfg = world.get("harm", {})
    harm_val = harm_cfg.get("value", 0)
    harm_thr = harm_cfg.get("threshold_warn", 20)
    harm_norm = harm_val / max(1.0, float(harm_thr))
    guilt = max(0.0, b * harm_norm)

    return boldness, kindness, guilt
