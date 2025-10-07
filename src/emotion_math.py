## src/emotion_math.py
from typing import Tuple
import random

Color = Tuple[int, int, int]

def clip_rgb(c: Color) -> Color:
    r, g, b = (int(c[0]), int(c[1]), int(c[2]))
    return (
        max(0, min(255, r)),
        max(0, min(255, g)),
        max(0, min(255, b)),
    )

def project_nlc_to_lc(nlc: Color, confidence: float = 1.0) -> Color:
    """
    NLC → LC 射影（R≥G≥B の単調回帰に相当）＋ 小ノイズで“ゆらぎ”
    """
    r, g, b = map(int, nlc)
    if g > r:
        avg = (g + r) // 2
        r = g = avg
    if b > g:
        avg = (b + g) // 2
        g = b = avg
    if g > r:
        avg = (g + r) // 2
        r = g = avg
    # 小ゆらぎ：信頼度が低いほど大きい
    sigma = max(0, int((1.0 - float(confidence)) * 4))
    if sigma > 0:
        r += random.randint(-sigma, sigma)
        g += random.randint(-sigma, sigma)
        b += random.randint(-sigma, sigma)
    return clip_rgb((r, g, b))

def expand_lc_to_nlc(lc: Color, confidence: float = 1.0) -> Color:
    """
    LC → NLC の残差サンプリング（1対多）。小ノイズで“ゆらぎ”を付与。
    直交近似ベクトル u1=(0,1,-1), u2=(1,-1,0) に沿って散らす。
    """
    R, G, B = map(int, lc)
    sigma = max(2, int((1.0 - float(confidence)) * 12))
    a = random.randint(-sigma, sigma)
    b = random.randint(-sigma, sigma)
    # u1=(0,1,-1), u2=(1,-1,0)
    r = R + a*1 + b*0
    g = G + a*(-1) + b*1
    bl = B + a*0 + b*(-1)
    return clip_rgb((r, g, bl))

def hadamard(x: Color, y: Color) -> Color:
    return (x[0]*y[0]//255, x[1]*y[1]//255, x[2]*y[2]//255)

def mix(x: Color, y: Color, t: float) -> Color:
    t = max(0.0, min(1.0, float(t)))
    return clip_rgb((
        int(x[0]*(1-t) + y[0]*t),
        int(x[1]*(1-t) + y[1]*t),
        int(x[2]*(1-t) + y[2]*t),
    ))
