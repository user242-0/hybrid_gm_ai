# GM-AI 設計補足：MicroGoal と Operation.MiniGoal の関係

作成日: 2026-06-30  
目的: `gm_ai_tpo_operation_design_260630.md` の補足資料として、MicroGoal / Operation / Operation.MiniGoal の役割と先立つ順番を整理する。
[HUDアクション→オペレーション](gm_ai_tpo_operation_design_260630.md)
---

## 1. この文書の結論

GM-AIにおいて、MicroGoal と Operation.MiniGoal は競合する概念ではない。  
両者は階層が異なる。

```text
MicroGoal
= RC / プレイヤーに見せる道しるべ。
  「何を達成したいか」を示す。

Operation
= MicroGoalを達成するため、または物語上の作戦を進めるための文脈。
  直接世界を動かす実行単位ではない。

Operation.MiniGoal
= Operationの現在フェーズから生まれる小目標。
  「今どの段階を進めるか」を示す。
```

山登りに例えるなら、以下の関係になる。

```text
山頂標識:
  MicroGoal

登山ルート:
  Operation

〇合目標識:
  Operation.MiniGoal
```

つまり、MicroGoalは大きな道しるべ、Operation.MiniGoalは作戦内の小さな道しるべである。

---

## 2. 基本方針

当面の実装では、以下の順番を基本とする。

```text
MicroGoal
  ↓
HUD Action
  ↓
Operation開始
  ↓
Operation.MiniGoalを進める
  ↓
MicroGoal達成
```

つまり、まずMicroGoalがあり、それを達成するためにHUDアクションが提示され、そのHUDアクションを選ぶことでOperationが立ち上がる。

ただし、将来的には逆向きの流れもあり得る。

```text
Operation進行
  ↓
重要なdiscovery獲得
  ↓
ROが次のMicroGoal候補を提案
  ↓
新しいMicroGoalが立ち上がる
```

したがって、設計としては双方向を許容するが、MVPでは `MicroGoal → Operation → Operation.MiniGoal` を基本とする。

---

## 3. MicroGoal と Operation.MiniGoal の違い

| 概念 | 役割 | UI上の見せ方 | 実装上の性質 |
|---|---|---|---|
| MicroGoal | RCの現在の道しるべ | 大きく表示する | actor単位で1つを基本にする |
| Operation | 作戦文脈 | 必要なら表示する | active / suspended / completed を持つ |
| Operation.MiniGoal | Operation内の現在小目標 | 小さく表示する、またはHUD候補に反映 | phaseから生成される |
| HUD Action | 高レベル候補 | 選択肢として表示 | Operationを開始・更新・分岐できる |
| GUI Action | 具体行動 | 即時実行ボタン | location / target / same-location requirement で厳格判定 |

重要なのは、MicroGoalを「実行可能アクションそのもの」として扱わないことである。

```text
MicroGoal = 目指す状態
GUI Action = 今すぐ実行できる行動
Operation.MiniGoal = その状態に近づくための現在フェーズ
```

---

## 4. なぜ分ける必要があるか

従来の設計では、HUDアクション候補の一つがMicroGoalとして選ばれていた。

この設計はシンプルだが、以下の問題が出る。

```text
- MicroGoalに選ばれたアクションが今すぐ実行できない場合、「未設定」になりやすい
- MicroGoalが「目的」なのか「行動」なのか曖昧になる
- 複数ターン/複数locationにまたがる作戦を表現しにくい
- HUDアクション→Operationの導入時に役割が競合して見える
```

そこで、MicroGoalを「道しるべ」、Operationを「作戦文脈」、Operation.MiniGoalを「作戦内の現在小目標」と分ける。

これにより、MicroGoalが今すぐ実行可能でなくても問題なくなる。

例:

```text
MicroGoal:
  真実を一件だけ報告

Operation:
  報告準備中

Operation.MiniGoal:
  重要な手がかりの確認を取る
```

この場合、まだ報告そのものはできなくても、MicroGoalは有効であり続ける。

---

## 5. 具体例：真実を一件だけ報告

### 5.1 MicroGoal

```yaml
MicroGoal:
  id: report_one_truth
  actor_id: detective
  label: 真実を一件だけ報告
  status: active
  purpose: 事件の真相を一段階だけ公的記録に近づける
```

MicroGoalは「何を達成したいか」を示す。  
この時点では、報告が今すぐ可能かどうかは問わない。

---

### 5.2 HUD Action

```yaml
HUD Action:
  id: start_reporting_operation
  actor_id: detective
  label: 報告に向けて確認を取る
  action_layer: HUD
  starts_operation: reporting_a_single_truth
  parent_microgoal_id: report_one_truth
```

HUDアクションは、MicroGoalを達成するための高レベル候補である。  
選択されるとOperationを開始する。

---

### 5.3 Operation

```yaml
Operation:
  id: reporting_a_single_truth
  actor_id: detective
  type: report
  label: 真実を報告する準備
  target_id: trickster
  status: active
  phase: obtain_confirmation
  priority: 80
  created_from: microgoal
  parent_microgoal_id: report_one_truth

  allowed_modes:
    - FREEZE
    - WITNESS

  candidate_locations:
    - 警察署
    - 拠点_ボロアパート

  preferred_action_tags:
    - keep_record
    - report
    - send_message
    - obtain_confirmation

  required_discoveries:
    important_clue_known: ok
    obtain_confirmation: yet

  mini_goal:
    id: obtain_confirmation_for_truth_report
    label: 重要な手がかりの確認を取る
    status: active
```

Operationは「真実を一件だけ報告」というMicroGoalに向かうための作戦文脈である。  
Operationそのものは、世界を直接動かす実行単位ではない。

