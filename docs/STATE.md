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

### Design Note: HUDアクション合成 / GUIアクションコンパイル

HUDアクション合成、GUIアクションコンパイル、GUIアクションとHUDアクションの責務分離については、
`general_documents/future_goals/HUD_ACTION_SYNTHESIS_AND_GUI_COMPILE.md` を参照する。

重要な方針:

- GUIアクションはHUDアクションの旧実装ではない。
- GUIアクションは世界状態を動かす基礎動詞。
- HUDアクションは、GUIアクション・TPO・discovery・RC状態を物語的に束ねた高レベル候補。
- Session51ではHUDアクション合成エンジン本実装やGUIアクションコンパイル本実装までは行わない。
- まずはpackベースの小さなTPO縦切りを進める。
- TPO / current_target / same-location / Operation設計は `general_documents/future_goals/gm_ai_tpo_operation_design_260630.md` を参照。
- MicroGoal と Operation.MiniGoal の関係は `general_documents/future_goals/gm_ai_microgoal_operation_minigoal_260630.md` を参照。

current_target と narrative_targetの違い：

- actor.current_target = そのRCが意識している対象
- gui.selected_target = GUI上で選択中の対象
- hud.narrative_target = HUD候補生成上の物語対象
- world.current_focus = 演出焦点

- RC別 perceived_world / RC行動認知ループの将来設計は `general_documents/future_goals/gm_ai_rc_perception_loop_memo_260706.md` を参照。

## 1. すぐ動かす（入口コマンド）
- Run:
  - `python -m src.simulation`
- Test:
  - `pytest -q`
- RC（回帰/自動挙動）:
  - （例）`python -m src.simulation --rc` / `python -m src.rc_ai` など
  - 現状のRC起動方法: TODO（確定したらここに1行で）

## 2. いまの状態（3行で）
### Session56: RC_AI read-only advisory v0.1

- 既存 `src/rc_ai.py` に `generate_rc_advisory(bundle)` を追加した。
- 刑事の active inquiry Operation + `mini_goal_first_testimony` から、単一意図 `advance_inquiry_first_testimony` と `choose_first_inquiry_target` を返す最小縦切りを実装した。
- advisory は単一のYAML/JSON-safe dictで、`preferred_action_layer: HUD` / `confidence: 1.0` / `auto_execute: false` を返す。
- 対応する利用可能HUD候補がない場合は `no_safe_action` を返し、入力Bundleやworldを変更しない。
- RCContextBundleへactor別RGB snapshotと `active_operation.mini_goal_id` を追加した。
- actor別RGBは `emotions_by_actor` → actor object → active actorのworld emotion → default の順で解決し、0..255へ正規化する。
- 既存 `select_action()` / `pick_action()` とその呼び出し経路は変更していない。
- 自動実行 / ActionPipeline接続 / Operation進行 / RGB tie-breaker / 愉快犯FLEE rule / RO接続は未実装。
- pytest: 398 passed, 1 skipped（399 collected）。

### Session55.5: HUDウィンドウ位置リセット修正

- HUDの初期geometry指定は生成時の1回だけで、refreshやActor切替による再指定は無かった。
- 根本原因は、simulation側の協調 pump() とHUDの33ms after がともに root.update() を実行し、Tkイベントループが再入していたことだった。
- DirectorHUD.run_async() の内部タイマーを廃止し、初回描画後はsimulation側の協調 pump() だけで更新するようにした。
- HUD内容更新、Actor切替、advisory更新は既存のenqueue経路を維持した。
- GUI非依存の回帰テストで、run_async() が内部タイマーを登録しないことを固定した。
- pytest -q: 381 passed。
- Session56のRC_AI/advisory選択ロジックには着手していない。

### Session55-A: RCContextBundle v0

- `src/rc_context.py` を新規作成した。
- `build_rc_context_bundle(actor_id, game_state, director)` v0 を実装した。
- `perceived_world` / actor_mode / micro_goal / active_operation / available_actions / recent_memory placeholder を束ねるRC_AI入力用bundleを生成できるようにした。
- `available_actions` は gui / hud / meta に分類する。
- `move_to_location(destination)` は gui に分類する。
- `switch_character` / `set_emotion` は meta に分類し、`rc_ai_eligible: false` とする。
- Operation依存HUD候補は hud に含め、`required_operation_type` 等で区別する。
- RCContextBundleは保存せず、毎回生成する派生ビューとして扱う。
- rc_ai.py / LLM / 行動意図生成 / 自動実行 / Operation進行 / memory保存 / belief保存はまだ未実装。

