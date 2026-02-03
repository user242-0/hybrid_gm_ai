# STATE.md - 現在地（最優先で更新）

> このファイルは「数週間空いても復帰できる」ための現在地メモ。
> Claude Code / Cursor / 人間が、最初に読む。


## 0. いま何を作ってる？
- プロジェクト: hybrid_gm_ai（ナラティブゲームシミュレーションエンジン）
- 直近の方向性: ネオノワール「落魄の刑事 vs 愉快犯」シナリオを軸に、会話アクションを実装して“遊べる体験”を強化

## 1. すぐ動かす（入口コマンド）
- Run:
  - `python -m src.simulation`
- Test:
  - `pytest -q`  （※まだ無い/別コマンドならここを更新）
- RC（回帰/自動挙動）:
  - （例）`python -m src.simulation --rc` / `python -m src.rc_ai` など
  - 現状のRC起動方法: TODO（確定したらここに1行で）

## 2. いまの状態（3行で）
- ✅ 動くもの:
  - `python -m src.simulation` で起動し、HUDから選択→ActionPipeline経由でアクション実行できる
  - 初期stateが `cop_trickster` パック準拠（刑事/愉快犯・ロケーション・関係性タグ）で立ち上がる
  - **emotions_by_actor** でactor別emotion管理、set_emotion/switch_character後も値が保持される
  - RCの連打・時間暴走が制御されている（decision_interval, time_budget）
  - LLM呼び出しがモード/アクション/レート制限でゲート制御されている
- ⚠️ いまの課題:
  - 会話テンプレがまだ少なく、状況（場所/時間/天候）と関係性の掛け算が薄い
  - `talk` が MicroGoal/おすすめアクションとどう循環するかは未調整（会話→新micro生成など）
  - RC は常時動作から「明示起動」へ分離したい（run/demo/rcの整理）
- 🎯 今やっている目的:
  - RCの暴走を抑え、プレイヤー主導で「世界観→会話→microgoal循環」を遊べる状態を維持

## 3. 直近の変更（最新3つだけ）
- 2026-02-04: Session25: GUIカラーバグ修正（emotions_by_actor導入、set_emotion/switch_character後の上書き防止）
- 2026-02-02: Session24: RC制御強化（switch封印, LLMゲート, throttle, sleep分離）
- 2026-02-01: Session23: cop_trickster初期state + talkアクション + 日替わりリセット + Choice自動生成

## 4. 次にやること（最大3つ・小さく）
1. RC_AIの「緑優先」をキャラの心値×アクション心値による閾値フィルタに発展させる
2. `talk` を状況（場所/時間/天候）にも反応させてテンプレを増やす（最低でも 6〜12 本）
3. sleeping状態中の行動抑制と時間経過での解除を最小実装する

## 5. ブロッカー（止まってる理由があれば）
（現状）大きなブロッカーなし。Session25のemotion修正が安定しているか動作確認を推奨。

## 6. 参考（読む順番）
1. `CLAUDE.md`（前提とルール）
2. `docs/STATE.md`（このファイル）
3. `docs/LOGBOOK.md`（日誌・気づき）
4. 主要ファイル:
   - `src/simulation.py`
   - `src/game_context.py`
   - `src/ui/action_pipeline.py`
   - `src/ui/hud_callbacks.py`
   - `src/director/director.py`

## 7. 作業ブランチ / バックアップ
- 基準（安定）: `cursor-trial/microgoal-logging`
- 作業（Session25）: `feature/session25-gui-color-rc-heart`
- バックアップ: `backup/pre-session25-20260203`, `backup/pre-refactor-20260131`
