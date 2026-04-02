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

**最終セッション**: 2026/4/2 (Session 33)

**完了した作業** (Session 30-33):
- Session 30: Affordance Bridge（GUIアクション結果→HUD候補追加/ラベル差し替え）
- Session 31: HUD location表示 + debug dropdown（shared state変更→HUD/GUI反映の確認基盤）
- Session 32: Affordance Bridge v2 — discovery/opportunity 分離、visible_when、governed action、HUD_DEBUG 注入
- Session 33: Pack単一化（goals.yml削除）、Recommended governance修正、check_tip二重源泉解消、Action Proposal DSL v0.1

**次回やること** (Session 34):
1. Action Proposal DSL の B-F validation check を段階的に実装
2. RO policy_patch（ROがRC_AIの行動選択に介入する仕組み）
3. action_result trigger 用の examine_scene / review_footage を action_definitions に追加

**詳細**: `docs/LOGBOOK.md` (Session 33)

## 起動方法

```bash
python -m src.simulation
```

## ブランチ

- 安定: `cursor-trial/microgoal-logging`
- 作業中: `feature/session33-pack-unify-recommended-guard`（Session 33）
- 前作業: `feature/session32-discovery-opportunity-separation`（Session 32）
- バックアップ: `backup/pre-session26-20260207`, `backup/pre-session25-20260203`
