# GM-AI Session 60-0A

## 現行Operation責務マップ v0.1

* 対象branch：`design/session60-0-operation-lifecycle-boundary-v01`
* baseline commit：`32b177b9180c9b774e4e9302a396be059a0d50cc`
* 調査基準：Session 59-C完成状態
* 本文の区分：

  * `CURRENT`：現行コード上の事実
  * `OBSERVATION`：事実から分かる構造上の特徴
  * `DEFERRED`：次回以降に判断する事項

---

# 1. CURRENT：現行構造の一文要約

現在のOperation lifecycleは、一つのmoduleが所有しているのではなく、次の連鎖によって成立している。

```text
scenario pack上のAction／Operation開始metadata
→ ActionSpecへ変換
→ DirectorがHUD候補を生成
→ ActionPipelineが実行条件を再検証
→ Action effects
→ Operation progression
→ Operation transition event
→ RC Memory
→ RC Belief
→ Operation開始metadataがあればOperation start
→ time／log／scene／HUD refresh
```

特に重要なのは、現行`ActionPipeline.request_action()`では概ね次の順序になっている点である。

```text
Action effects
→ Operation progression
→ transition event
→ RC Memory
→ RC Belief
→ Operation start
```

そのため、Operation開始Actionである`start_inquiry_operation`も、開始前に一度progressionを評価する。

現行の全体経路と責務の所在は、共有前調査でも同じ構造として確認されている。

---

# 2. CURRENT：Operation lifecycle責務マップ

## 2.1 Operation定義・開始候補

| 段階              | 現在の担当                                                     | 主な入力                                      | 主な出力                       | world変更     | 永続性             | 現行上の性質              |
| --------------- | --------------------------------------------------------- | ----------------------------------------- | -------------------------- | ----------- | --------------- | ------------------- |
| Operation開始定義   | `data/director/packs/cop_trickster.yml`                   | シナリオ定義                                    | ActionとOperation開始metadata | なし          | repository上で永続  | Content／Blueprint寄り |
| metadata schema | `src/action_model.py::ActionSpec`                         | pack field                                | runtime ActionSpec         | なし          | runtime一時object | 境界schema            |
| pack→spec変換     | `src/action_definitions.py::_spec_from_new()`             | pack action dict                          | ActionSpec                 | なし          | 一時              | Definition Adapter  |
| HUD候補生成         | `Director.list_actions_for_actor()`およびTPO候補処理             | actor、mode、discoveries、location、Operation | HUD Action候補               | 原則read-only | 一時              | Candidate builder   |
| 実行直前gate        | `Director.can_execute_tpo_hud_action()`                   | 最新world、actor、source、action               | allow／reject               | なし          | 一時result        | Machine Core候補      |
| 開始指示            | `ActionPipeline._start_operation_from_spec()`             | 成功Action、ActionSpec、actor                 | domain関数呼び出し               | 間接的         | 一時              | Coordinator責務       |
| instance生成      | `actor_operations.start_operation_once()`                 | actor、type、phase、MiniGoal等                | active Operation           | あり          | 次回save対象        | Machine Core domain |
| authoritative保存 | `world["actor_operations"][actor_id]["active_operation"]` | Operation instance                        | 現在のactive Operation        | あり          | persistent      | authoritative state |

---

## 2.2 Operation開始定義の現状

現行には、独立した`OperationDefinition` objectやregistryは存在しない。

Operationを開始するための定義は、`start_inquiry_operation`というActionに付属するmetadataとして保持されている。

```yaml
start_inquiry_operation:
  starts_operation: true
  operation_type: inquiry
  operation_label: "聞き込みを始める"
  operation_phase: start
  operation_mini_goal:
    id: mini_goal_choose_first_inquiry_target
    label: "聞き込み先を一件選ぶ"
    status: active
```

これらは`ActionSpec`の次のfieldへ変換される。

```text
starts_operation
operation_type
operation_label
operation_phase
operation_mini_goal
```

一方、`choose_first_inquiry_target`はOperationを開始しない。Action effectsによってworld conditionを成立させ、既存Operationを進行させるActionである。

したがって、現行では次が一つのAction定義内に結び付いている。

