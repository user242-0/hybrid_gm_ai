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
  - RCの連打・時間暴走が制御されている（decision_interval, time_budget）
  - LLM呼び出しがモード/アクション/レート制限でゲート制御されている
  - 睡眠アクション（start_sleep/sleep）が追加、RC向け短時間版とプレイヤー向け8時間版
- ⚠️ いまの課題:
  - 会話テンプレがまだ少なく、状況（場所/時間/天候）と関係性の掛け算が薄い
  - `talk` が MicroGoal/おすすめアクションとどう循環するかは未調整（会話→新micro生成など）
  - RC は常時動作から「明示起動」へ分離したい（run/demo/rcの整理）
- 🎯 今やっている目的:
  - RCの暴走を抑え、プレイヤー主導で「世界観→会話→microgoal循環」を遊べる状態を維持

## 3. 直近の変更（最新3つだけ）
- 2026-02-02: Session24: RC制御強化（switch封印, LLMゲート, throttle, sleep分離）
- 2026-02-01: Session23: cop_trickster初期state + talkアクション + 日替わりリセット + Choice自動生成
- 2026-01-31: Session22: simulation.py をリファクタ（GameContext導入 / HUDCallbacks分離）

## 4. 次にやること（最大3つ・小さく）
1. 起動テスト: RCのthrottle動作確認（連打しない、input_pending中に時間が暴走しない）
2. `talk` を状況（場所/時間/天候）にも反応させてテンプレを増やす（最低でも 6〜12 本）
3. sleeping状態の自動進行（world_tickでの小刻み処理）を実装

## 5. ブロッカー（止まってる理由があれば）
（現状）大きなブロッカーなし。Session24の変更が安定しているか動作確認が必要。

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
- 作業（Session24）: `feature/session24-rc-throttle-llm-gating`
- バックアップ: `backup/pre-refactor-20260131`