### Session54-A: RC別 perceived_world v0

- `src/perceived_world.py` を新規作成した。
- `build_perceived_world(actor_id, director_world)` v0 を実装した。
- actor_id / location / actor_mode / discoveries / active_operation / visible_routes / interpretations を含むRC別viewを生成できるようにした。
- `visible_routes` は `location_graph` と `allowed_actors` を反映する。
- `interpretations` はルールベースで、刑事と愉快犯で異なる見え方を返す。
- HUD_DEBUG時に perceived_world の短いread-only要約を表示する。
- perceived_world は保存せず、director_world等から毎回生成する派生ビューとして扱う。
- CaseSeed / hidden_role / case_theory / clue真相役割 / arrest判定 / belief_world / memory / RC_AI / LLM / Operation進行 / GUI Action Compile はまだ未実装。

### Session53-A: GUI基礎動詞「移動する」縦切り

- Session53-A-Fix-3: `move_to_location(destination)` 成功時は通常アクションと同じ行動ログへ記録される。不正destination拒否時は成功ログを残さない。

- `location_graph` v0 を導入した。
- GUI基礎動詞 `move_to_location(destination)` を追加した。
- `move_to_location(destination)` はHUD ActionsではなくGUIアクション欄に表示されるGUI基礎動詞として接続した。
- 実行本体は `ActionPipeline` + `location_graph.py` に寄せ、GUI候補の `params.destination` を選択経路から保持して渡す。
- 移動実行時に `director_world["actor_locations"][actor_id]` を更新し、active actor viewとして `game_state["current_location"]` も同期する。
- 移動先は現在地の `location_graph.exits` と `allowed_actors` によって制限される。
- `酒場` / `情報源_夜の酒場` のlocation重複を整理し、Session53-Aでは `酒場` に統一した。
- `time_min` はedge metadataとして定義したが、まだ時計や時間stateは進めない。
- 移動してもOperation / Operation.MiniGoal / MicroGoalは勝手に変わらない。
- perceived_world本実装 / GUI Action Compile / 自動移動 / 経路探索 / 時間消費 / Operation phase進行はまだ未実装。

### Session52-C: required_operation_type によるHUD候補の最小接続

- `required_operation_type: inquiry` を導入し、inquiry Operation中だけ「聞き込み先を一件選ぶ」が出るようにした。
- 「聞き込みを始める」は既存挙動として、刑事 + PURSUE/WITNESS + camera_skew_noticed でHUD候補に出て、実行すると inquiry Operation を開始する。
- Operationが無い時、他actorのOperationしか無い時、statusがactive以外の時はOperation依存候補が出ない。
- Operation依存候補も実行時gateで再チェックされる。
- OperationはHUD候補に1条件だけ影響するが、GUI候補には影響しない。
- phase自動進行 / 自動実行 / MicroGoal上書き / GUI Action Compile / RO接続はまだ未実装。

### Session52-B: HUD actionからOperationを1本だけ開始

- 刑事HUD action「聞き込みを始める」から inquiry Operation を開始できるようにした。
- Operationは director_world["actor_operations"][actor_id]["active_operation"] に保存される。
- Operation.MiniGoalとして「最初の証言を取る」を持つ。
- 同じHUD actionを2回実行してもOperationが重複しない。
- required_discovery未達や他actorからの直接requestではOperationが開始しない。
- Operation開始後もGUI gatingには影響しないことをテストで固定した。
- OperationによるHUD候補変化、required_operation_type、MicroGoal上書き、自動phase進行、自動実行はまだ未実装。

### Session52-A: active_operation保存・表示スケルトン

- actorごとにactive_operationを0..1で持てるようにした。
- 保存先は director_world["actor_operations"]。
- OperationはYAML safe_dump / safe_load、HUD save/loadで残る。
- world_defaults適用時に actor_operations が上書きされないよう preserve対象に追加した。
- HUDにactive actorのOperation / MiniGoalをread-only表示するようにした。
- switch_characterでOperation表示がactive actorに追従する。
- OperationはGUI gatingに一切影響しないことをテストで固定した。
- HUD actionからOperation開始、starts_operation、required_operation_type、Operationによる候補変化、自動phase進行、自動実行はまだ未実装。

### Session52-0: Operation前提修理

