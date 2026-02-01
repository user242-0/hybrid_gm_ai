# hybrid_gm_ai

## プロジェクト概要

AIゲームマスター(GM)とインタラクティブなキャラクターロールプレイを融合した**ナラティブゲームシミュレーションエンジン**。

- **シナリオ**: 「落魄の刑事 vs 愉快犯」（ネオノワール風）
- **感情システム**: RGB カラー空間で表現 (R=衝動, G=自制, B=共感)
- **Director層**: マイクロゴール自動選択、モード遷移管理

## 主要ファイル

```
src/
├── simulation.py        # メインエントリーポイント (535行)
├── game_context.py      # GameContext - 全状態を保持するクラス
├── director/
│   └── director.py      # シナリオ注入、ゴール選択
├── ui/
│   ├── hud_callbacks.py # HUD コールバック群 (HUDCallbacks クラス)
│   ├── action_pipeline.py # アクション実行パイプライン
│   └── director_hud.py  # tkinter HUD
├── emotion_*.py         # 感情システム (RGB)
├── rc_ai.py             # RC AI (感情ベースの行動選択)
└── action_*.py          # アクション定義・実行

data/
├── director/packs/      # シナリオパック (YAML)
└── logs/                # ゲームログ

config.yml               # アプリケーション設定
```

## 現在の作業状況
最初に `docs/STATE.md` と `docs/LOGBOOK.md` を必ず読んで、現状と文脈を把握してから作業すること。
作業後は `docs/STATE.md` を更新し、必要なら `docs/LOGBOOK.md` に短く記録すること。

**最終セッション**: 2026/1/31 (Session 22)

**完了した作業**:
- simulation.py リファクタリング (860行 → 535行, -38%)
- GameContext クラス導入
- HUDCallbacks 分離
- 未使用コード削除

**次回やること**:
1. game_state 初期設定の修正 (Hero/Luna → 刑事/愉快犯)
2. 「会話する」アクション実装 (状況・関係性ベースのフレーバーテキスト)

**詳細**: `general_documents/diary/session22_summary_2026_1_31.txt`

## 起動方法

```bash
python -m src.simulation
```

## ブランチ

- 作業中: `cursor-trial/microgoal-logging`
- バックアップ: `backup/pre-refactor-20260131`
