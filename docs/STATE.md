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
- ✅ 動くもの:
  - `python -m src.simulation` で起動し、HUDから選択→ActionPipeline経由でアクション実行できる
  - 初期stateが `cop_trickster` パック準拠（刑事/愉快犯・ロケーション・関係性タグ）で立ち上がる
  - **emotions_by_actor** でactor別emotion管理、set_emotion/switch_character後も値が保持される
  - 全JSONLログに `controller_id`（意思決定者）/ `actor_rc_id`（行動主体）が自動付与される
  - **RO (Reversible Operator)** Phase A+B 導入済み（助言生成 + HUD黄色テキスト表示）
  - **戦闘ログ辞書** + **resolve_exchange** が `engage_combat` に統合済み（hit/miss判定 → narrative描写 → HP処理）
  - **Affordance Bridge v2**: discovery/opportunity/label の3層分離。governed action で Director 既定候補も visible_when に従う
  - **HUD_DEBUG**: location dropdown + discovery 注入 Combobox + Inject ボタン + affordance 状態ログ
  - **Pack Single Source**: `packs/cop_trickster.yml` に modes + affordances を統一。`cop_trickster_goals.yml` は削除済み
  - **Recommended governance**: governed action が visible でなければ Recommended ボタン抑制 + on_action_select で再検証
  - **Action Proposal DSL v0.1**: syntax validator 実装済み（B-F は UNKNOWN stub）
- ⚠️ いまの課題:
  - ROがRC_AIの行動選択に影響を与える仕組み（policy_patch）が未実装
  - action_result trigger の実動作未確認（examine_scene / review_footage が action_definitions に未定義）
  - move_low_profile の移動先決定ロジック未実装
  - 既存テスト3件が Session 33 以前から壊れている（test_npc_switch, test_requirements_time_weather, test_scene_graph_roundtrip）
- 🎯 今やっている目的:
  - Session 33 完了。次回は Action Proposal DSL の B-F check 実装、または RO policy_patch

## 3. 直近の変更（最新3つだけ）
* 2026-06-07: Codex CLI trial: Action Proposal DSL validator の現状仕様テストを追加。`tests/test_action_proposal_validator.py` 作成、`pytest tests/test_action_proposal_validator.py -q` 成功。次は Check B: Uniqueness の小実装。
- 2026-04-02: Session33: Pack単一化、Recommended governance修正、check_tip二重源泉解消、Action Proposal DSL v0.1種まき
- 2026-03-30: Session32: Affordance Bridge v2 — discovery/opportunity 分離、visible_when、governed action、HUD_DEBUG 注入

## 4. 次にやること（最大3つ・小さく）
1. Action Proposal DSL の Check B: Uniqueness を実装
2. Action Proposal DSL の C-F validation check を段階的に実装
3. RO policy_patch（ROがRC_AIの行動選択に介入する仕組み）

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
