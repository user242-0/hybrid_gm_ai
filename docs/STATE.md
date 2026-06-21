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

### Session 49-B: 60秒デモ前のMicroGoal/Actions整合ポリッシュ

* RC別MicroGoalに `action_id` を保存し、旧saveはtext / modeから後方互換で補完する。
* active actor + ActorMode + discovery gating適用後のHUD Actionsに対応Actionが存在する場合だけ現在MicroGoalを表示する。
* 未解放・条件未達の候補は削除せず、現在選べない場合は `MicroGoal(<actor>): 未設定` と表示する。
* switch_character / ActorMode変更 / save-load後も同じ判定を行い、AI提案HUDのactor_idフィルタ/read-onlyは維持する。
* TPOコンテンツ縦切り、RC別location/discovery、ROのRC別実装は後続タスク。

### Session 49: RC別MicroGoal

* 60秒YouTubeデモの優先実装として、HUD MicroGoalをactive actor + ActorModeで切り替える。
* `director_world["actor_micro_goals"]` にRCごとのtext / mode / baseline / recent IDsを保存し、刑事と愉快犯が互いのMicroGoalを上書きしない。
* active actor不明時は既存のグローバルMicroGoal、ActorMode未設定時は `Director.mode` にフォールバックする。
* switch_character、ActorMode変更、save/load後もactive actor由来のMicroGoal表示を維持する。
* AI提案HUDのactor_idフィルタ/read-onlyは維持。TPOコンテンツ縦切りとROのRC別実装は後続タスク。

### Session 48-C: ActorMode HUD verification

* Director HUDで `DirectorMode` と `ActorMode(active actor)` を別表示する。
* `DirectorMode` dropdownは世界全体modeを変更し、MicroGoal / Recommended / AI stepに使う。
* `ActorMode` はactive actorのHUD Actions生成に使い、`HUD_DEBUG=1` のときだけdropdownから変更できる。
* ActorMode変更時は `director_world["actor_modes"][active_actor.name]` を更新し、HUD cache rev更新後にActionsを再描画する。
* actor_modes未設定actorは従来通り `Director.mode` へフォールバックする。
* RC別MicroGoalの本格実装は後続タスクのまま。

### Session 48: ActorMode by actor_id

* `Director.mode` は世界全体・演出焦点・MicroGoal/Recommended/AI step の DirectorMode として維持する。
* RCごとの現在行動方針は `director_world["actor_modes"]` に保存し、packの `world_defaults.actor_modes` から初期化する。
* HUD Actions生成時だけ `active_char.name` のActorModeを優先し、未設定・未知actorは `Director.mode` へフォールバックする。
* mode dropdownは引き続きグローバル `Director.mode` を操作する。active actorのActorMode編集UIは後続タスクとする。
* RC別MicroGoalとTPOコンテンツ縦切りは後続タスクとして残す。

### Session 47-B: 愉快犯用の基本HUDアクション

* `cop_trickster` の愉快犯FLEEに、逃走・攪乱・潜伏・観察系の基本アクション5件を追加。
* `plant_false_trace` は demo_seed と同じcanonical IDを使用するが、AI提案HUDは引き続きread-onlyで、採用・実行導線には接続していない。
* RC別MicroGoalの本格設計は未着手。現状はactor別HUD Actionsの元になるmode割当を最小構成で利用している。

### Session 45 完了: actor_id付き AI提案HUD / Demo Seed

* 2026-06-18: Session 45: Action Proposal advisory pipeline に `actor_id` を通し、AI提案HUDを current active_char に応じて出し分けられるようにした。

  * proposal → shadow record → advisory item → display item → provider → HUDCallbacks まで `actor_id` を伝播。
  * HUDCallbacks は `game_state["active_char"].name` を provider へ渡し、現在操作中RC向けのAI提案だけを表示する。
  * `src/action_proposal/demo_seed.py` を追加し、刑事向け・愉快犯向けのDemo Proposalを標準shadow logへ生成できるようにした。
  * demo_seed は冪等化済み。同一 `actor_id + proposal_id` の既知seed proposalは重複追加せず、既存重複も1件に正規化する。
  * HUD確認済み:

    * 操作RC = 刑事 → 「証言時刻を照合する」のみ表示
    * 操作RC = 愉快犯 → 「偽の痕跡を残す」のみ表示
  * AI提案は引き続き read-only 表示。ActionPipeline / action_registry / Actions listbox には未接続。



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
    * `python -m src.action_proposal.demo_seed` で、刑事/愉快犯向け actor_id 付きPASS proposalを標準shadow logへ生成できる
    * HUDに「AI提案」欄を表示できる
    * ただし、現時点では表示のみ。クリック不可・実行不可・Actions listboxには混ぜない

* ⚠️ いまの課題:

  * HUDのAI提案欄は read-only 表示まで。提案をプレイヤーが採用・実行する導線は未実装
  * shadow log はデモseed経由で作れる段階。ゲーム本体から自然に proposal を生成する導線は未実装
  * `jobs/%Y%m%d_quick/action_proposal_shadow.jsonl` はプレイセッション監査ログとして扱う必要が出てきた
  * requirements の値検証や `RequirementsChecker` 連携は未実施
  * effects の world state 適用や `action_registry` 連携は未実施
  * ROがRC_AIの行動選択に影響を与える仕組み（policy_patch）は未実装
  * `pytest -q` はall green。

* 🎯 今やっている目的:

  * Action Proposal DSL v0.1 を、実行系へ直結させる前に「提案→検問→ログ→表示」まで安全に通す
  * 次は、HUDに見えているAI提案を、どうやって自然に生成するか、またはプレイヤーがどう採用するかを段階的に設計する

## 3. 直近の変更（最新3つだけ）
* 2026-06-21: Session 49-B: 60秒デモ前のMicroGoal/Actions整合ポリッシュ。現在HUD Actionsに対応ActionがあるRC別MicroGoalだけを表示し、未解放時は `未設定` にする。
* 2026-06-20: Session 49: active actor + ActorModeごとのRC別MicroGoal保存・表示とsave/load維持を追加。
* 2026-06-20: Session 48-C: DirectorMode / active actor ActorModeをHUDで別表示し、HUD_DEBUG時のActorMode変更dropdownとActions即時再描画を追加。PURSUE affordance、FLEE解除、save/load維持をテスト。

## 4. 次にやること（最大3つ・小さく）
### 次の優先タスク

1. `pytest -q` のall greenを維持する。

   * 新しいactor別HUD ActionsとAI提案HUDの回帰を継続して確認する。

2. 愉快犯向けTPOコンテンツ縦切りを作り、場所・時間・条件・物語上の抑制を追加する。

3. RC別location/discoveryとROのRC別実装を設計する。

   * 現在MicroGoalと潜在目標 / 予兆 / ヒントの表示分離は後続で扱う。


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
