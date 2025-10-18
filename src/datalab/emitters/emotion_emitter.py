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
    return (signals["salience"] >= base["emit_if"]["salience_min"]
            and signals["emotion"]["red_impulse"] >= base["emit_if"]["red_impulse_min"])
