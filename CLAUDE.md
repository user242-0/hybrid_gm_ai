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
├── ui/
│   ├── hud_callbacks.py # HUD コールバック群 (HUDCallbacks クラス)
│   ├── action_pipeline.py # アクション実行パイプライン
│   └── director_hud.py  # tkinter HUD
├── utility/
│   ├── config_loader.py # config.yml 読み込み + 各種getter
│   └── llm_guard.py     # LLM呼び出しゲート制御
├── emotion_*.py         # 感情システム (RGB)
├── rc_ai.py             # RC AI (感情ベースの行動選択)
└── action_*.py          # アクション定義・実行

data/
├── director/packs/      # シナリオパック (YAML)
└── logs/                # ゲームログ

config.yml               # アプリケーション設定（RC制御, LLMゲートなど）
```

## 現在の作業状況
最初に `docs/STATE.md` と `docs/LOGBOOK.md` を必ず読んで、現状と文脈を把握してから作業すること。
作業後は `docs/STATE.md` を更新し、必要なら `docs/LOGBOOK.md` に短く記録すること。

**最終セッション**: 2026/2/4 (Session 25)

**完了した作業** (Session 25):
- ブランチ整理: main追従、不要ブランチ削除（アーカイブタグ付け）
- GUIカラーバグ修正: `emotions_by_actor` 導入でactor別emotion管理
- set_emotion/switch_character後のemotion上書き防止

**次回やること**:
1. RC_AIのアクション選択を「緑優先」から発展させ、キャラの心値×アクション心値による閾値フィルタを導入する
2. アクション心値を文脈（状況/関係性/場所/直近行動）で軽量に変動させる仕組みを試作する
3. sleep系：sleeping状態中の行動抑制と時間経過での解除を最小実装する
4. talkテンプレを状況（場所/時間/天候）にも反応させて増やす

**詳細**: `docs/LOGBOOK.md` (Session 25)

## 起動方法

```bash
python -m src.simulation
```

## ブランチ

- 安定: `cursor-trial/microgoal-logging`
- 作業中: `feature/session25-gui-color-rc-heart`
- バックアップ: `backup/pre-session25-20260203`, `backup/pre-refactor-20260131`
