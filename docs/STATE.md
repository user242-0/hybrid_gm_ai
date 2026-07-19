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
### Session59-B: RC Memory Projection v0.1 実装

- `src/rc_memory.py` を追加し、Session59-Aの客観 `operation_transition_v0.1` eventをactor別の主観Memoryへ決定的に投影する縦切りを実装した。保存先はauthoritativeなdirector world rootの `actor_memories[actor_id]` で、root／actor bucketはvalid Memoryの保存直前だけ遅延生成する。
- 対応ruleは、刑事の inquiry Operationが `start → target_selected` へ進み、最初の聞き込み先選択MiniGoalを完了したstructured fieldsの完全一致だけを扱う。event ID文字列自体はrule selectorにせず、構造との整合性確認と `source_event_id` に使う。Memoryは `rc_memory_v0.1`、`kind=operation_progress`、`memory_key=first_inquiry_target_selected`、決定的summary「最初の聞き込み先を選んだ」を持つ。
- Memory IDは `memory:{memory_actor_id}:{source_event_id}`。v0.1は一source event・一actor・一Memoryとし、memory IDとactor＋source eventの線形照合で冪等化する。重複時はworldを変更せず既存Memoryのdeepcopyを返し、不正root／bucketは上書きしない。
- live projectionは `ActionPipeline.request_action()` でtransition recordがeventを返した直後に行う。Memory projection例外は専用ログに分離し、Action effects、Operation進行、客観transition event、`ActionExecutionOutcome`、後続UIを巻き戻さない。残ったeventは後のcatch-upで再投影でき、transaction／rollbackは導入していない。
- catch-upはmanual loadでloaded worldを正式採用し、`game_state`のworld参照を差し替えた直後だけ実行する。startup、HUD refresh、Bundle生成、advisory生成では実行しない。catch-up後の自動Saveも行わず、次の明示Saveでdiskへ永続化する。
- `RCContextBundle["recent_memory"]` はactor bucketから直近5件のMemory record全体を古い順→新しい順でdeepcopyして返すread-only派生viewになった。長期store側の古いMemoryは削除せず、刑事Memoryを愉快犯へ混ぜない。Memory追加後も現行RC_AIへ新ruleは加えていないため、進行後advisoryは従来どおり `no_safe_action` になる。
- Memory subtreeはJSON-safeかつYAML safe_dump/safe_load・deepcopy可能で、既存save/loadとworld defaultsに自然に保持される。pack defaults、save/load本体、world defaults、perceived_world、ActionExecutionOutcomeは変更していない。simulation clock、OS時刻、confidence／salience／emotion、observer Memory、検索／忘却、Beliefは対象外。
- 自動テストは `641 passed / 2 skipped`、`git diff --check`成功。自動テスト完了、Windows手動確認待ち。専用Memory UIは追加していないため、手動確認ではAction後に明示Saveし、`director_world.yml` の `actor_memories.刑事` と `source_event_id` を確認する。次はChatGPTへSession59-Bデブリーフを持ち帰り、Session59-Cへは勝手に進まない。

### Session59-A: Operation Transition Record v0.1 実装

- Operation progression成功resultを客観eventへ変換する `src/operation_transition_history.py` を追加した。eventはauthoritativeなdirector world rootの `operation_transition_history` へglobal append-only listとして遅延生成・保存し、Memory / Beliefの主観情報や人間向けsummaryは混ぜていない。
- schemaは `operation_transition_v0.1` / `kind=operation_transition` と、actor / Operation / from-to phase / completed-next MiniGoal / trigger action / world conditionを持つ。`reason` は `world_condition` へ写し、IDは `operation_transition:{actor_id}:{operation_id}:{from_phase}:{to_phase}:{completed_mini_goal_id}` の決定的文字列とした。simulation clock、OS時刻、UUIDは保存していない。
- `ActionPipeline.request_action()` のeffects成功 → Operation progression成功直後、Operation start / time advance前でrecordする。現在のactive Operation post-stateとactor/id/type/to_phase/next MiniGoalを照合し、history内のevent ID線形走査で冪等化する。重複時はworldを変更せず既存eventのdeepcopyを返し、不正historyは上書きしない。
- record例外はprogression例外と分離してログに残し、Action effects、Operation進行、`ActionExecutionOutcome.executed`、UI refreshを巻き戻さない部分成功契約とした。v0.1ではtransaction / rollbackを導入していない。
- event/history subtreeはJSON-safeかつYAML safe_dump/safe_load・deepcopy可能で、既存director world save/loadへ自然に含まれる。`world_defaults.py`、pack defaults、save/load本体、ActionExecutionOutcome、RCContextBundle、perceived_worldは変更していない。
- 同actor・同typeのOperation再開始では現在の固定Operation IDによりevent IDが衝突し得る。Operation instance identityはv0.1既知制限として、Operation完了／clear／再開始を設計するSessionへ残す。RC Memory、Belief、Bundleの `recent_memory` / beliefs反映も未実装。
- 自動テストは `586 passed / 2 skipped`、`git diff --check`成功。builder/recorder、actor・post-state照合、冪等性、serialization、Pipeline成功／拒否／effects・progression・record例外、手動advisory採用、HUD/Bundle/advisory read path、switch、save/loadを固定した。自動テスト完了、Windows手動確認待ち。次はChatGPTへSession59-Aデブリーフを持ち帰った後にSession59-Bを検討する。

