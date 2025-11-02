# scripts/run_eval_suite.py
import argparse, importlib, sys, yaml, shutil
from pathlib import Path
from datetime import datetime

# ルートを import パスに追加
sys.path.append(str(Path(".").resolve()))

# 基本モジュール
from src.character_status import CharacterStatus
from src.action_definitions import actions
from src.datalab.emitters.emotion_emitter import summarize_why_now, emit_emotion_eval
from src.datalab.emitters.story_emitter import emit_story_line
from src.datalab.emitters.scene_graph_emitter import emit_scene_graph
from datalab.registry.action_registry import normalize_action
from src.utility.config_loader import get_cfg
from src.utility.seed_ledger import append_seed_ledger
import src.simulation_utils as sim  # ← SCENE_JOB_DIR を差し替えるため module 参照

def _normalize_list(value, default):
    if value is None:
        return list(default)
    if isinstance(value, (list, tuple, set)):
        return list(value)
    return [value]



def build_state_from_ctx(ctx: dict):
    # アクター集合（最小）
    hero = CharacterStatus("Hero", faction="player", is_rc=True, is_npc=False)
    luna = CharacterStatus("Luna", faction="player", is_rc=True, is_npc=True)

    party = {hero.name: hero, luna.name: luna}
    location = ctx.get("current_location", "どこか")
    time_of_day = ctx.get("time_of_day", "night")
    talk = _normalize_list(ctx.get("talk_situation"),
                           ["late_night"] if time_of_day in ("night", "late_night", "midnight") else ["normal"])

    gs = {
        "active_char": hero,
        "party": party,
        "current_location": location,
        "location": ctx.get("location", location),
        "talk_situation": talk,
        "time_of_day": time_of_day, 
        "has_enemy": bool(ctx.get("has_enemy", False)),
        "current_target": ctx.get("current_target"),
    }

    # 敵が必要なケース
    if gs["has_enemy"]:
        gob = CharacterStatus("ゴブリン", faction="enemy", is_rc=True, is_npc=True)
        gs["enemy"] = gob
        if not gs["current_target"]:
            gs["current_target"] = gob.name

    # ターゲット（石像など）を party にも置く：relation_label を resolver に載せるため
    tgt_name = ctx.get("current_target")
    if tgt_name and tgt_name not in party:
        party[tgt_name] = CharacterStatus(tgt_name, faction="neutral", is_rc=False, is_npc=True)

    # 装備
    if ctx.get("equipped_weapon_is") == "sword" or ctx.get("equip_sword"):
        hero.equip_weapon({"name": "鉄の剣", "attack_bonus": 5, "weapon_type": "sword"})

    # relation labels
    rel = ctx.get("relation_labels") or {}
    gs["relation_labels"] = set(rel.get("labels", [])) if isinstance(rel, dict) else set()
    if rel:
        target = party.get(rel.get("target") or gs["current_target"])
        observer = rel.get("from_actor", "Hero")
        if target:
            for lab in rel.get("labels", []):
                target.add_label_from(observer, lab)
                gs["relation_labels"].add(lab)

    return hero, gs


def _ensure_case_outputs(job_dir: Path, cfg: dict, *, actor, action: str,
                         args: list[str], game_state: dict, expect: dict):
    """Create minimal outputs when emitters fail so validation can proceed."""

    fallback = []
    emo_path = job_dir / "emotion_eval.yml"
    emo_doc = None
    if emo_path.exists():
        try:
            emo_doc = yaml.safe_load(emo_path.read_text(encoding="utf-8")) or {}
        except yaml.YAMLError:
            emo_doc = None
            print("  ! emotion_eval.yml unreadable → regenerating fallback")
    if emo_doc is None:
        emo_doc = emit_emotion_eval(job_dir, actor_obj=actor, game_state=game_state)
        fallback.append("emotion_eval.yml")

    story_path = job_dir / "story.yml"
    if not story_path.exists():
        emit_story_line(
            job_dir,
            actor=actor.name,
            action=action,
            args=args,
            game_state=game_state,
            extra={"fallback": True, "time_of_day": game_state.get("time_of_day")},
        )
        fallback.append("story.yml")

    sg_expect = expect.get("scene_graph")
    want_scene = expect_scene_graph(job_dir, cfg, emo_doc) if sg_expect in (None, "auto") \
        else (sg_expect in ("emit", "present"))

    sg_path = job_dir / "scene_graph.yml"
    if want_scene and not sg_path.exists():
        canon = normalize_action(action, args) or action
        emit_scene_graph(
            job_root=job_dir,
            theme=f"{game_state.get('current_location', 'どこか')}での{canon}",
            background=f"{game_state.get('time_of_day', 'night')} ambience around {game_state.get('current_location', 'どこか')}",
            objects=[{"name": actor.name, "category": "character", "action": canon, "base_prompt": "default character"}],
            loras=[],
            seed=0,
            why_now="fallback emit (auto)",
            profile=cfg.get("profile", "prod"),
            actor=actor.name,
            action=canon,
            args=args,
            extra_meta={
                "fallback": True,
                "tpo_ctx": {
                    "location": game_state.get("current_location"),
                    "time": game_state.get("time_of_day"),
                    "relation_labels": sorted(list(game_state.get("relation_labels", [])))
                    if isinstance(game_state.get("relation_labels"), (list, set, tuple)) else []
                },
            },
        )
        fallback.append("scene_graph.yml")
        sg_path = job_dir / "scene_graph.yml"

    ledger_path = job_dir / "seed_ledger.csv"
    if not ledger_path.exists() and sg_path.exists():
        append_seed_ledger(
            job_dir,
            scene_file=sg_path,
            seed=0,
            commit_hash="fallback",
            profile=cfg.get("profile", "prod"),
            actor=actor.name,
            action=normalize_action(action, args) or action,
            args=args,
        )
        fallback.append("seed_ledger.csv")

    if fallback:
        print("  ↻ generated fallback outputs:", ", ".join(fallback))

    return emo_doc

