from pathlib import Path
import yaml

def _to01(rgb):  # 0-255 → 0-1
    r,g,b = rgb
    return round(r/255, 4), round(g/255, 4), round(b/255, 4)

def emit_emotion_eval(job_root, *, actor_obj, game_state, thresholds=None):
    job = Path(job_root); job.mkdir(parents=True, exist_ok=True)
    yml = job / "emotion_eval.yml"
    r,g,b = _to01(getattr(actor_obj, "emotion_color", (127,127,255)))
    signals = {
        "salience": 0.7 if game_state.get("has_enemy") else 0.3,
        "novelty": 0.5,
        "emotion": {"red_impulse": r, "green_control": g, "blue_kindness": b},
    }
    base = {"eval_id": game_state.get("eval_id", "auto"),
            "signals": signals,
            "emit_if": thresholds or {"salience_min": 0.60, "red_impulse_min": 0.50}}
    yml.write_text(yaml.safe_dump(base, allow_unicode=True, sort_keys=False), encoding="utf-8")
    # 将来的にはここで threshold 判定→ True のときだけ scene_graph を発火
    return base

# 既存の emit_emotion_eval の下あたりに追加
def summarize_why_now(signals: dict, thresholds: dict, *, label_ok="OK", label_ng="NG"):
    """
    例: "salience≥0.60 & red_impulse≥0.50 (actual: 0.72, 0.64)"
    """
    t_sal = float(thresholds.get("salience_min", 0.0))
    t_red = float(thresholds.get("red_impulse_min", 0.0))
    sal   = float(signals.get("salience", 0.0))
    red   = float(signals.get("emotion", {}).get("red_impulse", 0.0))
    ok_sal = sal >= t_sal
    ok_red = red >= t_red
    ok = ok_sal and ok_red
    text = (f"{label_ok if ok else label_ng}: "
            f"salience {sal:.2f} {'≥' if ok_sal else '<'} {t_sal:.2f}, "
            f"red_impulse {red:.2f} {'≥' if ok_red else '<'} {t_red:.2f}")
    return {"ok": ok,
            "text": text,
            "checks": {"salience": {"actual": sal, "min": t_sal, "ok": ok_sal},
                       "red_impulse": {"actual": red, "min": t_red, "ok": ok_red}}}