```text
Actionの意味
Action effects
Operationを開始するか
開始するOperation type
初期phase
初期MiniGoal
```

---

# 3. CURRENT：Operation instanceとauthoritative owner

## 3.1 正本の保存先

現行active Operationのauthoritative ownerは次である。

```text
director_world
└─ actor_operations
   └─ actor_id
      └─ active_operation
```

代表的なOperation instanceは次のfieldを持つ。

```text
id
type
label
status
phase
actor_id
target_id
parent_microgoal_id
created_from
mini_goal
notes
```

## 3.2 現行制約

現行構造は実質的に次の契約を持つ。

```text
1 actorにつきactive Operationは最大1件
```

`start_operation_once()`は、

* 同一actorに別Operationがあれば開始を拒否する
* 同じ`op_{operation_type}_{actor_id}`があれば既存Operationを返す
* 空いていれば新しいOperationを作成する

という挙動を持つ。

現行Operation IDは次の形式で決定される。

```text
op_{operation_type}_{actor_id}
```

## 3.3 semantic authority

`actor_operations`は、現在何を実行中かを表す正本である。

以下は正本とは役割が異なる。

```text
operation_transition_history
= 過去に起きた遷移の客観記録

actor_memories
= actor本人に帰属する経験記録

actor_beliefs
= actor本人が現在信じている認識snapshot

RCContextBundle
= RC_AIへ渡す一時的なread-only snapshot

RC advisory
= 次に何をしたいかという提案
```

---

# 4. CURRENT：Operation開始フロー

## 対象Action

```text
start_inquiry_operation
```

## 4.1 HUD候補になる条件

packとDirectorの現行条件では、おおむね次が必要になる。

```text
actor_id = 刑事
actor mode = WITNESS または PURSUE
camera_skew_noticed discoveryを持つ
interaction_scope = any_location
```

Directorは候補表示時に、次を確認する。

```text
actor
actor mode
required discoveries
forbidden discoveries
required Operation type
location scope
```

さらに実行時にも`can_execute_tpo_hud_action()`で同様の条件を再確認する。

候補として表示されたことだけでは、実行は保証されない。

---

## 4.2 正確な開始順序

```text
start_inquiry_operationを選択
↓
ActionPipeline.request_action()
↓
ActionSpec取得
↓
Director execution gate
↓
action_registry.execute_action_core()
↓
Action effects成功
  ※このActionのeffectsは空
↓
advance_operation_after_action()
↓
active Operationがまだ存在しない
↓
progression result
  advanced = false
  reason = no_active_operation
↓
transition eventなし
↓
RC Memoryなし
↓
RC Beliefなし
↓
ActionPipeline._start_operation_from_spec()
↓
start_operation_once()
↓
actor_operations.刑事.active_operationを作成
↓
time／Director tick／log／HUD refresh
```

つまり、現行ではOperation開始Actionに対し、Operation開始より先にprogression評価が行われる。

```text
progression
→ no_active_operation
→ start
```

この順序は動作上は成立している。

ただし処理を読む人にとっては、直感的な順序ではない。

---

# 5. CURRENT：Operation進行フロー

## 対象Action

```text
choose_first_inquiry_target
```

## 5.1 HUD候補になる条件

おおむね次が必要になる。

```text
actor_id = 刑事
actor mode = WITNESS または PURSUE
active Operation type = inquiry
active Operation status = active
inquiry_target_chosenをまだ持っていない
```

`required_operation_type: inquiry`は、現在のactor本人のactive Operationだけを参照する。

他actorのOperationは候補条件を満たさない。

---

## 5.2 正確な進行順序

```text
choose_first_inquiry_targetを選択
またはRC advisoryを手動採用
↓
ActionPipelineへdispatch
↓
Director execution gateを再確認
↓
Action effects
├─ actor_discoveries.刑事にinquiry_target_chosenを追加
└─ investigation_progressを加算
↓
advance_operation_after_action()
↓
active Operationを検証
├─ actor_id
├─ operation type
├─ status
├─ phase
└─ MiniGoal
↓
world conditionを検証
inquiry_target_chosenが存在
↓
Operationを更新
├─ phase: start → target_selected
└─ MiniGoal:
   聞き込み先を一件選ぶ
   → 最初の証言を取る
↓
progression result
↓
Operation transition event
↓
RC Memory
↓
RC Belief
↓
_start_operation_from_spec()
  ※starts_operationではないため何もしない
↓
time／Director tick／log／HUD refresh
↓
fresh RCContextBundle
↓
fresh RC advisory
```

