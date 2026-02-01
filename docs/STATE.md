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
  - `python -m src.simulation` で起動し、HUDから選択→ActionPipeline経由で実行できる
  - MicroGoal/Progress/おすすめアクション表示が安定（チラつき収束）
  - simulation.py は GameContext / HUDCallbacks 分離済みで保守しやすい
- ⚠️ いまの課題:
  - 初期 game_state が Hero/Luna + 「祭壇」(ファンタジー風) のまま
  - MicroGoal の候補数が少ないモードでは「やり尽くし感」が出る（体験枯渇）
  - RC は常時動作から「明示起動」へ分離したい（run/demo/rcの整理）
- 🎯 今やっている目的:
  - ネオノワールの世界観（刑事/愉快犯/拠点/関係性）を初期stateに反映し、
    その上で「会話する」アクションMVPを入れて“遊べる体験”へ

## 3. 直近の変更（最新3つだけ）
- 2026-01-31: simulation.py をリファクタ（GameContext導入 / HUDCallbacks分離 / 未使用コード削除）
- 2026-01-13: HUD/旧GUI/CLI を共通 ActionPipeline に統合、clock二重進行を解消
- 2025-11-01: SceneGraph/ログ出力基盤の導入（データ工房の前段）

## 4. 次にやること（最大3つ・小さく）
1. game_state初期設定を「刑事/愉快犯 + ネオノワール拠点 + 関係性タグ」に変更（MVP）
2. 「会話する」アクションMVP：状況（場所/時間/天候）＋関係性タグ→テンプレ選択→ログ出力
3. MicroGoal 枯渇対策：候補を「テンプレ×スロット」で増やす or ActionSpec から自動生成する

## 5. ブロッカー（止まってる理由があれば）
- 例）RCがHUD側から自動発火していてrunと混ざっている
- 例）会話の入力/出力の置き場所（ログ形式）が未確定

（現時点）ブロッカーなし。まずは「初期state」を整える。

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
- バックアップ: `backup/pre-refactor-20260131`
- 次（Session23）: `feature/session23-conversation-microgoal`（作成予定）
