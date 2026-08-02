# GM-AI Session 60-1

## OperationRuntime抽出・実装仕様策定依頼

あなたはChat（Work）として、repositoryの現行コードを確認し、Session 60-1の安全な実装仕様を策定してください。

この依頼では、まず現行コードに基づく調査と仕様策定を行ってください。

**この段階では実装・commit・pushを開始しないでください。**

---

# 1. 基準branch

現在の作業branch：

```text
design/session60-0-operation-lifecycle-boundary-v01
```

Session 60-0 baseline commit：

```text
32b177b9180c9b774e4e9302a396be059a0d50cc
```

保護対象として残っているローカル変更：

```text
M .gitignore
M config.yml
?? AGENTS.md
?? general_documents/study_notes/README.md
```

これらは変更、削除、stash、reset、restore、stage、commitしないでください。

禁止：

```text
git clean
git reset --hard
git stash
git restore .
git checkout -- .
git add .
git add -A
git commit -a
force push
```

---

# 2. Session 60-1の直近目標

> ActionPipelineからOperationの意味・進行・記録責務を外し、ActionOutcomeをOperationRuntimeへ渡す形へ整える。

## ミニゴール

> 既存のOperation開始・進行・transition記録をOperationRuntimeへまとめ、ActionPipelineから一回呼ぶ形にする。

---

# 3. 目標アーキテクチャ

将来の目標形は次です。

```text
GameCommandService.execute(command)
  │
  ├─ ActionPipeline.execute(action_request)
  │      └─ ActionOutcome
  │
  ├─ OperationRuntime.apply_action_outcome(outcome)
  │      └─ OperationTransition[]
  │
  ├─ MemoryProjection.apply(transitions)
  │      └─ MemoryRecord[]
  │
  ├─ BeliefProjection.apply(memories)
  │      └─ BeliefUpdate[]
  │
  └─ fresh RCContextBundle生成
```

ただし、Session 60-1では`GameCommandService`をまだ導入しません。

Session 60-1では、現在の`ActionPipeline.request_action()`を上位入口として維持したまま、Operation lifecycleの統括責務だけを`OperationRuntime`へ抽出します。

暫定形：

```text
ActionPipeline.request_action()
  │
  ├─ Actionの検証・effects適用
  │
  ├─ ActionOutcome相当を構築
  │
  ├─ OperationRuntime.apply_action_outcome(...)
  │      └─ OperationTransition[]
  │
  ├─ 現行のMemory投影
  ├─ 現行のBelief投影
  └─ time／log／scene／HUD refresh
```

---

# 4. Session 60-1で移す責務

現在`ActionPipeline.request_action()`に直接書かれている次のOperation関係の統括処理を調査してください。

```text
advance_operation_after_action()
build_operation_transition_event()
record_operation_transition()
_start_operation_from_spec()
```

Session 60-1では、これらの呼び出しと処理順の統括を、原則として`OperationRuntime`へまとめる想定です。

ただし、既存の狭いdomain関数そのものを巨大な一関数へ統合しないでください。

目標：

```text
ActionPipeline
→ OperationRuntimeを一回呼ぶ

OperationRuntime
├─ 既存Operationの進行を評価
├─ 必要ならtransitionを生成・保存
├─ ActionSpecに開始metadataがあればOperationを開始
└─ commit済みOperationTransitionのlistを返す
```

---

# 5. Session 60-1で維持する責務

以下は当面ActionPipeline側に残す想定です。

```text
Actionの取得
actorの解決
requirements確認
Director execution gate
Action effectsの実行
Memory projection
Belief projection
time advance
Director tick
MicroGoal処理
affordance処理
action log
scene emission
HUD refresh
既存ActionExecutionOutcomeの外部互換性
```

ただし、現行コードを調査して、OperationRuntime抽出に伴い最低限必要な変更があれば明示してください。

---

# 6. Session 60-1で行わないこと

以下は今回のscope外です。