Session 59黄金経路では、最後のfresh advisoryは`no_safe_action`になる。

このAction→Operation→event→Memory→Belief→fresh Bundleの経路が、Session 60以降も保護すべき最重要characterization contractである。

---

# 6. CURRENT：Operation progression

## 6.1 担当

```text
src/operation_progression.py
└─ advance_operation_after_action()
```

## 6.2 入力

```text
world
actor_id
executed_action_id
```

## 6.3 authoritative write

進行条件を満たす場合、次を書き換える。

```text
world["actor_operations"][actor_id]["active_operation"]
```

具体的には、

```text
phase
mini_goal
```

が更新される。

その他のOperation metadataはdeepcopyによって維持される。

## 6.4 進行条件の正本

重要な現行方針は次である。

```text
Action IDそのものではなく、
Action effects後のworld conditionが進行条件の正本
```

現行inquiryでは、

```text
actor_discoveries.刑事に
inquiry_target_chosenが存在する
```

ことが完了条件になっている。

`executed_action_id`は、どの成功Actionがprogression評価を起動したかを記録する。

したがって概念上は、

```text
Actionが直接phaseを進める
```

のではなく、

```text
Actionがworldを変える
→ Operationがworld conditionを読む
→ 条件成立なら進む
```

という構造である。

---

# 7. CURRENT：progression result

## 7.1 位置づけ

progression resultは、Operation stateでもDomainEventでもない。

次の処理へ渡す一時resultである。

```text
Operation progression
→ progression result
→ transition event builder
```

## 7.2 主なfield

成功時には次を含む。

```text
advanced
actor_id
reason
trigger_action_id
operation_id
operation_type
from_phase
to_phase
completed_mini_goal_id
next_mini_goal_id
```

失敗／no-op時には主に次を返す。

```text
advanced = false
reason
actor_id
trigger_action_id
```

## 7.3 性質

```text
JSON-safe
一時的
save dataへ直接保存しない
worldの正本ではない
履歴ではない
```

progression resultは、

> Operationを更新した直後に何が起きたかを、客観eventへ変換するための引換票

と捉えると分かりやすい。

---

# 8. CURRENT：Operation transition event

## 8.1 担当

```text
src/operation_transition_history.py
├─ build_operation_transition_event()
└─ record_operation_transition()
```

## 8.2 入力

```text
advanced = trueのprogression result
```

## 8.3 出力

```text
operation_transition_v0.1
```

の客観event。

代表field：

```text
schema_version
kind
event_id
actor_id
operation_id
operation_type
from_phase
to_phase
completed_mini_goal_id
next_mini_goal_id
trigger_action_id
world_condition
```

## 8.4 保存先

```text
world["operation_transition_history"]
```

globalなappend-only listとして保存される。

## 8.5 progression resultとの境界

transition recorderは、progression resultをそのまま無条件で記録しない。

更新後のactive Operationを再取得し、次が一致していることを確認する。

```text
actor_id
operation_id
operation_type
to_phase
next_mini_goal_id
```

つまりtransition eventは、

```text
progression functionがそう報告した
```

だけでなく、

```text
authoritative Operationが実際にその後状態になっている
```

ことを照合した客観記録である。

---

# 9. CURRENT：RC Memory

## 9.1 担当

```text
src/rc_memory.py
```

## 9.2 入力

```text
objective Operation transition event
```

## 9.3 出力

actor本人に帰属するRC Memory。

```text
rc_memory_v0.1
kind = operation_progress
```

## 9.4 保存先

```text
world["actor_memories"][actor_id]
```

## 9.5 性質

```text
actor-relative
persistent
transition eventから決定的に生成
idempotent
Bundleではread-only snapshotとして読む
```

Memoryはeventそのものではない。

