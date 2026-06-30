# GM-AI TPO縦切り前 設計メモ
## current_target / same-location / GUI-HUD / Operation / RO 整理

作成日: 2026-06-30  
用途: GM-AI 実装セッション共有用メモ  
対象セッション: Session51-A 以降 / TPOコンテンツ縦切り前の設計整理

---

## 0. このメモの目的

Session50で、RC別 `location` / `discovery` が導入された。

これにより、刑事RCと愉快犯RCが別々の場所にいて、別々の発見を持つことができるようになった。

次の課題は、RC同士が互いを `current_target` として認識している場合に、別locationにもかかわらずGUI上で「話す」「戦う」などの直接行動が出てしまう問題である。

このメモでは、TPO縦切り前に以下を整理する。

- `current_target` はグローバルで1つか、actor別に持つべきか
- `talk` / `combat` / `arrest` などの直接行動に `same-location requirement` を必須にすべきか
- 別locationの相手に対する行動はGUIではなくHUDで表現すべきか
- GUIアクションとHUDアクションの役割分担
- 将来のHUDアクション合成 / GUIアクションコンパイルを壊さないために、今どこまで実装すべきか
- HUDアクションをOperationとして扱う設計
- OperationとRO（Reversible Operator）の関係

---

# 前半: TPO縦切り前の基本五題

---

## 1. current_target はグローバルで1つか、actor別に持つべきか

### 結論

`current_target` は actor別に持つべきである。

グローバルに1つだけ持つと、複数RCが別々の場所・別々の目的・別々の認識を持った時点で破綻しやすい。

特に、刑事と愉快犯が互いを意識しているが別locationにいる場合、

- 刑事の target は愉快犯
- 愉快犯の target は刑事
- しかし両者は同じ場所にはいない

という状態が自然に発生する。

このとき `current_target` がグローバル1つだと、GUI生成側が「対象がいる」と誤認し、目の前にいない相手に対して「話す」「戦う」などを出してしまう危険がある。

### 推奨整理

```text
actor.current_target
= そのRCが現在、意識・追跡・警戒・妨害している対象

world.current_focus
= 演出・ログ・シーン上の注目対象

gui.selected_target
= GUI上で現在選択されている対象

hud.narrative_target
= HUD候補生成上の物語的対象
```

直接行動の判定に使ってよいのは、基本的には以下である。

```text
actor.current_target
gui.selected_target
actor.location
target.location
```

`world.current_focus` は便利だが、直接行動の根拠にはしない。

### 重要な定義

`current_target` は「目の前にいる相手」ではない。

```text
current_target
= そのRCが今、意識している相手
```

したがって、刑事が愉快犯を `current_target` にしていても、別locationなら「話す」「戦う」「逮捕する」は出ない。

その代わりHUDで、

- 逃走経路を推理する
- 足取りを追う
- 目撃証言を照合する
- 現場を封鎖する

などが出る。

---

## 2. talk / combat は same-location requirement を必須にすべきか

### 結論

`talk` / `combat` / `arrest` などの直接行動には、原則として `same-location requirement` を必須にすべきである。

```text
talk_face_to_face = same-location required
combat            = same-location required
arrest            = same-location required
```

特に `combat` と `arrest` は、原則として同じ場所にいる場合だけ成立するべきである。

### talk の例外

`talk` には将来的に例外がある。

たとえば、

- 電話する
- 無線で呼びかける
- メールを送る
- 犯行声明に応答する
- 交渉メッセージを送る

などは、対面の `talk` ではなく、別種の通信アクションとして扱う。

```text
talk_face_to_face  = same-location required
call_by_phone      = phone channel required
send_message       = known_contact required
broadcast_warning  = authority / media channel required
```

つまり、GUIに出る「話す」は基本的に対面行動とする。

別locationの対象に働きかける場合は、「話す」ではなく、

- 連絡する
- 呼びかける
- メッセージを送る
- 挑発する
- 警告する

などの別アクションにする。

---

## 3. 別locationにいる相手への行動はGUIではなくHUDで表現すべきか

### 結論

別locationにいる相手への干渉は、原則としてGUIアクションではなくHUDアクションで表現するのが自然である。

別locationの愉快犯に対して刑事ができることは、「殴る」「話す」「逮捕する」ではない。

しかし、物語的には戦える。

### 刑事側の例

