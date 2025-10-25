# scripts/run_eval_suite.py
import argparse, importlib, sys, yaml, shutil
from pathlib import Path
from datetime import datetime

# ルートを import パスに追加
sys.path.append(str(Path(".").resolve()))

# 基本モジュール
from src.character_status import CharacterStatus
from src.action_definitions import actions
from src.datalab.emitters.emotion_emitter import summarize_why_now
from src.utility.config_loader import get_cfg
import src.simulation_utils as sim  # ← SCENE_JOB_DIR を差し替えるため module 参照

def build_state_from_ctx(ctx: dict):
    # アクター集合（最小）
    hero = CharacterStatus("Hero", faction="player", is_rc=True, is_npc=False)
    luna = CharacterStatus("Luna", faction="player", is_rc=True, is_npc=True)

    party = {hero.name: hero, luna.name: luna}

    gs = {
        "active_char": hero,
        "party": party,
        "current_location": ctx.get("current_location", "どこか"),
        "time_of_day": ctx.get("time_of_day", "night"),
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
    if rel:
        target = party.get(rel.get("target") or gs["current_target"])
        observer = rel.get("from_actor", "Hero")
        if target:
            for lab in rel.get("labels", []):
                target.add_label_from(observer, lab)

    return hero, gs

def expect_scene_graph(job_dir: Path, cfg: dict):
    """
    emit_policy=always → 期待=あり
    threshold         → summarize_why_now(signals, thresholds)['ok'] なら あり
    """
    eva = yaml.safe_load((job_dir / "emotion_eval.yml").read_text(encoding="utf-8"))
    signals = eva.get("signals", {})
    th = cfg.get("datalab", {}).get("emit_thresholds", {})
    policy = cfg.get("datalab", {}).get("emit_policy", "always")
    ok = True if policy == "always" else summarize_why_now(signals, th)["ok"]
    return ok

def validate_outputs(job_dir: Path, cfg: dict, expect: dict):
    ok = True
    # 1) story.yml
    if not (job_dir / "story.yml").exists():
        print("✗ story.yml not found")
        ok = False
    # 2) emotion_eval.yml
    emo_p = job_dir / "emotion_eval.yml"
    if not emo_p.exists():
        print("✗ emotion_eval.yml not found"); ok = False
    else:
        eva = yaml.safe_load(emo_p.read_text(encoding="utf-8"))
        sal = eva.get("signals", {}).get("salience")
        exp_sal = expect.get("emotion.salience")
        if exp_sal is not None and abs(float(sal) - float(exp_sal)) > 1e-3:
            print(f"✗ salience mismatch: {sal} vs {exp_sal}")
            ok = False
    # 3) scene_graph.yml 期待
    sg_p = job_dir / "scene_graph.yml"
    want_emit = expect_scene_graph(job_dir, cfg) if expect.get("scene_graph") in (None, "auto") \
                else (expect.get("scene_graph") in ("emit", "present"))
    has_sg = sg_p.exists()
    if want_emit != has_sg:
        print(f"✗ scene_graph expectation mismatch: want={want_emit}, has={has_sg}")
        ok = False
    # 4) seed_ledger.csv
    if not (job_dir / "seed_ledger.csv").exists():
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

    # 検証
    ok = validate_outputs(job_dir, cfg, expect)
    print(("✓" if ok else "✗"), path.name, "->", job_dir)
    return ok

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--glob", default="data/eval_set/cases/p2_*.yml")
    ap.add_argument("--out", default=None, help="batch dir (default auto)")
    args = ap.parse_args()

    cfg = get_cfg()  # emit_policy / thresholds / job_dir_pattern を参照 :contentReference[oaicite:20]{index=20}

    # ★ out の決定ロジックを置き換え
    if args.out:
        # 例: "jobs/%Y%m%d_%H%M_p2_suite_rerun" → jobs/20251025_1523_p2_suite_rerun
        try:
            out_str = datetime.now().strftime(args.out)
        except Exception:
            out_str = args.out  # 念のためフォールバック
    else:
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        out_str = f"jobs/{ts}_p2_suite"

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
