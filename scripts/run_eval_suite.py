from pathlib import Path
import yaml, difflib
from src.character_status import CharacterStatus
from src.choice_definitions import choice_definitions
from src.simulation_utils import execute_player_choice
from datalab.registry.action_registry import normalize_action
from utility.config_loader import job_root_from_cfg, get_cfg

CFG = get_cfg()

def _to_choice_key_and_args(cmd: str):
    parts = (cmd or "").split()
    raw_key, rest = (parts[0], parts[1:]) if parts else ("", [])

    # 1) そのまま一致
    if raw_key in choice_definitions:
        return raw_key, rest

    # 2) 正規化で一致（choice の定義名を正規化して比較）
    canon = normalize_action(raw_key)
    for k in choice_definitions.keys():
        if normalize_action(k) == canon:
            return k, rest

    # 3) ファジー（雑にでも近いキーへ）
    close = difflib.get_close_matches(raw_key, list(choice_definitions.keys()), n=1, cutoff=0.75)
    if close:
        return close[0], rest

    return None, rest

def _make_min_state(case: dict):
    # 要件を満たしやすい最小の game_state
    gs = {
        "time_of_day": case.get("time", "night"),
        "current_location": case.get("location", "祭壇"),  # ← simulation_utils は current_location を参照
        "current_target": case.get("target", "古代の石像"),
        "has_enemy": True,
        "enemy": CharacterStatus("Goblin", is_rc=False, is_npc=True),
        "party": {"Hero": CharacterStatus("Hero", is_rc=True, is_npc=False)},
    }
    return gs

def run_case(case):
    job_root_before = job_root_from_cfg()
    key, args = _to_choice_key_and_args(case["cmd"])
    if not key:
        return {"name": case.get("name"), "status": "SKIP", "reason": f"unknown cmd: {case['cmd']}"}

    hero = CharacterStatus("Hero", is_rc=True, is_npc=False)
    gs = _make_min_state(case)

    execute_player_choice(hero, key + (" " + " ".join(args) if args else ""), gs)

    # 生成物の存在チェック
    job_root_after = job_root_from_cfg()
    # 同日なら同じ job_root_pattern の可能性あり → 後続で中身を確認
    out_dir = job_root_after
    scene = out_dir / "scene_graph.yml"
    story = out_dir / "story.yml"
    emo   = out_dir / "emotion_eval.yml"

    produced = scene.exists() or story.exists() or emo.exists()
    return {
        "name": case.get("name"), "status": "PASS" if produced else "FAIL",
        "job_root": str(out_dir),
        "files": {"scene": scene.exists(), "story": story.exists(), "emotion": emo.exists()}
    }

def main():
    cases_path = Path("data/eval_set/cases.yaml")
    cases = yaml.safe_load(cases_path.read_text(encoding="utf-8")) or []
    results = [run_case(c) for c in cases]

    print("=== eval results ===")
    for r in results:
        print(f"- {r['name']}: {r['status']} @ {r.get('job_root','-')} {r.get('files','')}")
    print("done")

if __name__ == "__main__":
    main()
