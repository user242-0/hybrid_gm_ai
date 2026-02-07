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

**最終セッション**: 2026/2/7 (Session 26)

**完了した作業** (Session 26):
- ログ識別子の最小改修: `controller_id` / `actor_rc_id` を全JSONLログ行に自動付与（logger.py 1箇所）
- RO (Reversible Operator) Phase A: playerログから助言（recommendation + why）を生成する `src/ro/ro.py` 導入
  - `config.yml` に `ro.enabled` / `ro.log_window` 追加（デフォルト OFF）
  - action_pipeline.py からプレイヤーアクション後に自動呼び出し、`game_state["ro_recommendation"]` に格納
  - RO日誌を `data/logs/ro_diary_latest.jsonl` に出力

**次回やること**:
1. RO Phase B: HUDにRO助言を表示する（recommendation表示欄の追加）
2. RO Phase C: ROがpolicy_patchを出し、RC_AIの行動選択に影響を与える仕組み
3. RC_AIの「緑優先」をキャラの心値×アクション心値による閾値フィルタに発展させる
4. talkテンプレを状況（場所/時間/天候）にも反応させて増やす

**詳細**: `docs/LOGBOOK.md` (Session 26)

## 起動方法

```bash
python -m src.simulation
```

## ブランチ

- 安定: `cursor-trial/microgoal-logging`
- 作業中: `feature/session26-simple-RO`
- バックアップ: `backup/pre-session26-20260207`, `backup/pre-session25-20260203`
