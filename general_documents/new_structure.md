# プロジェクト構成（共有ファイル向けガイド）

> 目的：SceneGraphの評価運用（A/B→preference→aggregate→apply→run_eval）を再現可能にし、セッション19以降の拡張（Δt, (x,y), 文脈評価, RC選択）に備える。

## ルート構成

```
.
├─ README.md                         # セッション18ワークフローの最新版（1ページ運用メモ）
├─ chatgpt_shared_manifest.yml       # 共有パックのマニフェスト
├─ config.yml
├─ scripts/                          # 運用スクリプト（評価/スナップショット/集計等）
│   ├─ run_eval_suite.py
│   ├─ snapshot_job.py
│   ├─ preference_cli.py
│   ├─ sg_to_prompt.py
│   ├─ policy_linter.py
│   ├─ apply_priority_suggestions.py
│   ├─ ab_pipeline.py
│   ├─ prefs_aggregate.py
│   ├─ render_with_diffusers.py
│   ├─ list_referenced_jobs.py
│   ├─ gc_jobs.py
│   └─ repair_prefs_paths.py
├─ src/                              # 実行系（セッション18では主に既存を使用）
│   ├─ action_definitions.py
│   ├─ choice_definitions.py
│   ├─ character_status.py
│   ├─ story_emitter.py
│   ├─ emotion_emitter.py
│   ├─ scene_graph_emitter.py
│   ├─ action_registry.py
│   ├─ scene_resolver.py
│   ├─ config_loader.py
│   ├─ seed_ledger.py
│   ├─ git_info.py
│   ├─ scene_graph.py
│   └─ datalab/registry/
│        └─ scene_policy.yaml        # policy本体（priority反映済み）
├─ data/
│   └─ eval_set/
│        └─ cases/
│             └─ p2_*.yml           # 固定評価ケース（6件）
├─ jobs/                             # 生成物（Git管理外・共有しない）
│   ├─ snapshots/
│   └─ prefs/
└─ docs/
    ├─ README_session18_workflow.md  # 任意：アーカイブとして残す場合
    ├─ new_structure.md              # 本ファイル（このガイド）
    └─ diary/
        └─ session18_summary_2025-11-01.txt  # ← 後で追加（任意）
```

## 運用の約束
- **生成物は jobs/ に集約**（共有しない）。A/B比較は `jobs/snapshots/<label>/<run-id>/<case>/…`。
- **preference は jobs/prefs/** に保存。集計→`priority_suggestions.yaml`→policy反映。
- **policy の priority は “条件一致後の加点”**。TPOをねじ曲げない（when を満たさないルールは選ばれない）。
- **scripts/** は相互に相対参照しているため、**パスを変えない**。
- **manifest を更新**：差分共有のたびに `chatgpt_shared_manifest.yml` を更新。

## セッション19で増える予定（予告）
- `src/game_state.py`：Δt・(x,y)・facing・speed
- `src/context_eval.py`：文脈評価（色/gating/係数）
- `src/rc_select.py`：有効スコア計算と選択（softmax/argmax）
- `data/eval_set/cases/p3_*.yml`：文脈/位置/時間の差分ケース