- 足取りを追う
- 逃走経路を推理する
- 監視カメラの時刻を照合する
- 目撃者の証言を整理する
- 現場を封鎖する
- 次に現れそうな場所へ先回りする
- 容疑者の現在地を特定する
- 逮捕に向けて包囲を狭める

### 愉快犯側の例

- 偽の痕跡を残す
- 目撃証言を撹乱する
- 人混みに紛れる
- 顔を見られた店を避ける
- 監視カメラの死角へ移動する
- 刑事の推理を遅らせる
- 逃走経路を変更する

これらは、直接行動ではなく物語行動である。

したがってGUIではなくHUDに出す。

### 原則

```text
直接行動は、空間的に制限する。
物語行動は、情報的に制限する。
```

つまり、

```text
話す / 戦う / 逮捕する
=> 同じ場所にいないとできない

推理する / 撹乱する / 追跡する / 痕跡を残す
=> 同じ場所でなくてもできるが、discovery / TPO / RC状態が必要
```

この整理により、AI側も「知っていること」「いる場所」「現在の状態」に縛られるため、AIチートになりにくい。

---

## 4. GUIアクションは基礎動詞、HUDアクションは高レベル候補、という整理でよいか

### 結論

この整理でよい。

より正確には、以下のように分ける。

```text
GUIアクション
= 今いる場所で、今すぐ実行できる基礎動詞
```

```text
HUDアクション
= RC・TPO・discovery・mode・目的・状態を束ねた高レベル候補
```

### GUIアクションの例

- 話す
- 調べる
- 移動する
- 拾う
- 開ける
- 追いかける
- 拘束する
- 戦う
- 逮捕する

GUIアクションは、条件が厳格であり、実行結果も比較的明確である。

```text
GUI Action
- atomic
- immediate
- strict
- same-location が多い
- 実行結果が明確
```

### HUDアクションの例

- 証言時刻を照合する
- 逃走経路を推理する
- 証拠を隠す
- 偽の痕跡を残す
- 現場を封鎖する
- 逮捕に踏み切る
- 聞き込みを始める
- 刑事の推理を撹乱する

HUDアクションは、単一のGUIアクションに即時変換できるとは限らない。

```text
HUD Action
- strategic / narrative
- time-spanning
- RC-specific
- discovery / TPO / mode に依存
- Operation や MicroGoal を生成する
```

### 重要な補足

HUDアクションは、GUIアクションの上位互換ではない。

GUIは「現場の手」である。  
HUDは「物語の舵」である。

```text
HUDで物語を詰める。
GUIで現場決着する。
```

たとえば、

```text
HUD: 逮捕に踏み切る
```

は即座に逮捕を実行するわけではない。

その結果、

```text
Operation: arrest_flow
MicroGoal: 容疑者の現在地を特定する
HUD: 逃走経路を推理する
GUI: 現場を調べる / 証人と話す / 移動する
```

という流れに入る。

実際の決着としての

```text
GUI: 逮捕する
```

は、同じlocationにいて、証拠条件などを満たした時だけ出る。

---

## 5. 将来のHUDアクション合成 / GUIアクションコンパイルを壊さないために、今どこまで実装すべきか

### 結論

今は、HUDアクション合成エンジンやGUIアクションコンパイルを本格実装しすぎなくてよい。

ただし、将来壊さないための「契約」は先に置くべきである。

### 今入れるべき最小契約

```text
1. current_target を actor別にする
2. talk / combat / arrest に same-location requirement を付ける
3. GUIアクション生成時に can_execute 判定を通す
4. HUDアクションには action_layer / interaction_scope を持たせる
5. 別locationの target には remote_narrative 系HUDだけ出す
6. HUDアクションは Operation を開始・更新できるようにする
7. Operation は GUI候補 / HUD候補 / MicroGoal / RO提案に影響できるようにする
```

### 推奨属性

```text
action_layer: GUI / HUD

interaction_scope:
  same_location
  known_location
  inferred_location
  any_location
  channel

actor_id
target_id
required_discovery
required_location
required_actor_mode
effects
starts_operation
updates_operation
```

### 例

```text
talk:
  action_layer: GUI
  interaction_scope: same_location
```

```text
combat:
  action_layer: GUI
  interaction_scope: same_location
```

```text
arrest:
  action_layer: GUI
  interaction_scope: same_location
```

```text
pursue_trace:
  action_layer: HUD
  interaction_scope: known_or_inferred_location
```

```text
leave_false_trace:
  action_layer: HUD
  interaction_scope: any_location_or_current_location
```

### 実装の優先度