```text
GameCommandService本導入
ActionPipeline公開APIの全面変更
directoryの大規模移動
OperationStore本導入
OperationInstance本導入
MemoryProjectionのclass化
BeliefProjectionのclass化
HCP dashboard
Operation Trace Spine
新しい汎用event bus
Operation ID刷新
save schema変更
migration
Unity連携
mobile連携
startup auto-load
```

---

# 7. 最重要方針：責務抽出であり、意味変更ではない

Session 60-1では、既存挙動を維持してください。

現行では概ね次の順です。

```text
Action effects
→ Operation progression
→ transition生成・保存
→ Memory
→ Belief
→ Operation start
```

OperationRuntimeへ抽出する際も、まずは現行の開始・進行順序と意味を保護してください。

特に、

```text
start_inquiry_operation
```

では、現行どおり開始前のprogressionが`no_active_operation`となった後、Operationを開始します。

Session 60-1でこの順序が不自然に見えても、責務抽出と同時に意味変更しないでください。

順序変更は、抽出後に独立した設計判断として扱います。

新しい`OperationStarted` eventも、今回は追加しないでください。

---

# 8. OperationRuntimeの位置づけ

`OperationRuntime`は、Operation lifecycleを統括するDeterministic Machine Core側のcomponentです。

中心責務：

```text
Actionの確定結果を受け取る
現在のOperation stateを読む
Operation progressionを評価する
Operation開始metadataを評価する
必要なdomain writerを正しい順で呼ぶ
commit済みtransitionを返す
```

持たせない責務：

```text
Action effectsの実行
RC Memoryの意味化
RC Belief形成
ContextBundle生成
RC_AI advisory
HUD更新
save/load
HCP表示
```

`OperationRuntime`が既存のdomain ruleを吸収して巨大化するのではなく、既存の狭い関数を統括する形にしてください。

---

# 9. ActionOutcomeに関する調査

現行の`ActionExecutionOutcome`または相当するreturn構造を確認してください。

OperationRuntimeへ渡すために、最低限どの情報が必要かを整理してください。

候補：

```text
action_id
actor_id
executed
reason
source
effects_committed
value
Operation開始metadata
```

ただし、Session 60-1で新しい大規模schemaを確定する必要はありません。

次の選択肢を比較してください。

### 案A

既存`ActionExecutionOutcome`を最小拡張し、OperationRuntimeへ渡す。

### 案B

ActionPipeline内部だけで使う暫定的なOperationRuntime inputを作る。

### 案C

既存outcome＋ActionSpec＋actor_idを個別引数としてRuntimeへ渡す。

以下の観点から推奨案を提示してください。

```text
将来のGameCommandServiceへの移行
既存外部API互換性
変更範囲
型の意味の明確さ
テスト容易性
暫定構造の負債
```

---

# 10. Runtimeを呼ぶ条件に関する調査

次の二案を比較してください。

### 案1

Action effects成功時だけ`OperationRuntime`を呼ぶ。

### 案2

成功／失敗を含むすべての`ActionOutcome`をRuntimeへ渡し、Runtime側がno-opを判断する。

Session 60-1では挙動維持と変更範囲の小ささを優先しますが、Session 60-2の目標形も考慮して推奨を提示してください。

---

# 11. OperationRuntimeの戻り値

将来形では、

```text
OperationTransition[]
```

を返す想定です。

現行では最大1件でも、将来的には一つのActionOutcomeから複数のOperation transitionが発生する可能性があります。

ただし、現在の`operation_transition_history`へ保存されたcommit済みeventと、まだ保存されていない候補eventを混同しないでください。

戻り値に含めるものは、原則として、

```text
authoritative Operation更新後に照合され、
operation_transition_historyへの記録が完了したtransition
```

としてください。

Operation開始は現行transition historyに記録されないため、今回の戻り値に新規started eventを捏造しないでください。

---

# 12. 調査対象

最低限、次を確認してください。