---

### 5.4 GUI Action

現在locationやtarget条件を満たしたときだけ、GUIアクションが出る。

例:

```yaml
GUI Action:
  id: send_report
  label: 報告する
  required_location:
    - 警察署
    - 拠点_ボロアパート
  required_discoveries:
    important_clue_known: ok
    obtain_confirmation: ok
```

このように、MicroGoalが「報告したい」という目的を持ち、Operationが「報告準備」という文脈を持ち、Operation.MiniGoalが「確認を取る」という現在小目標を持つ。  
GUIアクションの「報告する」は、条件が揃ったときだけ実行可能になる。

---

## 6. MicroGoalが先か、Operationが先か

結論として、どちらもあり得る。

ただし、現段階では以下の優先順が自然である。

### Phase 1: MicroGoal先行型

```text
MicroGoalが先に立つ
  ↓
そのMicroGoalを達成するためのHUDアクションが出る
  ↓
HUDアクションからOperationが立つ
  ↓
Operation.MiniGoalを進める
  ↓
MicroGoal達成
```

これはプレイヤーに道しるべを与えやすく、既存のMicroGoal実装とも相性がよい。

### Phase 2: Operation完了から次MicroGoalを生む

```text
Operationを進める
  ↓
discoveryや状況変化が起きる
  ↓
ROが次のMicroGoal候補を提案する
  ↓
新しいMicroGoalが選ばれる
```

これはよりGM-AIらしいが、MVPでは後回しでよい。

---

## 7. ROとの関係

ROは、MicroGoal / Operation / Operation.MiniGoal の橋渡し役になる。

ROが見るもの:

```text
- actor_id
- current location
- current time
- actor state
- discovery
- current MicroGoal
- active Operation
- Operation phase
- Operation.MiniGoal
- recent logs
```

ROが提案するもの:

```text
- Operationを開始するHUDアクション
- Operationを継続するHUDアクション
- Operationを中断するHUDアクション
- Operationを再開するHUDアクション
- Operation.MiniGoalを更新する提案
- MicroGoal達成に近づくGUIアクション候補
- Operation完了後の次MicroGoal候補
```

例:

```text
MicroGoal:
  真実を一件だけ報告

Operation:
  真実を報告する準備

Operation.MiniGoal:
  重要な手がかりの確認を取る

RO提案:
  - ボロアパートで確認を取る
  - 警察署に戻って記録を整理する
  - まだ報告せず、証言の裏を取る
```

ROは自動操縦ではなく、作戦参謀として機能する。

---

## 8. UI表示案

プレイヤーに見せる場合、以下のような階層表示が分かりやすい。

```text
MicroGoal:
  真実を一件だけ報告

Operation:
  真実を報告する準備

MiniGoal:
  重要な手がかりの確認を取る
```

または省略表示なら、MiniGoalだけをHUD候補に反映してもよい。

```text
HUD候補:
  - ボロアパートで確認を取る
  - 警察署で記録を整理する
  - まだ報告せず、証言を照合する
```

---

## 9. 最小実装案

既存実装を壊さないため、最初は以下だけでよい。

```yaml
actor:
  id: detective

  microgoal:
    id: report_one_truth
    label: 真実を一件だけ報告
    status: active

  active_operation:
    id: reporting_a_single_truth
    parent_microgoal_id: report_one_truth
    status: active
    phase: obtain_confirmation
    mini_goal:
      id: obtain_confirmation_for_truth_report
      label: 重要な手がかりの確認を取る
      status: active
```

MVPでやること:

```text
1. MicroGoalはactor単位で1つを維持する
2. active_operationをactor単位で1つ持たせる
3. active_operationにはparent_microgoal_idを持たせる
4. active_operationにはphaseとmini_goalを持たせる
5. HUD候補生成時にMicroGoalとOperation.MiniGoalの両方を見る
6. GUIアクションは今まで通り厳格な実行条件で出す
```

まだやらなくてよいこと:

```text
- 複数MicroGoalの同時管理
- 複数Operationの本格並行管理
- Operationの完全自動実行
- Operation完了から次MicroGoalを自動生成する高度なRO
```

---

## 10. 設計原則

この補足設計の中心原則は以下である。

```text
MicroGoalは、目的である。
Operationは、その目的に向かう作戦文脈である。
Operation.MiniGoalは、その作戦の現在フェーズである。
GUI Actionは、今この場で実行できる具体行動である。
HUD Actionは、MicroGoalやOperationを進めるための高レベル候補である。
ROは、それらの橋渡しをする作戦参謀である。
```

最も重要な一文:

```text
MicroGoalは「山頂標識」、Operation.MiniGoalは「〇合目標識」である。
```

この整理により、既存のMicroGoal設計を殺さずに、HUDアクション→Operationの設計を導入できる。

---

## 11. 実装セッションへの持ち込み要約

```text
MicroGoalとOperation.MiniGoalは分ける。

MicroGoalは、RC/プレイヤーに見せる大きな道しるべ。
Operationは、そのMicroGoalを達成するための作戦文脈。
Operation.MiniGoalは、Operationの現在フェーズから生まれる小目標。

当面は MicroGoal → HUD Action → Operation → Operation.MiniGoal → MicroGoal達成 の流れを基本にする。
将来的には Operation完了やdiscovery獲得から、ROが次のMicroGoal候補を提案する流れも許容する。

MVPではactorごとにMicroGoalを1つ、active_operationを1つ持たせ、active_operationにparent_microgoal_id / phase / mini_goalを持たせる程度でよい。

Operationは自動実行される長い行動ではなく、長い文脈である。
MicroGoalは山頂標識、Operation.MiniGoalは〇合目標識である。
```
