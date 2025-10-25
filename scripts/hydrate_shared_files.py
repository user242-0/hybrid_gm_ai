# scripts/hydrate_shared_files.py
from pathlib import Path
import shutil

# 共有ファイル（フラットに置かれている）→ 既定の配置先
MAP = {
  "config.yml": "config.yml",
  "simulation_e.py": "src/simulation_e.py",
  "simulation_utils.py": "src/simulation_utils.py",
  "requirements_checker.py": "src/requirements_checker.py",
  "action_definitions.py": "src/action_definitions.py",
  "choice_definitions.py": "src/choice_definitions.py",
  "character_status.py": "src/character_status.py",
  "story_emitter.py": "src/datalab/emitters/story_emitter.py",
  "emotion_emitter.py": "src/datalab/emitters/emotion_emitter.py",
  "scene_graph_emitter.py": "src/datalab/emitters/scene_graph_emitter.py",
  "action_registry.py": "src/datalab/registry/action_registry.py",
  "scene_resolver.py": "src/datalab/registry/scene_resolver.py",
  "scene_policy.yaml": "src/datalab/registry/scene_policy.yaml",
  "scene_graph.py": "schemas/scene_graph.py",
  "seed_ledger.py": "src/utility/seed_ledger.py",
  "git_info.py": "src/utility/git_info.py",
  "run_eval_suite.py": "scripts/run_eval_suite.py",
  "snapshot_job.py": "scripts/snapshot_job.py",
  "preference_cli.py": "scripts/preference_cli.py",
}

def main():
    repo = Path(".").resolve()
    shared = repo  # 共有ファイルを置いた場所（同ディレクトリ想定）
    for src_name, dst_rel in MAP.items():
        src = shared / src_name
        dst = repo / dst_rel
        if not src.exists():
            print(f"skip (not found): {src_name} -> {dst_rel}")
            continue
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)
        print("placed:", src_name, "->", dst_rel)

if __name__ == "__main__":
    main()
