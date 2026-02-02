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

**最終セッション**: 2026/2/2 (Session 24)

**完了した作業** (Session 24):
- RC制御強化: `switch_character` 封印、連打・時間暴走制御（3レバー）
- LLMゲート: mode/allow_actions/rate_limit による呼び出し制御
- 睡眠アクション: `start_sleep`(RC用) / `sleep`(プレイヤー用8h)

**次回やること**:
1. GUIコマンド色の不具合（真っ暗化・急激な変化）を再現ログ付きで特定し、RGB clamp＋色計算の集約（必要ならスムージング）で安定化する
2. RC_AIのアクション選択を「緑優先」から発展させ、キャラの心値×アクション心値による閾値フィルタ（不一致な行動は候補から落とす）を導入する
3. アクション心値を固定値だけでなく文脈（状況/関係性/場所/直近行動）で軽量に変動させる仕組み（重くならないルールベース）を試作する
4. 「ここぞ」という時だけLLMを選択ロジックに混ぜられるよう、ログ/条件トリガでLLM判定を有効化する運用（rate limit前提）を設計する
5. sleep系：`start_sleep`をプレイヤーも実行可能にし、sleeping状態中の行動抑制と時間経過での解除（他RCの暗躍は継続）を最小実装する

**詳細**: `docs/LOGBOOK.md` (Session 24)

## 起動方法

```bash
python -m src.simulation
```

## ブランチ

- 安定: `cursor-trial/microgoal-logging`
- 作業中: `feature/session24-rc-throttle-llm-gating`
- バックアップ: `backup/pre-refactor-20260131`