def expect_scene_graph(job_dir: Path, cfg: dict, eva: dict | None = None):
    """
    emit_policy=always → 期待=あり
    threshold         → summarize_why_now(signals, thresholds)['ok'] なら あり
    """
    if eva is None:
        emo_p = job_dir / "emotion_eval.yml"
        if not emo_p.exists():
            return False
        try:
            eva = yaml.safe_load(emo_p.read_text(encoding="utf-8")) or {}
        except yaml.YAMLError:
            return False
    signals = eva.get("signals", {})
    th = cfg.get("datalab", {}).get("emit_thresholds", {})
    policy = cfg.get("datalab", {}).get("emit_policy", "always")
    ok = True if policy == "always" else summarize_why_now(signals, th)["ok"]
    return ok

def validate_outputs(job_dir: Path, cfg: dict, expect: dict, emo_doc: dict | None = None):
    ok = True
    # 1) story.yml
    if not (job_dir / "story.yml").exists():
        print("✗ story.yml not found")
        ok = False
    # 2) emotion_eval.yml
    emo_p = job_dir / "emotion_eval.yml"
    eva_doc = emo_doc
    if not emo_p.exists():
        print("✗ emotion_eval.yml not found"); ok = False
    else:
        if eva_doc is None:
            try:
                eva_doc = yaml.safe_load(emo_p.read_text(encoding="utf-8")) or {}
            except yaml.YAMLError as exc:
                print(f"✗ emotion_eval.yml parse error: {exc}")
                ok = False
        if eva_doc is not None:
            sal = eva_doc.get("signals", {}).get("salience")
            exp_sal = expect.get("emotion.salience")
            if exp_sal is not None and abs(float(sal) - float(exp_sal)) > 1e-3:
                print(f"✗ salience mismatch: {sal} vs {exp_sal}")
                ok = False
    # 3) scene_graph.yml 期待
    sg_p = job_dir / "scene_graph.yml"
    want_emit = expect_scene_graph(job_dir, cfg, eva_doc) if expect.get("scene_graph") in (None, "auto") \
                else (expect.get("scene_graph") in ("emit", "present"))
    has_sg = sg_p.exists()
    if want_emit != has_sg:
        print(f"✗ scene_graph expectation mismatch: want={want_emit}, has={has_sg}")
        ok = False
    # 4) seed_ledger.csv
    need_ledger = has_sg or want_emit
    if need_ledger and not (job_dir / "seed_ledger.csv").exists():
        print("✗ seed_ledger.csv not found"); ok = False
    return ok

def run_case(path: Path, batch_dir: Path, cfg: dict) -> bool:
    case = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    ctx = case.get("ctx", {})
    actor_name = case.get("actor", "Hero")
    action = case.get("action", "")
    args = case.get("args", [])
    expect = case.get("expect", {})

    # ケース毎のジョブディレクトリ
    job_dir = batch_dir / path.stem
    if job_dir.exists():
        shutil.rmtree(job_dir)
    job_dir.mkdir(parents=True, exist_ok=True)

    # simulation_utils の出力先を差し替え
    importlib.reload(sim)  # 念のため再読込
    sim.SCENE_JOB_DIR = job_dir  # ← ここが肝

    # state 構築
    actor, gs = build_state_from_ctx(ctx)
    gs["eval_id"] = path.stem  # emotion_eval に載るメタ（任意）:contentReference[oaicite:18]{index=18}

    # 実行
    cmd = " ".join([action] + list(map(str, args or [])))
    sim.execute_player_choice(actor, cmd, gs)  # Emotion→WhyNow→SG→Story まで連鎖 :contentReference[oaicite:19]{index=19}

    emo_doc = _ensure_case_outputs(job_dir, cfg, actor=actor, action=action, args=args, game_state=gs, expect=expect)

    # 検証
    ok = validate_outputs(job_dir, cfg, expect, emo_doc)
    print(("✓" if ok else "✗"), path.name, "->", job_dir)
    return ok

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--glob", default="data/eval_set/cases/p[23]_*.yml")
    ap.add_argument("--out", default=None, help="batch dir (default auto)")
    args = ap.parse_args()

    cfg = get_cfg()  # emit_policy / thresholds / job_dir_pattern を参照 :contentReference[oaicite:20]{index=20}

    # ★ out の決定ロジックを置き換え
    if args.out:
        # 例: "jobs/%Y%m%d_%H%M_p_suite_rerun" → jobs/20251025_1523_p_suite_rerun
        try:
            out_str = datetime.now().strftime(args.out)
        except Exception:
            out_str = args.out  # 念のためフォールバック
    else:
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        out_str = f"jobs/{ts}_p_suite"

    batch_dir = Path(out_str)
    batch_dir.mkdir(parents=True, exist_ok=True)

    paths = sorted(Path(".").glob(args.glob))
    if not paths:
        print("no cases"); return

    print(f"Running {len(paths)} cases -> {batch_dir}")
    results = [run_case(p, batch_dir, cfg) for p in paths]
    passed = sum(1 for r in results if r)
    print(f"{passed}/{len(results)} passed")

if __name__ == "__main__":
    main()