### Session58-B: Operation phase / MiniGoal progression 実装

- `src/operation_progression.py` を追加し、ActionPipelineのeffects成功直後にactor別world condition `inquiry_target_chosen`を評価するpost-success hookを接続した。条件成立時だけ `phase=start` / `mini_goal_choose_first_inquiry_target` から `phase=target_selected` / `mini_goal_take_first_testimony` へ一度だけ進み、他actor・不完全state・再評価は安全なno-opになる。
- cop_trickster packの新規inquiry初期MiniGoalを「聞き込み先を一件選ぶ」へ修正した。RC_AIのschema、intent ID、preferred action、通常表示は維持し、旧 `mini_goal_first_testimony` は初期段階のlegacy aliasとしてRC_AIと進行判定の両方で受理する。次MiniGoal用ruleは追加していないため、進行後のRC advisoryは空になる。
- `ActionExecutionOutcome`、HUDCallbacks、DirectorHUDは変更せず、既存HUD cache rev / refreshでOperation phase・MiniGoal更新とRC advisory消去を反映する。Operation statusと既存metadataは保持し、履歴schema、Memory / Belief、Operation完了、中断・切替、GUI Action Compileは対象外のまま。
- 自動テストは `498 passed / 2 skipped`。Operation進行の冪等性・legacy互換・actor分離・JSON/YAML安全性、Pipeline成功／拒否／effects失敗／progression例外、58-A手動採用、実行前後HUD表示、進行後save/loadまで固定済み。Windows手動確認でも、初期MiniGoalから `target_selected` / 「最初の証言を取る」への遷移とRC advisory消去を確認した。`investigation_progress +1`は手動では未確認だが、実Pipeline自動テストで1回だけ増えることを固定している。

### Session58-A: RC advisory manual adoption / execution 実装

- Session57.5の確定HEAD `5ab44e3` を `staging/session57-5-hud-intelligence-panel` としてoriginへcheckpoint化し、同HEADから `feature/session58a-rc-advisory-manual-execution` を作成した。
- RC COGNITION本文内へ「採用して実行」buttonと非modal statusを追加した。normalの折りたたみ時はbuttonも隠れ、demo/debugの既存展開方針、水平2ペイン、AFFECT、RO/Externalの独立setterは維持している。
- 表示済みRC advisoryは、HUDCallbacks内の非永続な構造化snapshotとして保持する。手動採用時にactive actorを再確認し、fresh RCContextBundle/advisoryを再生成してschema/actor/intent/action/layer/paramsが完全一致した場合だけ、既存 `source="HUD"` のActionPipeline経路へ1件渡す。不一致・switch・例外時はworldを変更せずstatus表示とHUD再生成へ安全に倒す。
- Session58-Aの実行allowlistは `choose_first_inquiry_target` のみ。ActionPipelineへ既存戻り値を変えないopt-in `ActionExecutionOutcome` を追加し、成功と拒否を区別した。愉快犯 `change_escape_route`、RO、External Proposalは表示のみを維持する。
- 二重実行防止は、TPO candidateへactor別 `forbidden_discoveries: [inquiry_target_chosen]` を追加し、Directorの候補生成時と実行時gateの双方で評価する。1回目にdiscovery追加と`investigation_progress +1`を適用すると候補/advisoryが消え、直接2回目を要求してもgateで拒否される。
- 58-AではOperation / Operation.MiniGoal / phaseを進めない。達成条件の読取りと進行は58-Bへ分離する。Operation interruption / arbitration（suspend/resume/cancel/replace/urgent discovery競合）も将来課題であり、58-Aへ持ち込まない。
- 全475件は473 passed / 2 skipped（headless Tk widget tests）で成功し、`git diff --check`も成功した。Windows手動確認では、刑事のactive inquiry Operationから「採用して実行」が成功し、effects 2件の適用、advisory消去、二重実行拒否、愉快犯advisory実行不可、Operation / MiniGoal / phase不変を確認済み。Session58-Aの受け入れ条件は達成した。

### Session57.5: HUD Intelligence Panel / horizontal two-pane layout