- Fable5外部レビューで指摘された重大リスク2件を、Operation実装前に修理した。
- discovery書き込みの正本を actor_discoveries[actor_id] に寄せ、legacy affordances.discoveries はactive actor viewの互換キャッシュとして扱う方針を強化した。
- affordance_bridge / ActionPipeline 経由のdiscovery獲得がHUD refreshで消えないようにした。
- TPO HUD / pack actionの実行時ゲートを追加し、actor_id / ActorMode / discovery / interaction_scope を実行時にも再チェックするようにした。
- 他actor用HUDアクションを直接requestしても実行されず、effectsが適用されないようにした。
- active_operation / Operation manager / GUI Action Compile はまだ未実装。

### Session51-E: RC別discovery語彙 / HUD_DEBUG注入整理

* Session51-E: RC別discovery語彙 / HUD_DEBUG注入候補を整理。
* actor別discovery catalogを導入し、刑事 / 愉快犯ごとにHUD_DEBUG注入候補を切り替えるようにした。
* 愉快犯向けdiscoveryとして `face_seen_risk` / `taunt_window_open` / `false_trace_material_ready` / `escalation_impulse` 等を追加。
* PROVOKEで `taunt_window_open` から挑発系HUD候補が出るようにした。
* MISLEAD / ESCALATE の `unsafe_route_identified` 依存を減らし、FLEE側の逃走系では維持した。
* discovery inventory: 既存のHUD_DEBUG dropdownは `discovery_rules` 由来のみで、TPO HUD候補の `required_discoveries` にあるIDが出ていなかった。
* 「知ったことを知る」系のメタ認識は今回は実装せず、将来課題として残した。
* future examples: `trickster_knows_fiber_collected` / `detective_notices_false_trace` / `trickster_realizes_witness_saw_face`。
* active_operation / Operation manager / GUI Action Compile はまだ未実装。

### Session51-D: Trickster ActorMode taxonomy / HUD候補整理

* Session51-D: 愉快犯ActorMode taxonomy / HUD候補整理を実施。
* DirectorModeは従来通り FREEZE / PURSUE / WITNESS / FLEE を維持。
* 愉快犯ActorModeを FLEE / MISLEAD / PROVOKE / ESCALATE に整理。
* FLEEに集中していた愉快犯HUD候補を、逃走・撹乱・挑発・エスカレート系へ分配。
* 「偽の痕跡を残す」など重複候補を整理。
* 「目撃証言を撹乱する」はMISLEAD系候補として扱う。
* Operation本実装 / active_operation / GUI Action Compile はまだ未実装。

### Session51-C: packベースTPO HUD候補

* Session51-C: packベースTPO HUD候補を追加。
* 51-Bで消えた別location direct actionの空白に、追跡・推理・撹乱・逃走経路変更・偽痕跡系のHUD候補を追加した。
* GUI直接行動のsame-location gatingは維持。
* Operation本実装 / active_operation / GUI Action Compile はまだ未実装。

### Session51-B: GUI action target gating / same-location requirement

* GUI直接行動に `same_location` requirement を導入した。
* `talk` / combat系GUIアクションは、有効targetが存在し、かつactorとtargetが同じlocationにいる時だけ候補に出る。
* `current_target` は「目の前にいる相手」ではなく「そのRCが意識している対象」として扱う。
* active actor自身をtargetにするself-targetは常に不許可。
* `has_enemy` はcombat系の十分条件ではなくなり、有効target + same-location が必要。
* `action_layer` / `interaction_scope` の最小メタデータを導入し、将来のHUD Action Synthesis / GUI Action Compile / Operation設計の足場にした。
* `arrest` / `逮捕する` はまだGUIコマンドとして実装していない。
* HUD Action / Operation本実装、TPO HUD候補追加はまだ行っていない。Session51-C以降に回す。

### Session51-A前: TPOコンテンツ縦切りの前整理
* TPO縦切りでは、まずGUI/HUD/Operationの境界を壊さないことを優先する。

* current_targetはactor別。
* talk/combat/arrestはsame-location必須。
* 別locationのtargetに対してはGUI直接行動を出さず、HUDのremote narrative actionとして追跡・推理・撹乱・痕跡系を出す。

* HUDアクションは即時GUIアクションではなく、Operationを開始・更新するものとして扱う。
* Operationは「長い行動」ではなく「長い文脈」。
* OperationはMicroGoal(Operation.MiniGoal)、HUD候補、GUIアクションの意味づけ、RO提案に影響する。

