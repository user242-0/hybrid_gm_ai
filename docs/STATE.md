# STATE.md - 現在地（最優先で更新）

> このファイルは「数週間空いても復帰できる」ための現在地メモ。
> Claude Code / Cursor / 人間が、最初に読む。


## 0. いま何を作ってる？
- プロジェクト: hybrid_gm_ai（ナラティブゲームシミュレーションエンジン）
- 直近の方向性: ネオノワール「落魄の刑事 vs 愉快犯」シナリオを軸に、会話アクションを実装して“遊べる体験”を強化

- RO（Reversible Operator）：プレイヤー側の常駐オペレーター層。ログ編集→方針（優先度/制約/評価）パッチ→RC_AI誘導を担う。
  - Reversibleとは、以下の立場・役割の可逆性を指す。
  - 1.指し手の可逆性（Human↔RO）
    - 通常は RO→RC が自然だが、状況によって プレイヤーがROから指示を受けて動く（RO→プレイヤー→RC）順も成立する。
  - 2.視点・没入の可逆性（メタ観察↔物語没入）
    - プレイヤーがメタ観察（ログ収集／優先度決定／状況把握）を行うモード
    - ROが感情・物語に没入し、RC_AI寄りの機能（局所判断）を担うモード
    - → 普段と逆が成立する＝Reversible
  - 3.ルール提案・承認の可逆性（提案者↔承認者）
    - ルール提案→承認のような特殊アクションにおいて、立場を逆にできる（RO提案／人間承認 ⇄ 人間提案／RO承認）。
  - 4.コーチングの可逆性（助言者↔育成対象）
    - 通常はROがアドバイスを与える側だが、人間がROをコーチングし育成することもある。

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
- 2026-02-04: Session25続: emotion上書き経路の根治（delta適用前にSoTロード、world["emotion"]常時同期）
- 2026-02-04: Session25: GUIカラーバグ修正（emotions_by_actor導入、set_emotion/switch_character後の上書き防止）
- 2026-02-02: Session24: RC制御強化（switch封印, LLMゲート, throttle, sleep分離）

## 4. 次にやること（最大3つ・小さく）
1. RC_AIの「緑優先」をキャラの心値×アクション心値による閾値フィルタに発展させる
2. `talk` を状況（場所/時間/天候）にも反応させてテンプレを増やす（最低でも 6〜12 本）
3. sleeping状態中の行動抑制と時間経過での解除を最小実装する

## 5. ブロッカー（止まってる理由があれば）
（現状）大きなブロッカーなし。emotion上書き根治済み。手動DoD確認を推奨。

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
