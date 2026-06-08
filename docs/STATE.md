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
  * **Action Proposal DSL v0.1**: Check A Syntax / Check B Uniqueness / Check C Requirements まで実装済み

    * B: `active_action_ids` 指定時に action id 重複を検出
    * C: `known_requirement_keys` 指定時に requirements key の妥当性を検査
    * D-F は UNKNOWN stub のまま

* ⚠️ いまの課題:

  * Action Proposal DSL の Check D-F が未実装
  * requirements の値検証や `RequirementsChecker` 連携は未実施
  * proposal を HUD / ActionPipeline / Director に接続する導線はまだ未実装
  * ROがRC_AIの行動選択に影響を与える仕組み（policy_patch）が未実装
  * action_result trigger の実動作未確認（examine_scene / review_footage が action_definitions に未定義）
  * move_low_profile の移動先決定ロジック未実装

* 🎯 今やっている目的:

  * Action Proposal DSL の検問を A→F の順に小さく実装し、将来的な「アクション提案アクション」の安全な入口を作る

## 3. 直近の変更（最新3つだけ）

* 2026-06-08: Session 34: Action Proposal DSL Check B / C 実装。`active_action_ids` による重複検査、`known_requirement_keys` による requirements key 検査を追加。`pytest tests/test_action_proposal_validator.py -q` は 26 passed。
* 2026-06-07: Codex CLI trial: Action Proposal DSL validator の現状仕様テストを追加。`tests/test_action_proposal_validator.py` 作成、`pytest tests/test_action_proposal_validator.py -q` 成功。
* 2026-04-02: Session33: Pack単一化、Recommended governance修正、check_tip二重源泉解消、Action Proposal DSL v0.1種まき

## 4. 次にやること（最大3つ・小さく）

1. Action Proposal DSL の Check D: Effects を「構造だけ検証する」粒度で実装
2. Check E: Safety / Check F: Narrative を段階的に実装
3. Shadow mode の `propose_action` 導線を作り、proposal を検問してログ保存できるようにする


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