```text
transition event
= 客観的に何が起きたか

Memory
= actor本人の経験として何が残ったか
```

---

# 10. CURRENT：RC Belief

## 10.1 担当

```text
src/rc_belief.py
```

## 10.2 入力

```text
actor本人のRC Memory
```

## 10.3 出力

現在のBelief snapshot。

```text
rc_belief_v0.1
kind = operation_state
belief_id = first_inquiry_target_selected
```

## 10.4 保存先

```text
world["actor_beliefs"][actor_id][belief_id]
```

## 10.5 性質

```text
actor-relative
persistent
current snapshot
source_memory_idsを保持
Operationの正本ではない
world truthへ逆流しない
```

Beliefは、

```text
何が起きたかの履歴
```

ではなく、

```text
現在そのactorが何を真だと認識しているか
```

を表す。

---

# 11. CURRENT：save／load／world adoption

## 11.1 Save

担当：

```text
src/simulation.py
└─ save_director_world()
```

director world全体をYAMLへ保存する。

したがって、次はdirector worldの一部として自然に保存される。

```text
actor_operations
operation_transition_history
actor_memories
actor_beliefs
```

## 11.2 Load

担当：

```text
src/simulation.py
└─ load_director_world()
```

YAMLを読み、dictを返す。

ただし、この時点ではまだruntimeの正本へ正式採用されていない。

## 11.3 World adoption

担当：

```text
HUDCallbacks.on_load()
```

loaded worldを次へ差し替える。

```text
ctx.director_world
game_state["director_world"]
game_state["world"]
```

したがって、GM-AI内では次を区別する必要がある。

```text
load
≠ world adoption
```

```text
load
= 保存データをdictとして読み出す

world adoption
= そのdictを現在のauthoritative runtime worldとして採用する
```

## 11.4 Catch-up

world adoption後に次の順で実行される。

```text
project_pending_rc_memories()
↓
project_pending_rc_beliefs()
```

つまり、保存されたtransition historyやMemoryが存在する一方で投影結果が欠落している場合、load時に補完できる。

---

# 12. CURRENT：Operation UI表示

担当：

```text
HUDCallbacks.refresh_hud()
```

主な表示経路：

```text
get_active_operation()
↓
format_operation_summary()
↓
DirectorHUD.set_operation_summary()
```

また同じrefresh内で、

```text
build_perceived_world()
build_rc_context_bundle()
generate_rc_advisory()
```

なども呼ばれ、Intelligence PanelやAction候補が更新される。

ただし、`refresh_hud()`は完全なread-only処理ではない。

冒頭で次を呼んでいる。

```text
sync_actor_view_to_legacy()
```

これによりactive actorのviewがlegacy fieldへ同期される。

主なmutation：

```text
game_state["current_location"]
world["affordances"]["discoveries"]
world["affordances"]["spent_opportunities"]
```

したがって現時点では、

```text
HUD refresh
≠ 純粋なrendering
```

である。

これは60-0Bの「隠れたworld更新」整理における重要項目となる。

---

# 13. CURRENT：Operation proposal

## 結論

現行には、明示的な`OperationProposal` schemaは存在しない。

現在proposalに近い役割を部分的に担うのは次である。

```text
Directorが表示するstart_inquiry_operation候補
RC_AIが出すpreferred action advisory
```

ただし、これらはOperationそのものの提案ではない。

```text
start_inquiry_operation候補
= Operation開始Actionの候補

RC advisory
= 実行したいActionの提案
```

現行RC_AIは、すでに存在するactive inquiry Operationを読み、

```text
choose_first_inquiry_target
```

をpreferred actionとして提案する。

RC_AIが次のようなものを生成しているわけではない。

```text
proposal_id
operation_type
goal
priority
reason
initial_phase
initial_mini_goal
termination conditions
```

したがって現状は次の整理になる。

```text
Operation proposal schema
= 未実装

Operation開始Action候補
= 実装済み

Action advisory
= 実装済み
```

---

# 14. CURRENT：ActionPipelineの現状責務

`ActionPipeline.request_action()`は現在、上位経路として非常に多くの責務を扱う。