- `feature/session57-5-hud-intelligence-panel` 上で、Director HUDを `tk.PanedWindow` による水平2ペインへ変更した。左はDirectorMode / Clock / ActorMode / Operation / Actions等のOperational Core、右はACTIVE RC / AFFECT / RC_AI判断 / RO / External Proposalsを分離表示する。
- Intelligence Panelはnormal / demo / debugの全モードで既定有効。`debug.hud_intelligence_panel` または `HUD_INTELLIGENCE_PANEL` で非表示にでき、設定省略時はtrueとする。
- RC_AI判断はnormalだけ初期折りたたみ、demo/debugは初期展開とした。normalでは「潜在意図あり」の状態表示から手動展開でき、新advisory到着では自動展開しない。折りたたみ状態は非永続で、timer / after / animationは追加していない。
- RC欄を「現在文脈から生成された潜在意図・継続候補」と明記し、RCの確定した本心とは扱わない。通常/demoは人間向けlabelのみ、debugは既存internal advisory fieldsを表示する。
- AFFECTは既存 `RCContextBundle["emotion"]` を再利用し、actor付き非永続cacheから表示する。通常/demoは色点のみ、debugはRGB数値も表示する。switch時はactor mismatchでRC advisoryとRGBを再生成し、Bundle失敗時はRC/AFFECTだけを安全にclearする。
- `set_ro_recommendation()` / `set_advisory_items()` / `set_rc_advisory()` は維持し、各sectionを独立更新する。Action Proposal、RC_AI rule、RO、ActionPipeline、Operation進行は変更していない。
- geometryは初期化時の1回だけ、`run_async()`と協調pumpも変更していない。全460件は458 passed / 2 skipped（headless Tk widget tests）で成功し、`git diff --check`も成功。Windows手動確認も完了し、Session57.5の受け入れ条件を達成した。

### Session57-B: Trickster FLEE reactive intent rule

- 57-A HEADから `feature/session57b-trickster-flee-intent` を分岐し、実装前のコードフロー調査を完了した。
- `generate_rc_advisory()` の共通経路を維持し、`_build_intent()` をOperation優先resolverとreactive resolverへ最小分割した。active Operationがある場合は未対応でもreactiveへfallthroughせず `no_safe_action` とする。
- active Operationがない場合のみ、愉快犯 + FLEE + `perceived_world.discoveries` の `unsafe_route_identified` から `avoid_unsafe_escape_route` / `change_escape_route` を決定的に選ぶreactive ruleを実装した。
- `get_active_operation()` はstatusを絞らないため、summary dictの `status == active` を遮断条件とする。明示的な非active文字列statusはreactive評価可、壊れたOperation構造は安全に `no_safe_action` とする。
- 57-AのHUD adapterへ日本語intent labelだけを追加し、action labelは既存ActionSpec、理由はadvisory rationaleを利用する。DirectorHUD/cache/switch経路、pack、ActionPipelineは変更していない。
- discovery消費、再推薦抑制、自動実行、HUD水平2ペイン化は対象外として将来の実行ループ設計へ残す。
- 単体・実Bundle・HUD表示・刑事→愉快犯→刑事switch統合を追加。対象149件と全回帰446件（445 passed / 1 skipped）が成功した。
- `.venv`での手動確認でも、愉快犯をFLEEにして `unsafe_route_identified` を注入すると「危険な逃走経路を避ける」intentがRC_AI判断欄へ表示された。Session57-Bの受け入れ条件は達成。
- 次候補はSession57.5としてHUD Intelligence Panel／水平ペインを検討。その後はSession58-Aでadvisory手動採用→ActionPipeline再検証→1件実行、Session58-BでOperation.MiniGoalまたはphaseの最小進行を想定する。

### Session57-A: Runtime RC_AI advisory → Director HUD read-only integration

- `HUDCallbacks.refresh_hud()` の既存HUD action cache再計算直後で、active actorの `RCContextBundle` とRC advisoryを生成するread-only経路を実装した。
- RC advisory表示cacheは永続stateへ保存せず `HUDCallbacks` インスタンス内にactor_id付きで保持し、表示反映は毎refreshでactor一致を確認する。cache revision差分に加えactor/mode不一致でも再計算し、switch時の残留を防ぐ。
- `DirectorHUD.set_rc_advisory(display_item | None)`、専用StringVar/row/formatterを既存 `set_advisory_items()` と独立して追加した。通常HUDではactor/短いintent/action label/reason、DEBUG HUDでは内部advisory fieldsも表示する。
- action labelは注入済み `get_action_spec()` を第一参照、Bundle内のHUD候補labelを第二参照とし、どちらもなければ通常HUDは空にする。
- `no_safe_action` またはRC経路の例外時はRC_AI欄だけをclearし、Action Proposal由来AI提案、Actions、Operation等のrefreshを継続する。
- 専用テストを追加し `git diff --check` は成功。ローカルPythonが未導入で、既存 `.venv` も削除済みPython 3.10を参照しているため、pytest実行はpython -m pytest -q: all passed, 0 skipped.実行環境では合計件数が表示されなかった
- 手動確認で「聞き込みを開始する」後に刑事のRC_AI判断がHUDへ表示されることを確認済み。Session57-Aの受け入れ条件は達成。
- RC_AI判断の複数行表示で縦方向が圧迫され、Actions/Operation周辺が隠れやすくなる。57-Aの機能完了とは分離し、右ペインへの水平分割などを次回以降のHUDレイアウト改善候補とする。

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