```text
src/ui/action_pipeline.py
src/action_model.py
src/action_registry.py
src/action_effects.py
src/actor_operations.py
src/operation_progression.py
src/operation_transition_history.py
src/rc_memory.py
src/rc_belief.py
src/rc_context.py
src/simulation.py
src/ui/hud_callbacks.py
data/director/packs/cop_trickster.yml

tests/test_operation_progression.py
tests/test_operation_transition_history.py
tests/test_hud_actions.py
tests/test_rc_context.py
```

必要に応じて関連する呼び出し元やtestも確認してください。

---

# 13. 黄金経路

必ず次の既存挙動を保護してください。

```text
start_inquiry_operation
→ inquiry Operation start
→ choose_first_inquiry_target
→ effects
→ inquiry_target_chosen
→ Operation start → target_selected
→ transition event
→ RC Memory
→ RC Belief
→ fresh RCContextBundle
→ RC_AI no_safe_action
```

また、次も維持してください。

```text
Action失敗時はOperation進行なし
gate拒否時はOperation進行なし
同じActionの重複評価で二重進行しない
transition eventを二重記録しない
Memoryを二重生成しない
Belief source_memory_idsを重複させない
actor間でOperation／Memory／Beliefを混線させない
HUD refreshやBundle再生成だけでは書き込みを発生させない
save/load後も整合を維持する
```

---

# 14. Human Control Planeとの関係

Session 60-1ではHCPを実装しません。

ただし、将来HCPが次を観測できる境界になるよう考慮してください。

```text
ActionOutcome
OperationRuntimeのresult
OperationTransition
Memory projection result
Belief projection result
```

HCPは正本を書き換えず、各段階のresultとauthoritative stateを観察します。

OperationRuntimeのAPIや戻り値を、HCP専用の表示情報で汚染しないでください。

Machine Coreの客観resultをHCPが後から観察できる形を優先してください。

---

# 15. 仕様策定結果として提出してほしいもの

実装前に、以下を報告してください。

## A. 現行call graph

```text
ActionPipeline.request_action()
から
Operation開始・進行・transition・Memory・Belief
までの正確な呼び出し順
```

## B. 現行責務の抽出対象

ActionPipelineから何を外し、何を残すか。

## C. 新規または変更module案

候補例：

```text
src/operation_runtime.py
```

既存project構造に照らして最適な配置を提案してください。

大規模directory移動は行わないでください。

## D. API案

最低限、次のsignature候補を比較してください。

```python
OperationRuntime.apply_action_outcome(...)
```

またはfunction型であるべきなら、その案も提示してください。

classを導入する理由が弱い場合、無理にclass化しないでください。

## E. ActionOutcomeの扱い

既存schemaの最小拡張、内部input、個別引数のどれを採用するか。

## F. 開始／進行順序

現行順序を正確に示し、Session 60-1でどのように保持するか。

## G. 戻り値

commit済み`OperationTransition[]`をどう返すか。

## H. Memory／Beliefとの接続

Runtimeの戻り値を、現行Memory／Belief処理へどう渡すか。

## I. 変更予定ファイル

追加・変更する可能性のある全ファイル。

## J. テスト計画

既存testのうちそのまま使うもの、新規追加・更新が必要なもの。

## K. リスク

特に次を確認してください。

```text
Operation start順序の意味変更
transition二重記録
Memory／Belief二重投影
ActionExecutionOutcome互換性
Action失敗時の部分成功
HUD refreshによる副作用
actor混線
save/load
```

## L. 実装単位

一つのcommitで安全か、複数commitへ分けるべきかを提案してください。

---

# 16. 最終確認

今回の作業は、

```text
ActionPipelineを廃止する
```

ことではありません。

また、

```text
Operation domain ruleを全部書き直す
```

ことでもありません。

目標は、

```text
ActionPipeline内に直書きされた
Operation開始・進行・transition記録の統括順序を
OperationRuntimeという明示的な境界へ抽出する
```

ことです。

現行挙動を維持した、最小で安全な仕様を策定してください。
