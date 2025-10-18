from pathlib import Path
from datetime import datetime
import yaml

def _infer_intent(action: str) -> str:
    return {"swing_sword": "実行", "攻撃する": "実行", "戦う": "実行"}.get(action, "描写")

def _one_liner(actor, action, args, gs) -> str:
    loc = gs.get("current_location", "どこか")
    if action == "swing_sword":
        return f"{loc}で、{actor}は一閃する"
    return f"{loc}で、{actor}が{action}{(' ' + ' '.join(args)) if args else ''}"

def emit_story_line(job_root, *, actor, action, args, game_state, extra=None):
    job = Path(job_root); job.mkdir(parents=True, exist_ok=True)
    yml = job / "story.yml"
    story = {"story_id": datetime.now().strftime("%Y%m%d-%H%M%S"),
             "theme": game_state.get("theme", ""),
             "beats": [], "constraints": {"pov": "三人称/近距離"}}
    if yml.exists():
        try:
            loaded = yaml.safe_load(yml.read_text(encoding="utf-8")) or {}
            story.update({k: loaded.get(k, v) for k, v in story.items()})
            story["beats"] = loaded.get("beats", [])
        except Exception:
            pass

    beat = {
        "id": f"beat{len(story['beats'])+1}",
        "summary": _one_liner(actor, action, args, game_state),
        "intent": _infer_intent(action),
    }
    if extra: beat.update(extra)
    story["beats"].append(beat)
    yml.write_text(yaml.safe_dump(story, allow_unicode=True, sort_keys=False), encoding="utf-8")
