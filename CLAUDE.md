# hybrid_gm_ai

## プロジェクト概要

AIゲームマスター(GM)とインタラクティブなキャラクターロールプレイを融合した**ナラティブゲームシミュレーションエンジン**。

- **シナリオ**: 「落魄の刑事 vs 愉快犯」（ネオノワール風）
- **感情システム**: RGB カラー空間で表現 (R=衝動, G=自制, B=共感)
- **Director層**: マイクロゴール自動選択、モード遷移管理

## 主要ファイル

```
src/
├── simulation.py        # メインエントリーポイント
├── game_context.py      # GameContext - 全状態を保持するクラス
├── director/
│   └── director.py      # シナリオ注入、ゴール選択
├── ro/
│   └── ro.py            # RO (Reversible Operator) - 助言生成
├── ui/
│   ├── hud_callbacks.py # HUD コールバック群 (HUDCallbacks クラス)
│   ├── action_pipeline.py # アクション実行パイプライン
│   └── director_hud.py  # tkinter HUD
├── utility/
│   ├── config_loader.py # config.yml 読み込み + 各種getter
│   └── llm_guard.py     # LLM呼び出しゲート制御
├── logger.py            # JSONL ログ（controller_id / actor_rc_id 自動付与）
├── emotion_*.py         # 感情システム (RGB)
├── rc_ai.py             # RC AI (感情ベースの行動選択)
└── action_*.py          # アクション定義・実行

data/
├── director/packs/      # シナリオパック (YAML)
└── logs/                # ゲームログ (gameplay_*.jsonl, ro_diary_*.jsonl)

config.yml               # アプリケーション設定（RC制御, LLMゲート, RO設定など）
```

## 現在の作業状況
最初に `docs/STATE.md` と `docs/LOGBOOK.md` を必ず読んで、現状と文脈を把握してから作業すること。
作業後は `docs/STATE.md` を更新し、必要なら `docs/LOGBOOK.md` に短く記録すること。

**最終セッション**: 2026/3/29 (Session 31)

**完了した作業** (Session 30-31):
- Session 30: Affordance Bridge（GUIアクション結果→HUD候補追加/ラベル差し替え）
- Session 31: HUD location表示 + debug dropdown（shared state変更→HUD/GUI反映の確認基盤）

**次回やること** (Session 32: Discovery / Opportunity Separation + Visibility Rules):
1. discoveries を「手がかり」として分離し、action 候補（opportunities）と区別する
2. action ごとに可視条件・実行条件を整理する（場所限定 / どこでも可 / location更新の有無）
3. PURSUE既定action と discovery由来action の重複、場所不整合を仕様として解決する

**詳細**: `docs/LOGBOOK.md` (Session 31)

## 起動方法

```bash
python -m src.simulation
```

## ブランチ

- 安定: `cursor-trial/microgoal-logging`
- 作業中: `feature/session30-affordance-bridge`（Session 30-31）
- バックアップ: `backup/pre-session26-20260207`, `backup/pre-session25-20260203`