* ROはOperationの進行・分岐・中断・再開・発展を提案する作戦参謀として活用したい。

* まずは自動実行ではなく、HUDからOperationを開始し、OperationがMicroGoalとHUD候補に影響し、ROが次の一手を提案するところまでを小さく縦切りする。


### Session50: RC別location / discovery

* `director_world["actor_locations"]` にRCごとの現在地を保存する。
* `director_world["actor_discoveries"]` にRCごとの発見を保存する。
* `game_state["current_location"]` は廃止せず、active actor location のlegacy互換キャッシュとして扱う。
* `director_world["affordances"]["discoveries"]` は廃止せず、active actor discoveries のlegacy互換ビューとして扱う。
* `switch_character` / HUD refresh時に、HUD Actions / MicroGoal / affordance gating の前提がactive actor視点へ切り替わる。
* 刑事のdiscoveryが愉快犯HUDに混ざらず、愉快犯のdiscoveryも刑事HUDに混ざらない。
* 提案候補は引き続きactor_id filter / read-onlyのまま。
* ActionPipeline接続、提案候補の実行化、RO / Recommended / Progressの本格RC別対応、HUD Action Synthesis本実装、GUI Action Compile本実装はまだ行っていない。

### Session 49-D: HUD_DEMO legibility pass

* 60秒デモ撮影用にHUD_DEMOの文字サイズと表示ラベルを調整した。
* HUD_DEMOではDirectorMode / ActorMode / MicroGoal / Actions / 提案候補を14ptで表示し、Director HUDを700x600へ広げて余白と折り返し幅を調整する。
* 「AI提案」はAction Proposal / advisoryを含む内部実装名として維持し、HUD_DEMO表示のみ「提案候補」とする。
* 通常HUD / DEBUG HUDの既存表記と表示モード優先順位、ActorMode変更、RC別MicroGoal / Actions、actor_idフィルタ、read-only動作は維持する。

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
* 2026-06-30: Session51-B: GUI直接行動のsame-location gatingを実装。talk/combat系は有効target + same-locationが必要になり、self-targetや別location targetでは表示・実行されない。`action_layer` / `interaction_scope` の最小メタデータも追加。
* 2026-06-29: Session50: RC別location/discoveryを実装。active actorごとに現在地と発見を保持し、HUD refresh時にlegacy互換の `current_location` / `affordances.discoveries` へ同期する。HUD_DEBUGで刑事/愉快犯の発見が混ざらないことを確認。
* 2026-06-21: Session 49-C: 60秒デモ撮影用に `HUD_DEMO=1` を追加。RO / Recommended / ProgressはデモHUDから隠し、ActorMode / location / discovery操作は残す。`HUD_DEBUG=1` は開発用フルHUD、両方無効なら通常HUD。

## 4. 次にやること

### 次の優先タスク

1. Session56: rc_ai.py advisory v0 を検討する。
2. RCContextBundleを入力に、認識・葛藤・desired_intent・preferred_action候補をread-onlyで出す。
3. RC_AI出力は自動実行せず、必ず既存gateで検証する方針を維持する。
4. move_to_locationがログに記録されない問題を別途 Session53-A-Fix-3 として調査する。

## 5. ブロッカー（止まってる理由があれば）
（現状）大きなブロッカーなし。

* 既知課題: 愉快犯側で刑事と同じlocationにいても、有効な `actor_targets["愉快犯"] = "刑事"` が未設定ならtalk/combat系は出ない。これは安全側の挙動であり、actor別target導入時に整理する。

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

### ブランチ方針

- `main`
  - Prototype Demo #1 公開時点を保持する安定ブランチ。
  - `demo-001` タグあり。
  - YouTubeデモ公開直後のため、しばらく直接更新しない。

- `staging/*` または `integration/*`
  - Demo #1 以降の開発成果を一時統合するブランチ。
  - Session50以降の実装は、まずここへ集約してからmain mergeを判断する。
  - 現在の作業ブランチは `staging/session50-actor-view`。

- `feature/*`
  - 個別実装用ブランチ。
  - 完了・統合済み・不要になったものは、削除候補として棚卸しする。
  - 削除は人間が確認してから行う。

### バックアップ方針

- 大きな節目ではGitHub pushに加え、zipをGoogle Driveへ退避する。
- 公開デモ、重要設計、main更新前後では、タグまたはブランチ名で復帰地点を明示する。
- 破壊的なブランチ削除は、削除候補メモを作ったあと、人間確認を挟んでから行う。
