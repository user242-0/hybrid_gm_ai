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

### Design Note: actor別 HUD Action Proposal

AI提案HUDは、将来的に「現在操作中RC」の提案だけを表示する方針。

- 操作RC = 刑事 → 刑事向けAI提案のみ表示
- 操作RC = 愉快犯 → 愉快犯向けAI提案のみ表示
- 非操作中RCの提案は通常HUDに混ぜず、必要なら Debug / GM View / RC Activity Panel に分離する

次工程では、Action Proposal / Shadow / Advisory / Display item に `actor_id` を持たせ、
provider側で `current active_char` に一致する提案だけをHUDへ返すことを検討する。

この方針により、AI提案の実行可能化へ進む前に、
「誰が実行する提案なのか」を明確にできる。


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

  * `python -m src.simulation` で起動し、HUDから選択→ActionPipeline経由で既存アクションを実行できる
  * 初期stateが `cop_trickster` パック準拠（刑事/愉快犯・ロケーション・関係性タグ）で立ち上がる
  * **Action Proposal DSL v0.1**: A-F validator / Shadow / Advisory / Feed / Provider / HUD read-only表示 まで実装済み

    * A: Syntax
    * B: Uniqueness
    * C: Requirements
    * D: Effects
    * E: Safety
    * F: Narrative
    * `ValidationReport` contract 固定済み
    * `reason_codes` / `to_dict()` 実装済み
    * Shadow log: `jobs/%Y%m%d_quick/action_proposal_shadow.jsonl`
    * HUDに「AI提案」欄を表示できる
    * ただし、現時点では表示のみ。クリック不可・実行不可・Actions listboxには混ぜない

* ⚠️ いまの課題:

  * HUDのAI提案欄は read-only 表示まで。提案をプレイヤーが採用・実行する導線は未実装
  * shadow log は手動またはデモ経由で作る段階。ゲーム本体から自然に proposal を生成する導線は未実装
  * `jobs/%Y%m%d_quick/action_proposal_shadow.jsonl` はプレイセッション監査ログとして扱う必要が出てきた
  * requirements の値検証や `RequirementsChecker` 連携は未実施
  * effects の world state 適用や `action_registry` 連携は未実施
  * ROがRC_AIの行動選択に影響を与える仕組み（policy_patch）は未実装
  * `pytest -q` は既存と思われる3件が失敗中

    * `tests/test_npc_switch.py::test_npc_switch`
    * `tests/test_requirements_time_weather.py::test_statue_actions_are_gated_by_time_and_weather`
    * `tests/test_scene_graph_roundtrip.py::test_scene_graph_roundtrip_minimal`

* 🎯 今やっている目的:

  * Action Proposal DSL v0.1 を、実行系へ直結させる前に「提案→検問→ログ→表示」まで安全に通す
  * 次は、HUDに見えているAI提案を、どうやって自然に生成するか、またはプレイヤーがどう採用するかを段階的に設計する

## 3. 直近の変更（最新3つだけ）

* 2026-06-15: Session 44: HUD Advisory read-only表示を実装。`advisory_provider.get_advisory_display_items(limit=3)` をHUDCallbacksからread-onlyに呼び、Director HUDに「AI提案」欄を追加。Actions listboxには混ぜず、クリック不可・実行不可。手動shadow logによるHUD表示を目視確認し、日本語文字化けはテストデータ作成時のPowerShell文字コード問題として回避済み。
* 2026-06-15: Session 41-43: Advisory Adapter / Advisory Feed / Read-only Providerを実装。shadow recordからPASS済み提案だけをadvisory item化し、HUDが読むdisplay feedに整形し、provider経由で安全にitemsを取得できるようにした。
* 2026-06-15: Session 38-40: Validator contract / Shadow Adapter / Shadow Log Contractを実装。A-F checkの順序・`reason_codes`・`to_dict()`を固定し、proposalを検問して `jobs/%Y%m%d_quick/action_proposal_shadow.jsonl` にJSONL保存できる土台を作った。

## 4. 次にやること（最大3つ・小さく）

1. Action Proposal Demo Producer / Seed を作る

   * 手動PowerShellではなく、デモ関数またはdebug操作で proposal を1件生成
   * validator A-Fに通す
   * shadow logへ保存
   * HUDのAI提案欄に表示されるところまで確認
   * まだActionPipelineには接続しない

2. HUD AI提案欄の見た目を軽く整える

   * 長文detailのwrap
   * RO表示との間隔
   * 「AI提案なし」時の表示方針
   * ウィンドウ高さ・minsize調整

3. main統合前チェックの準備

   * targeted tests は通っていることを確認
   * `pytest -q` の既存3失敗を別件として整理
   * `jobs/` の扱いを「一時生成物」と「プレイセッション監査ログ」に分ける


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