Session51-A / 51-B では、以下を優先する。

```text
優先:
- actor別 current_target
- same-location gating
- GUI/HUDのaction_layer分離
- interaction_scope の導入
- HUDからOperation開始
- OperationがMicroGoalとHUD候補を変える

後回し:
- 完全なHUDアクション合成エンジン
- 完全なGUIアクションコンパイル
- 複数ステップの自動実行
- 複雑なOperation階層
```

---

# 後半: HUDアクションはOperationである

---

## 6. HUDアクションは「即時実行」ではなく「Operation開始・更新」として扱う

### 結論

HUDアクションは、必ずしもGUIアクションに即コンパイルされる必要はない。

むしろ多くのHUDアクションは、

```text
RCの作戦状態
物語の方向
時間幅を持つ行動方針
```

を開始・更新するものとして扱う方が自然である。

つまり、

```text
HUD Action
=> Operation
=> MicroGoal
=> GUI Action候補 / HUD Action候補 / RO提案
```

という流れにする。

---

## 7. HUDアクション / Operation の3分類

HUDアクションから生じるOperationは、大きく3種類に分けられる。

---

### A. すぐGUIアクションに落とせるもの

同じlocationにいて、必要条件も満たしており、即座にGUIアクションへ落とせるもの。

例:

```text
HUD: 目の前の相手に問い詰める
=> GUI: 話す / 尋問する
```

```text
HUD: 容疑者を拘束する
=> GUI: 拘束する
```

この場合、HUDはほぼGUIアクションの文脈つき候補である。

---

### B. 複数ターン / 複数locationにまたがる作戦

中長期の作戦として扱うもの。

例:

```text
HUD: 聞き込みを始める
=> Operation: inquiry
```

```text
HUD: 逮捕に踏み切る
=> Operation: arrest_flow
```

```text
HUD: 刑事の推理を撹乱する
=> Operation: mislead_investigation
```

B型Operationは、単なる方向性だけでは弱い。  
しかし、完全な自動実行シーケンスにするとプレイヤー操作を奪ってしまう。

したがって、B型Operationは以下として扱うのが自然である。

```text
B型Operation
= 方針 + 候補ルート + 次に出やすくなる行動 + 進行状態
```

---

### C. GUIアクションには落ちず、RCの方針・状態、director_worldの状態に影響するもの

即時のGUIアクションにも、明確な複数ステップ作戦にもならず、RCや世界の状態に影響するもの。

例:

```text
HUD: 警戒を強める
=> detective.operation_state = CAUTIOUS
=> director_world.tension +1
```

```text
HUD: 推理を撹乱する
=> trickster.operation_state = MISLEAD
=> detective側に false_discovery が混ざる可能性
=> director_world.confusion +1
```

```text
HUD: 逃走に専念する
=> trickster.focus = ESCAPE
=> escape_score +1
=> 次ターンのtrickster HUD候補が逃走寄りになる
```

C型は「実行」よりも「構え」「姿勢」「物語の圧力」に近い。

---

## 8. Operationは「長い行動」ではなく「長い文脈」

最重要原則:

```text
Operationは、長い行動ではなく、長い文脈である。
```

Operation自体が勝手に世界を動かすのではない。

Operationは、以下に影響する。

- HUD候補
- GUIアクションの意味づけ
- MicroGoal
- RO提案
- discovery生成
- director_worldの状態
- actorの優先行動
- action scoring

### 例: 聞き込みOperation

```text
Operation:
  type: inquiry
  label: 聞き込みを始める
  actor_id: detective
  target_id: trickster
  purpose: 犯人の情報を突き止める
  candidate_locations: 近場A, 近場B, 近場C
  preferred_action_tags: talk, ask_witness, compare_testimony
  phase: location_A
  status: active
```

このOperationがあると、HUDやROは以下を出しやすくなる。

- 近場Aで目撃者に話を聞く
- 近場Bへ移動して聞き込みを続ける
- 証言時刻を照合する
- 聞き込み結果から逃走経路を推理する
- 空腹なら蕎麦屋で腹ごしらえする

ただし、プレイヤー操作RCでは、自動でA→B→Cへ移動して自動で話を聞くことはしない。

Operationは操作を奪わない。  
Operationは候補の出方を変える。

---

## 9. Operation中の分岐・中断・再開

Operation中でも、他の行動や別Operationに分岐できるべきである。

たとえば、刑事が聞き込み中に12時になり、空腹が高まった場合、

