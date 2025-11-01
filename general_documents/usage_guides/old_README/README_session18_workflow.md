# ゲームマスターAI — セッション18 ワークフロー（1ページ版）

> 目的：**SceneGraph を安定生成 → A/B で“絵”を比較 → 好みを `scene_policy.yaml` に還元**する、再現可能な運用を確立する。  
> 生成物は **`jobs/`** に集約。固定評価は **6/6 PASS** を常にキープ。

---

## ディレクトリ規約（生成物は jobs/ に集約）

```
data/eval_set/cases/     # 固定評価ケース（*.yml）
scripts/                 # ツール群（run_eval_suite / snapshot_job / sg_to_prompt / …）
jobs/                    # 生成物（Git管理外）
  snapshots/             # A/B の保管庫（画像・SG・メタ）
    A/<run-id>/<case>/...
    B/<run-id>/<case>/...
  prefs/                 # 選好ログ（preference_*.yml / priority_suggestions.yaml）
  <timestamp>_p2_suite*  # 一時ジョブ（後で掃除OK：GC参照）
```

---

## 最短ワークフロー（A/B → preference → aggregate → apply → run_eval）

### 0) 依存（初回だけ）
- **Diffusers（ローカル生成）**  
  - CPU: `pip install --index-url https://download.pytorch.org/whl/cpu torch`  
  - 共通: `pip install diffusers transformers accelerate safetensors`

### 1) 固定評価（6/6を確認）
```bash
python scripts/run_eval_suite.py --glob "data/eval_set/cases/p2_*.yml" \
  --out "jobs/%Y%m%d_%H%M_p2_suite"     # --out は strftime 展開可
```

### 2) A/B を一気に作る（再エミット→スナップショット→プロンプト→画像）
```bash
python scripts/ab_pipeline.py \
  --case-a data/eval_set/cases/<Aケース>.yml \
  --case-b data/eval_set/cases/<Bケース>.yml \
  --label-a A --label-b B --style realistic
# 結果: jobs/snapshots/A/<run-id>/*/render/preview.png ほか
```
> **ポイント**：SG→プロンプトでは `meta.tpo_ctx / camera / lighting` を文面化。  
> CLIP の 77トークン制限を越えないよう、重要語は先頭・装飾語は短縮（自動トリミングを使っても可）。

### 3) 好みを保存（preference）
```bash
python scripts/preference_cli.py \
  "jobs/snapshots/A/<run-id>" "jobs/snapshots/B/<run-id>" \
  <a|b|tie> "短いメモ（例：『夜のリムライトが良い』）"
```
- 保存先：`jobs/prefs/preference_*.yml`（A/B のルートパスを保持）

### 4) 集計 → 優先度提案 → 反映
```bash
python scripts/prefs_aggregate.py                  # → jobs/prefs/priority_suggestions.yaml
python scripts/apply_priority_suggestions.py       # → scene_policy.yaml に priority を付与
python scripts/policy_linter.py                    # 語彙/キーの静的チェック
```
- `priority` は **“条件が一致した後の加点”**。`when.time: night` を満たさない限り **night ルールは選ばれない**（時空はねじれない）。

### 5) 回帰（固定評価を再確認）
```bash
python scripts/run_eval_suite.py --glob "data/eval_set/cases/p2_*.yml"
# → 6/6 PASS が維持されていること
```

---

## Scene Policy の書き方（最小の型）

```yaml
defaults:
  theme: ""
  background: ""
  camera:   { text: "" }
  lighting: { text: "" }

rules:
  - when: { action: ["swing_sword","攻撃する"], location: "洞窟", time: "night" }
    theme: "暗い洞窟での剣の一閃"
    background: "dark cave interior"
    camera:   { shot: "close", lens: "35mm", angle: "low" }
    lighting: { text: "torch warm bounce, cool rim" }
    priority: 1   # ← prefs 集計の結果をここに足す（候補内の“ひと押し”）
```

---

## 片付け（GC）

- **残す**：`jobs/snapshots/**`, `jobs/prefs/**`（preference がスナップショットへのパスを参照するため）  
- **消せる候補**：古い `jobs/<timestamp>_*`（ただし prefs が参照していないもの）  
- 補助ツール：  
  - `python scripts/list_referenced_jobs.py`（pref が参照するパス一覧）  
  - `python scripts/gc_jobs.py`（未参照ジョブを削除：初回は dry-run で確認）

---

## トラブルシュート

- **A/B のプロンプトが同じ** → policy が汎用に吸われた / SG→プロンプトで TPO 未反映。  
  → TPO ルールを増やす／`sg_to_prompt.py` を最新版に。  
- **77トークン超過** → 重要語を先頭、装飾語を短縮。  
- **スナップショットのパスが深い** → `--run-id` で整理（`A/<run-id>/…` 形式）。

---

## 10分スモークテスト（最短）

```bash
# 1) スイート実行 → 2) A/B 一括生成 → 3) 好み保存 → 4) 集計/反映 → 5) 回帰
python scripts/run_eval_suite.py --glob "data/eval_set/cases/p2_*.yml" --out "jobs/%Y%m%d_%H%M_p2_suite"
python scripts/ab_pipeline.py --case-a data/eval_set/cases/p2_04_*.yml --case-b data/eval_set/cases/p2_06_*.yml --label-a A --label-b B
python scripts/preference_cli.py jobs/snapshots/A/<run-id> jobs/snapshots/B/<run-id> b "夕景の逆光が良い"
python scripts/prefs_aggregate.py && python scripts/apply_priority_suggestions.py && python scripts/policy_linter.py
python scripts/run_eval_suite.py --glob "data/eval_set/cases/p2_*.yml"
```

---

## 本セッションの到達点

- **固定評価 6/6 PASS** を再現可能に。  
- **A/B → preference → aggregate → policy 反映**のループを確立。  
- SceneGraph は `meta.tpo_ctx / camera / lighting / why_now / commit / profile` と `outputs.image.seed` を記録（再現性）。  
- 生成物の保存先は **jobs/** に統一（snapshots, prefs）。
