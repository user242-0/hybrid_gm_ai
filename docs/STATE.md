# STATE.md - 現在地（最優先で更新）

> このファイルは「数週間空いても復帰できる」ための現在地メモ。
> Claude Code / Cursor / 人間が、最初に読む。


## 0. いま何を作ってる？
- プロジェクト: hybrid_gm_ai（ナラティブゲームシミュレーションエンジン）
- 直近の方向性: ネオノワール「落魄の刑事 vs 愉快犯」シナリオを軸に、会話アクションを実装して"遊べる体験"を強化

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

# Future Design Note: RC / switch_character

フルRCの処理設計について重要な方針が固まりつつある。

- フルRCは、プレイヤーと同一シーンにいる場合はローカル行動AIとして細かく動く。
- プレイヤーの視界外・別地点にいる場合は、戦略的/物語的な行動ログ生成モードで動く。
- ログ生成は switch_character 時の後付けではなく、ゲーム時間の進行に合わせて実際に生成される。
- switch_character 時には、その蓄積ログと現在状態を参照し、その時点からローカル操作へ切り替える。

詳細は `general_documents/future_goals/RC_switch_character_design_principles.md` に整理する。


## 1. すぐ動かす（入口コマンド）
- Run:
  - `python -m src.simulation`
- Test:
  - `pytest -q`
- RC（回帰/自動挙動）:
  - （例）`python -m src.simulation --rc` / `python -m src.rc_ai` など
  - 現状のRC起動方法: TODO（確定したらここに1行で）

## 2. いまの状態（3行で）

* ✅ 動くもの:

  * `python -m src.simulation` で起動し、HUDから選択→ActionPipeline経由でアクション実行できる
  * 初期stateが `cop_trickster` パック準拠（刑事/愉快犯・ロケーション・関係性タグ）で立ち上がる
  * **Action Proposal DSL v0.1**: Check A-F まで実装済み

    * A: syntax
    * B: uniqueness
    * C: requirements key validation
    * D: effects structure / path validation
    * E: safety limits
    * F: narrative tag/context consistency
    * `pytest tests/test_action_proposal_validator.py -q` は 81 passed

* ⚠️ いまの課題:

  * A-F check の reason 文言・report形式の contract がまだ固定されていない
  * proposal を HUD / ActionPipeline / Director に接続する導線はまだ未実装
  * Shadow mode の `propose_action` 導線は未実装
  * requirements の値検証や `RequirementsChecker` 連携は未実施
  * effects の world state 適用や `action_registry` 連携は未実施
  * ROがRC_AIの行動選択に影響を与える仕組み（policy_patch）が未実装

* 🎯 今やっている目的:

  * Action Proposal DSL v0.1 の validator contract を固め、次段階の Shadow mode / propose_action 導線に安全につなげる

## 3. 直近の変更（最新3つだけ）

* 2026-06-14: Session 37: Action Proposal DSL Check F 実装。`narrative_context` による source / rationale / modes / tone_tags / tags の機械的整合性チェックを追加。A-F checks がすべて実装済みになり、`pytest tests/test_action_proposal_validator.py -q` は 81 passed。
* 2026-06-14: Session 36: Action Proposal DSL Check E 実装。`safety_limits` による forbidden path / delta上限チェックを追加。`pytest tests/test_action_proposal_validator.py -q` は 62 passed。
* 2026-06-14: Session 35: Action Proposal DSL Check D 実装。`known_effect_paths` による effects構造・path検査を追加。`pytest tests/test_action_proposal_validator.py -q` は 45 passed。

## 4. 次にやること（最大3つ・小さく）

1. Action Proposal DSL validator の contract を固定する

   * `ValidationReport` の形式
   * check名
   * reason文言の安定化
   * 呼び出し側が依存してよい公開API
2. Shadow mode の `propose_action` 導線を設計する

   * proposalを検問する
   * 結果をログ保存する
   * まだHUD/ActionPipelineには接続しない
3. A-F実装完了後の共有ファイルを選定し直し、ChatGPTプロジェクト共有フォルダを更新する


## 5. ブロッカー（止まってる理由があれば）
（現状）大きなブロッカーなし。

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
   - `src/affordance_bridge.py`
   - `src/action_proposal/validator.py`

## 7. 作業ブランチ / バックアップ
- 基準（安定）: `cursor-trial/microgoal-logging`
- 作業（Session33）: `feature/session33-pack-unify-recommended-guard`
- 前作業（Session32）: `feature/session32-discovery-opportunity-separation`
- バックアップ: `backup/pre-session26-20260207`, `backup/pre-session25-20260203`
