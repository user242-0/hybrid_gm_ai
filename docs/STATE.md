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
  - `talk` アクションが追加され、関係性タグに応じた会話テンプレがログに出る（`last_dialogue` もstateに保持）
  - 日が変わると MicroGoal の消費履歴がリセットされる（枯渇対策のMVP）
  - Choiceが action_definitions から自動生成され、`ui_visible=True` のもののみ表示される
  - `action_key`（英語内部ID）と `label`（日本語表示名）が分離され、pack差し替えに対応しやすい構造
- ⚠️ いまの課題:
  - 会話テンプレがまだ少なく、状況（場所/時間/天候）と関係性の掛け算が薄い
  - `talk` が MicroGoal/おすすめアクションとどう循環するかは未調整（会話→新micro生成など）
  - RC は常時動作から「明示起動」へ分離したい（run/demo/rcの整理）
- 🎯 今やっている目的:
  - 「世界観の初期化」→「会話」→「microgoal循環」を最小ループで成立させ、遊びとしての手触りを上げる

## 3. 直近の変更（最新3つだけ）
- 2026-02-01: Session23: cop_trickster初期state + talkアクション + 日替わりリセット + Choice自動生成（64adfe9〜b1db9e8）
- 2026-01-31: Session22: simulation.py をリファクタ（GameContext導入 / HUDCallbacks分離 / 未使用コード削除）
- 2026-01-13: Session21: HUD/旧GUI/CLI を共通 ActionPipeline に統合、clock二重進行を解消

## 4. 次にやること（最大3つ・小さく）
1. `talk` を状況（場所/時間/天候）にも反応させてテンプレを増やす（最低でも 6〜12 本）
2. 会話を MicroGoal と循環させる（例: 会話ログ→新micro候補、または talk をおすすめに出やすくする）
3. RCを “常時動作” から “明示起動” へ分離する（run/demo/rcの整理）

## 5. ブロッカー（止まってる理由があれば）
- 例）RCがHUD側から自動発火していてrunと混ざっている
- 例）会話の入力/出力の置き場所（ログ形式）が未確定

（現状）大きなブロッカーなし。まずは起動テストで `talk` と日替わりリセットを確認。

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
- 作業（Session23）: `feature/session23-conversation-microgoal`
- バックアップ: `backup/pre-refactor-20260131`
