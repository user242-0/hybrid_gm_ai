# hybrid_gm_ai — フォルダ整理中の実験ゲームAI（データ工房機能搭載）

> **Status**: WIP（フォルダ構成を移行中）  
> **タグライン**: 人とAIが協働し、行動ログから“物語”と“3D向けシーン情報”を同時に生み出すハイブリッドGM。

---

## 何ができる？
- **感情ドリブンのシミュレーション**（`simulation_e.py`）  
  行動選択やログ出力が“心の色（RGB）”やTPO（場所/時間/関係/感情）に反応します。
- **二層ログ**
  - 人が読める `story.yml`（1行ビートが累積）
  - 3D/生成向けの `scene_graph.yml`（共通契約：カメラ/照明/オブジェクト/LoRA 等）
- **TPOポリシー**  
  `scene_policy.yaml` のルールで、場所/時間/関係/感情ごとにシーンを切替。

---

## クイックスタート
```bash
git clone <this-repo>
cd hybrid_gm_ai
pip install -e .
```
# 実行（推奨）
```bash
python -m src.simulation_e
```
* 挙動: 現行設定では 操作権限が Hero ↔ Luna に自動でスイッチします（デモ用の挙動）。

* 終了: ゲーム中いつでも q, quit, exit を入力すると安全に終了します。

# 互換実行（従来版）
```bash
python -m src.simulation
```
旧エントリ。simulation_utils.py を介さずに動作します（移行中のため、最新機能は simulation_e.py に集約）。

---
# 出力（jobs/）
実行ごとに jobs/<date_id>_.../ が生成されます（Git管理外を推奨）。

* scene_graph.yml … 3D/LoRA 連動の共通契約（カメラ/照明/オブジェクト/LoRA など）
* story.yml … 可読な1行ビートが蓄積
* emotion_eval.yml … salience 等の発火シグナル
* seed_ledger.csv … seed と commit の台帳（再現性のため）

.gitignore で jobs/ を除外してください（サンプルは samples/ や fixtures/ にスナップショットを保存）。

---
# 設定（config.yml 例）

```yaml
profile: lab  # prod | lab
datalab:
  emit_scene_graph: true
  emit_policy: always   # always | threshold | policy
  job_dir_pattern: "jobs/%Y%m%d_quick"
  emit_thresholds:
    salience_min: 0.60
    red_impulse_min: 0.50
```
---
# 実行フロー（概略）

1.execute_player_choice() が入力を解釈し、要件チェックを通過したらアクション実行。
1.Story/Emotion を出力し、emit_policy に応じて SceneGraph を出力。
>未定義の choice キーは無効として即リターンします（ログは吐かれません）。
1.SceneGraph には meta.commit / outputs.image.seed / meta.why_now / meta.tpo_ctx を付与。



---
# TPOポリシー
* ルール: src/datalab/registry/scene_policy.yaml

* 解決: scene_resolver が最も具体的に一致するルールを選びます（場所/時間/関係/感情）。

* 正規化: normalize_action() が日本語/英語/揺れ/軽微typoを吸収（例「攻撃する」「attack」「atack」→ attack）。
---
# テスト/Eval スニペット
```bash
# 正規化の単体テスト
pytest -k normalize_action

# SceneGraphのRound-tripスモーク
pytest -k roundtrip

# 固定評価セット（例）
python scripts/run_eval_suite.py

# A/Bのスナップショット → 選好保存
python scripts/snapshot_job.py 20251020_A
python scripts/snapshot_job.py 20251020_B
python scripts/preference_cli.py jobs/20251020_A jobs/20251020_B a "構図Aの方が良い"
```
---
# フォルダ（移行中）
```bash
hybrid_gm_ai/
  blueprints/                 # 人手テンプレ（story/emotion）
  src/
    datalab/emitters/         # story/emotion/scene_graph エミッタ
    datalab/registry/         # action正規化・TPOポリシー
    utility/                  # config/seed_ledger/git_info
    simulation_e.py           # 推奨エントリ
    simulation.py             # 従来エントリ（utils非経由）
  schemas/                    # SceneGraph 等の契約
  scripts/                    # eval/snapshot/preference
  jobs/                       # 生成物（Git管理外）
  tests/                      # 最小テスト
```
詳細は今後の整理で更新します。