```text
active_operation:
  聞き込みを始める

time:
  12:00

actor_state:
  hunger +2
```

ROは以下を提案できる。

```text
1. 聞き込みを続ける
   - hunger +1
   - concentration -1
   - inquiry_progress +1

2. 近くの蕎麦屋で腹ごしらえする
   - inquiry Operation を suspended
   - meal Operation を active
   - hunger -2
   - time +30min
   - 蕎麦屋で新しい証言が出る可能性

3. 署に戻って証言を整理する
   - inquiry Operation を review phase に進める
```

このように、Operation中の脱線は失敗ではない。

GM-AIでは、脱線が物語の分岐になる。

### 推奨状態

```text
actor.operations = 複数持てる
actor.active_operation = 1つだけ
actor.suspended_operations = 一時停止中のOperation
actor.microgoal = active_operationから派生する現在目標
```

現状のMicroGoalが複数持ちでないなら、それでよい。

```text
Operationは複数持てる。
MicroGoalは当面1つでよい。
```

---

## 10. GUIアクションの意味をOperationが染める

GUIアクションは基礎動詞である。

しかし、その意味はOperationによって変わる。

```text
Operation: 聞き込み
GUI: 話す
=> 証言を聞く
```

```text
Operation: 逮捕作戦
GUI: 話す
=> 容疑者を問い詰める
```

```text
Operation: 休憩
GUI: 話す
=> 店員と雑談する
```

```text
Operation: 撹乱
GUI: 話す
=> 嘘の情報を流す
```

つまり、

```text
GUIアクションは基礎動詞。
Operationは、その基礎動詞の物語上の意味を決める文脈。
```

これはGM-AIにおけるGUI/HUD/Operationの大きな接続点である。

---

## 11. RO（Reversible Operator）の役割

ROはOperationと非常に相性がよい。

ROは、現在のOperation、actor状態、location、discovery、ログを見て、次の候補を提案する。

```text
RO
= 現在のOperation、actor状態、location、discovery、ログを見て、
  次のHUD候補 / GUI候補 / Operation分岐を提案するもの
```

ROは「自動操縦」ではなく「作戦参謀」として扱う。

### ROが担うべきこと

```text
1. Operationを継続する提案
2. Operationを一時中断する提案
3. Operationを再開する提案
4. Operationのphaseを進める提案
5. Operationを別Operationへ発展させる提案
6. 同じlocation・条件達成時にGUIアクションを有効化する提案
```

### 例: 聞き込みOperation中

```text
Operation: inquiry
actor_state: normal
discovery: 目撃証言Aあり
```

RO提案:

- 近場Bで聞き込みを続ける
- 証言時刻を照合する
- 逃走経路を推理する

### 例: 聞き込みOperation中 + 空腹

```text
Operation: inquiry
time: 12:00
actor_state: hunger high
```

RO提案:

- 聞き込みを続ける
- 蕎麦屋で腹ごしらえする
- 署に戻って証言を整理する

### 例: 逮捕Operation中 + same-location + 証拠十分

```text
Operation: arrest_flow
actor.location == target.location
evidence_score >= threshold
```

RO提案:

- GUI: 逮捕する を有効化
- HUD: 逃走を封じる
- HUD: 身元確認を行う

---

## 12. Operationの最小データ構造案

最初は複雑にしすぎない。

```text
Operation:
  id
  actor_id
  type
  label
  target_id
  status: active / suspended / completed / failed
  phase
  priority
  created_from: HUD / RO / scenario
  candidate_locations
  preferred_action_tags
  required_discoveries
  progress
  notes
```

### 例: 聞き込みOperation

```text
id: op_inquiry_001
actor_id: detective
type: inquiry
label: 聞き込みを始める
target_id: trickster
status: active
phase: location_A
priority: 50
created_from: HUD
candidate_locations:
  - near_A
  - near_B
  - near_C
preferred_action_tags:
  - talk
  - ask_witness
  - compare_testimony
progress:
  near_A: done
  near_B: active
  near_C: pending
notes:
  - 犯人の情報を突き止めるための聞き込み
```

### 例: 逮捕Operation

```text
id: op_arrest_001
actor_id: detective
type: arrest_flow
label: 逮捕に踏み切る
target_id: trickster
status: active
phase: locate_or_close
priority: 80
created_from: HUD
required_discoveries:
  - target_identified
preferred_action_tags:
  - infer_location
  - close_distance
  - block_escape_route
  - arrest
progress:
  target_location_known: false
  evidence_score: medium
notes:
  - 即時逮捕ではなく、逮捕に向けた作戦状態
```