```text
Action ID／spec取得
actor解決
requirements確認
TPO execution gate
Action実行
effects
Operation progression
transition event
RC Memory
RC Belief
Operation start
time advance
emotion同期
Director tick
MicroGoal更新
affordance評価
action log
RO recommendation
scene graph emission
clock表示
HUD refresh
ActionExecutionOutcome
```

## 現状の強み

```text
一つの関数を上から読むと、
ゲーム内Action成功後の処理順を追える
```

## 現状の弱み

```text
Operation lifecycle以外の責務も非常に多い
例外境界が増えている
開始と進行の関係が読み取りにくい
projection chainがPipeline内部へ直書きされている
UI refreshまで同一経路に含まれる
```

ActionPipelineは、現行の一本道を守る上では重要である。

ただし、現在のまま責務を増やし続けることは難しい。

---

# 15. CURRENT：失敗時の境界

現行処理は全面的なtransactionではない。

## 15.1 Action effects失敗

```text
effects失敗
→ progressionを呼ばない
→ transitionなし
→ Memoryなし
→ Beliefなし
```

## 15.2 progression失敗

```text
Action effects成功
→ progression例外
→ Action effectsは残る
→ Action自体を失敗扱いへ戻さない
```

## 15.3 transition保存失敗

```text
Operation progression成功
→ transition保存失敗
→ 更新済みOperationは残る
```

## 15.4 Memory投影失敗

```text
transition event保存成功
→ Memory失敗
→ eventは残る
→ 後のcatch-upで再投影可能
```

## 15.5 Belief投影失敗

```text
Memory保存成功
→ Belief失敗
→ Memoryは残る
→ 後のcatch-upで再投影可能
```

現行は次のモデルである。

```text
段階的な部分成功
＋
下流projectionのcatch-up
```

これは意図された回復可能性を持つ一方、Operation lifecycle全体が一つのatomic transactionではないことを意味する。

---

# 16. OBSERVATION：Start／Progression二段構造

## 16.1 二つのActionに分かれていること自体

次はゲーム上の別の意思決定である。

```text
聞き込みを開始する
聞き込み先を選ぶ
```

したがって、

```text
start_inquiry_operation
choose_first_inquiry_target
```

を一つのActionへ統合する必要はない。

二段構造自体は自然である。

## 16.2 現在の問題

問題はActionが二つあることではなく、ActionPipeline内の順序である。

```text
すべての成功Action
→ progressionを評価
→ 必要ならOperationを開始
```

このため、開始Actionに対しても次が発生する。

```text
no_active_operation
→ その後start
```

これは機能上の不具合ではない。

ただし、次の点で分かりにくい。

* Operation開始Actionなのに、開始前に進行判定される
* `no_active_operation`が異常なのか正常なのか、文脈を知らないと分からない
* 将来「既存Operationを完了し、同じActionで次Operationを開始する」場合の順序が曖昧
* 中断、切替、破棄を追加するとActionPipelineの分岐が増える

---

# 17. OBSERVATION：現行責務のレイヤー分類

## Blueprint Intelligence寄り

```text
scenario上のOperation意味
perceived_world
Memoryの意味化
Belief
RCContextBundle
intent
advisory
将来のOperation proposal
```

## Machine Core寄り

```text
latest worldでのexecution gate
Action effects
Operation instance生成
active Operation競合確認
Operation phase／MiniGoal進行
transition event
idempotency
authoritative state mutation
```

## Adapter／Persistence寄り

```text
YAML save/load
world adoption
HUD表示
manual advisory adoption
将来のUnity／mobile接続
```

## 現在混在している場所

### Director

```text
候補生成
＋
実行直前の決定論gate
```

### ActionPipeline

```text
Action実行
＋
Operation lifecycle
＋
projection
＋
time
＋
logging
＋
scene
＋
UI refresh
```

### HUDCallbacks

```text
UI表示
＋
manual adoption
＋
world adoption
＋
catch-up
＋
legacy state同期
```

---

# 18. CURRENT：Read／Write／Projection暫定分類

