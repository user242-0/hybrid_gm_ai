from pathlib import Path
from datetime import datetime
import yaml
from datalab.registry.action_registry import normalize_action


from datalab.registry.action_registry import normalize_action

def _one_liner(actor, action, args, gs) -> str:
    loc = gs.get("current_location", "どこか")
    tgt = args[0] if args else ""
    norm = normalize_action(action, args)

    if norm == "swing_sword":
        return f"{loc}で、{actor}は{(tgt + 'へ') if tgt else ''}一閃する"
    if norm == "attack":
        return f"{loc}で、{actor}は{(tgt + 'に') if tgt else ''}攻めかかる"
    if norm == "talk_to_statue":
        return f"{loc}で、{actor}は石像にそっと語りかける"
    if norm == "switch_character":
        new_char = tgt or gs.get("next_actor") or "別のキャラ"
        return f"視点が{new_char}へ切り替わる"

    # フォールバック
    return f"{loc}で、{actor}が{action}{(' ' + ' '.join(args)) if args else ''}"

def _infer_intent(action: str) -> str:
    norm = normalize_action(action, None)
    if norm in ("swing_sword", "attack"):
        return "実行"
    if norm == "talk_to_statue":
        return "会話"
    if norm == "switch_character":
        return "視点移動"
    return "描写"

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