---

## 13. 実行ループ案

1アクションごと、または1ターンごとに、以下の流れにする。

```text
1. actor状態を更新する
   - 空腹
   - 疲労
   - 時刻
   - 場所
   - discovery

2. active_operationを読む

3. ROが候補を出す
   - 継続
   - 分岐
   - 中断
   - 再開
   - フェーズ進行
   - GUI化可能な直接行動

4. HUDに高レベル候補を出す

5. GUIに今すぐ可能な基礎行動を出す

6. プレイヤーまたはAIが1つ選ぶ

7. Operationのphase/progress/statusを更新する
```

### プレイヤー操作RC

- Operationは自動実行しない
- Operationは候補の出方を変える
- ROが作戦参謀として提案する
- プレイヤーが採用するか選ぶ

### AI操作RC

- OperationをもとにAIが次の一手を選ぶ
- ただし same-location / discovery / location / actor_state 制約は守る
- Operationによるチート実行はしない

---

## 14. Session51以降の実装方針

最初から複雑な自動進行はしない。

まずは、Operationを「作戦コンテキスト」として最小実装する。

### 最初に実装したいこと

```text
1. HUDアクションからOperationを開始できる
2. actorごとにactive_operationを持てる
3. OperationがHUD候補を変える
4. OperationがMicroGoal文言を変える
5. ROがOperation継続/分岐/中断候補を出す
6. GUIアクションはsame-location等で厳格判定する
```

### まだやらなくてよいこと

```text
1. Operationによる自動移動
2. Operationによる自動会話
3. 複数ステップの完全自動実行
4. 複雑なOperation階層
5. 完全なHUDアクション合成エンジン
6. 完全なGUIアクションコンパイル
```

---

## 15. 最終まとめ

### TPO縦切り前の原則

```text
current_target は actor別に持つ。
talk / combat / arrest は same-location requirement 必須。
別locationへの干渉はHUDアクションで表現する。
GUIは基礎動詞。
HUDはRC・TPO・discovery・状態を束ねた高レベル候補。
```

### HUD / GUI / Operation / RO の関係

```text
GUI Action
= 今この場で実行できる具体行動

HUD Action
= RCが今取りうる作戦候補・物語候補

Operation
= HUDアクションなどから開始される中長期の作戦コンテキスト

MicroGoal
= Operationから現在切り出された小目標

RO
= Operation・ログ・状態を読んで、次の一手や分岐を提案する作戦参謀
```

### 最重要定義

```text
Operationは、長い行動ではなく、長い文脈である。
```

Operation中でも、他の行動やOperationに分岐できる。  
聞き込み中に蕎麦屋で腹ごしらえしてもよい。  
その脱線が、新しい証言や物語分岐を生むこともある。

### GM-AIらしい戦い方

刑事と愉快犯が別locationにいる時は、

```text
刑事:
- 推理する
- 追跡する
- 証言を照合する
- 包囲する

愉快犯:
- 撹乱する
- 偽の痕跡を残す
- 逃走経路を変える
- 目撃者を避ける
```

同じlocationに入った時だけ、

```text
話す
問い詰める
拘束する
逮捕する
戦う
```

などのGUI直接行動が出る。

これにより、RC同士の戦いは単なるコマンドの殴り合いではなく、

```text
作戦
生活
偶然
制約
推理
妨害
移動
決着
```

が絡む物語になる。

---

## 16. 実装セッションへの短い持ち込み文

Session51-Aでは、以下の方針で進めたい。

```text
TPO縦切りでは、まずGUI/HUD/Operationの境界を壊さないことを優先する。

current_targetはactor別。
talk/combat/arrestはsame-location必須。
別locationのtargetに対してはGUI直接行動を出さず、HUDのremote narrative actionとして追跡・推理・撹乱・痕跡系を出す。

HUDアクションは即時GUIアクションではなく、Operationを開始・更新するものとして扱う。
Operationは「長い行動」ではなく「長い文脈」。
OperationはMicroGoal、HUD候補、GUIアクションの意味づけ、RO提案に影響する。

ROはOperationの進行・分岐・中断・再開・発展を提案する作戦参謀として活用したい。

まずは自動実行ではなく、HUDからOperationを開始し、OperationがMicroGoalとHUD候補に影響し、ROが次の一手を提案するところまでを小さく縦切りする。
```