| 分類                            | 主なmodule／function                                                                         |
| ----------------------------- | ----------------------------------------------------------------------------------------- |
| authoritative writer          | `action_effects.py`、`action_registry.py`、`actor_operations.py`、`operation_progression.py` |
| objective record writer       | `operation_transition_history.py`                                                         |
| projection writer             | `rc_memory.py`、`rc_belief.py`                                                             |
| read-only builder             | `perceived_world.py`、`rc_context.py`、`rc_ai.py`                                           |
| candidate builder             | `director/director.py`                                                                    |
| execution coordinator         | `ui/action_pipeline.py`                                                                   |
| adoption／catch-up coordinator | `ui/hud_callbacks.py`                                                                     |
| persistence adapter           | `simulation.py`                                                                           |
| UI adapter                    | `hud_callbacks.py`、`director_hud.py`                                                      |
| schema／definition             | `action_model.py`、`action_definitions.py`、scenario pack                                   |
| characterization contract     | `tests/test_hud_actions.py`および各domain test                                                |

注意：

```text
HUDCallbacks.refresh_hud()
```

はlegacy同期mutationを含むため、完全なread-only builderには分類できない。

---

# 19. 本日確定する事項

## CURRENTとして確定

1. active Operationのauthoritative ownerは`actor_operations`
2. Operation開始metadataは独立Operation定義ではなくActionSpecに付属している
3. 現行には明示的なOperation proposal schemaがない
4. Directorは候補生成と実行gateの両方を担当している
5. ActionPipelineが現行の上位実行coordinatorである
6. Operation progressionはAction effects成功後に呼ばれる
7. progression resultはtransientな内部resultである
8. transition eventは更新後Operationと照合された客観記録である
9. Memoryはobjective eventからのactor-relative projectionである
10. BeliefはMemoryからのactor-relative current snapshotである
11. Operation開始Actionでもprogression評価が先に行われる
12. Start／Progressionの二Action構造自体は自然である
13. 問題は二段構造ではなく、処理順と上位統括位置である
14. loadとworld adoptionは別処理である
15. load後catch-upはMemory→Beliefの順である
16. HUD refreshは現状完全なread-only処理ではない
17. 現行は全面transactionではなく段階的部分成功モデルである
18. event／Memory／Beliefの下流失敗は、上流の成功を巻き戻さない
19. Session 59黄金経路はSession 60以降も最重要characterization contractとして保護する

---

# 20. DEFERRED：本日はまだ決めない事項

以下は次回以降に比較・決定する。

```text
現状維持案
開始Action／進行ActionをActionPipelineで分岐する案
Lifecycle Coordinatorを導入する案
```

また、次も本日は確定しない。

```text
Lifecycle Coordinatorのmodule名
Lifecycle Coordinatorのreturn schema
OperationStarted eventを新設するか
Operation startとprogressionのどちらを先に評価するか
同一Actionで進行と開始の両方を許すか
Operation proposal schema
Plannerの具体的なinterface
ActionPipelineからprojection chainをいつ外すか
world adoptionをHUDCallbacksからいつ移すか
transaction／rollback方針
Operation instance identity刷新
```

---

# 21. 次回の再開地点

次回は、以下の三案を同じ評価軸で比較する。

## 案A：現状維持

```text
全成功Action
→ progression評価
→ 必要ならOperation start
```

## 案B：ActionPipelineで開始／進行を分岐

```text
開始Action
→ Operation start

通常Action
→ Operation progression
```

## 案C：Lifecycle Coordinator

```text
Action effects成功
→ Operation Lifecycle Coordinator
   ├─ 既存Operationを進める
   ├─ 新Operationを開始する
   ├─ 両方行う
   └─ 何もしない
```

比較軸：

```text
処理順の読みやすさ
domain関数の独立性
将来の中断／切替／破棄への拡張性
ActionPipelineの責務削減
黄金経路の維持
部分成功／catch-upとの整合
Plannerを後から差し込めるか
テストしやすさ
Unity Adapterから同じCoreを呼べるか
```

目標は、開始処理と進行処理を一つの巨大関数へ潰すことではない。

```text
上位からはlifecycleの順序が一か所で読める

内部では
start_operation_once()
advance_operation_after_action()
record_operation_transition()
などの狭いdomain処理を維持する
```

という境界を検討する。
