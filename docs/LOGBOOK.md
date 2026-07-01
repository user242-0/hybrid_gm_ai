# LOGBOOK.md - 開発日誌（雑談OK）

ルール:

- 1エントリは短くていい（箇条書きでもOK）
- 「気持ち」+「技術メモ」+「次回の最初の一手」を1つ入れる
- 長文になったら、`general_documents/diary/` に退避してリンクを貼る

---

### 整理メモ

Session45〜Session50は、Prototype Demo #1前後の中核開発ログとして当面LOGBOOK.mdに残す。
将来的に肥大化した場合は、`general_documents/diary/` に「Demo #1開発アーカイブ」として退避する。

## 2026-06-30（Session51-B: GUI target gating / same-location requirement）

### 今日やったこと

- GUI直接行動の `same_location` requirement を最小実装した。
- `talk` / `attack` / `swing_sword` / `engage_combat` / `avoid_combat` / `accept_attack` を、同じlocationの有効targetがいる場合だけ成立するようにした。
- `RequirementsChecker` のtarget解決を整理し、explicit args target / actor_targets / director_world actor_targets / current_target / enemy の順で参照するようにした。
- self-targetは常に不許可にした。
- `has_enemy` だけでcombat系が出る状態を防ぎ、有効target + same-location を必要条件にした。
- `action_layer` / `interaction_scope` の最小メタデータを追加した。
- `pytest -q` all greenを確認した。

### 気づき

- `current_target` は「目の前にいる相手」ではなく「そのRCが意識している相手」として扱う必要がある。
- GUI直接行動は「今この場でできる基礎動詞」に限定する方針が実装上も重要になった。
- 愉快犯側で刑事と同じlocationにいても、actor別targetが未設定ならtalk/combatが出ないのは安全側の挙動。
- Session51-Cでは、別locationだからこそ出るHUD/TPO候補を増やすと、今回消えた直接行動の空白を物語行動で埋められる。

### 次回の最初の一手

- Session51-Cとして、packベースTPO HUD候補を少し増やす。刑事は追跡・証言照合・包囲、愉快犯は撹乱・逃走経路変更・偽痕跡を中心にする。


## 2026-06-30(Session51-A前 TPOコンテンツ縦切りの整理)
- Session51-A前の設計整理として、TPO / Operation / MicroGoal補足メモを future_goals に追加した。

## 2026-06-29（Session50: RC別location / discovery）

### 今日やったこと

* active actorごとに location / discovery を保持する `actor_view_state` 層を追加した。
* HUD refresh時に active actor の location / discovery を、既存互換の `game_state["current_location"]` / `director_world["affordances"]["discoveries"]` へ同期するようにした。
* HUD_DEBUGのlocation変更・discovery injectionをactive actor対象に変更した。
* `cop_trickster` packに `actor_locations` / `actor_discoveries` の初期値を追加した。
* pytest all greenを確認した。
* 手動HUD_DEBUGで、刑事側のdiscoveryが愉快犯側に混ざらず、愉快犯側でdiscovery注入した時だけ追加アクションが出ることを確認した。

### 気づき

* `current_location` / `affordances.discoveries` を即削除せず、active actor視点のlegacy互換ビューとして扱う方針が安全だった。
* RCごとに場所と発見が分かれたことで、switch_characterの価値が一段強くなった。
* 一方で、別locationにいるRC同士が `current_target` になり、talk / combat系GUIアクションが出る問題が見えた。これはGUIアクション / target解決 / same-location requirementの後続課題。

### 次回の最初の一手

* Session51-Aとして、TPO縦切り前にGUIアクション / HUDアクション / current_target / location / discovery の責務を整理する。

## 2026-06-22（Session 49-D: HUD_DEMO legibility pass）

### 今日やったこと

* 60秒デモ撮影用にHUD_DEMOの文字サイズと表示ラベルを調整した。
* HUD_DEMOではDirectorMode / ActorMode / MicroGoal / Actions / 提案候補を大きく表示し、ウィンドウ幅、余白、折り返し幅を撮影向けに広げた。
* 「AI提案」は内部実装名として維持し、HUD_DEMO表示のみ「提案候補」とした。通常HUD / DEBUG HUDの表示、actor_idフィルタ、read-only動作は変更していない。

### 次回の最初の一手

* 60秒デモを試し撮りし、実際のYouTube表示サイズでDirector HUDの可読性を確認する。

## 2026-06-21（Session 49-C: Demo HUD cleanup）

### 今日やったこと

* 60秒デモ撮影用に `HUD_DEMO=1` を追加。RO / Recommended / ProgressはデモHUDから隠し、ActorMode / location / discovery操作は残した。
* `HUD_DEBUG=1` を開発用フルHUDとして最優先し、`HUD_DEBUG=0` かつ `HUD_DEMO=0` は通常HUDとしてDirectorMode / ActorMode / MicroGoal / Actions / AI提案だけを表示するよう整理した。
* HUDの初期geometry指定を生成時の専用処理に限定し、refresh経路では位置を再設定しない構造を明確化した。
* AI提案HUDのactor_idフィルタ/read-only、save/load、switch_character、ActorMode変更、MicroGoal更新の既存経路は維持した。

### 次回の最初の一手

* RO / Recommended / ProgressのRC別対応は後続タスクとして進める。

## 2026-06-21（Session 49-B: 60秒デモ前のMicroGoal/Actions整合ポリッシュ）

### 今日やったこと

* RC別MicroGoalへ `action_id` を保存し、Session 49以前のsaveはtext / modeから補完するようにした。
* discovery gating適用後のActions listboxに対応Actionがある場合だけ現在MicroGoalを表示し、選べない場合は `MicroGoal(<actor>): 未設定` にした。
* switch_character、ActorMode変更、save/load後もactive actorの表示可能Actionsとの整合を取り、AI提案HUDのactor_idフィルタ/read-onlyを維持した。
* 未解放のMicroGoal候補は削除せず、将来の「潜在目標 / 予兆 / ヒント」分離に残した。

### 次回の最初の一手

* TPOコンテンツ縦切り、RC別location/discovery、ROのRC別実装を後続タスクとして進める。

## 2026-06-20（Session 49: RC別MicroGoal）

### 今日やったこと

* 60秒YouTubeデモの優先実装として、active actor + ActorModeに対応するRC別MicroGoalを追加した。
* `director_world["actor_micro_goals"]` にactorごとのMicroGoal、mode、進捗baseline、抽選履歴を保存し、save/load対象にした。
* HUD表示を `MicroGoal(刑事): ...` / `MicroGoal(愉快犯): ...` とし、switch_characterとActorMode変更後に再表示するようにした。
* 既存グローバルMicroGoal API、ActorMode未設定時の `Director.mode` fallback、AI提案HUDのactor_idフィルタ/read-onlyを維持した。

### 次回の最初の一手

* TPOコンテンツ縦切りとROのRC別実装を後続タスクとして進める。

## 2026-06-20（Session 48-C: ActorMode HUD verification）

### 今日やったこと

* Director HUDの既存mode dropdownを `DirectorMode` と明示し、active actorの `ActorMode` を別行で表示した。
* `HUD_DEBUG=1` のときだけActorMode dropdownを有効にし、変更時に `director_world["actor_modes"]`、HUD cache rev、Actions listboxを更新するようにした。
* DirectorMode dropdownは世界全体mode、ActorModeはactive actorのHUD Actions用という責務分離を維持した。
* 刑事PURSUE時の `fix_cam_clock` affordance表示、刑事FREEZE時の非表示、愉快犯をFLEE以外へ変更した際のFLEE actions非継続、未設定actorのDirector.mode fallback、save/load維持をテストした。
* AI提案HUDのactor_idフィルタとread-only方針は変更していない。

### 次回の最初の一手

* RC別MicroGoalの本格設計は後続タスクとして扱う。

## 2026-06-20（Session 48: ActorMode by actor_id）

### 今日やったこと

* `director_world["actor_modes"]` をActorModeの保存先とし、セーブ/ロード対象のworld stateに統合した。
* `Director.get_actor_mode()` / `set_actor_mode()` を追加し、未設定actorは `Director.mode` へフォールバックする互換性を維持した。
* HUD Actionsはactive actorのActorModeを使って生成し、MicroGoal/Recommended/AI stepとmode dropdownはグローバルDirectorModeのまま維持した。
* `cop_trickster` の初期ActorModeは刑事=`FREEZE`、愉快犯=`FLEE` とした。

### 次回の最初の一手

* RC別MicroGoalのキャッシュ・進捗・履歴の保存単位を設計する。TPOコンテンツ縦切りも後続で扱う。

## 2026-06-20（Session 47-B: 愉快犯用の基本HUDアクション）

### 今日やったこと

* 愉快犯FLEE用に「証拠を隠す」「偽の痕跡を残す」「目撃者を避ける」「潜伏先を変える」「次の標的を観察する」を追加。
* effectsはsuspicion低下と小さな進行カウンタに限定した。
* affordance discovery未取得時でも基本5件はActions listboxに残り、刑事用アクションと混ざらないことをテストした。
* AI提案HUDとdemo_seedはread-onlyのまま維持した。

### 気づき

* 従来FLEEの2件は両方opportunity管理下にあり、discovery未取得時はHUD mergeで抑制されるため、Actions listboxが空になっていた。
* `plant_false_trace` はdemo proposalとruntime ActionSpecで同じ意味なので、canonical IDを共有する方が将来の採用導線を単純化できる。

### 次回の最初の一手

* RC別MicroGoalの本格設計は分離し、先に愉快犯向けTPOコンテンツ縦切りで場所・時間・条件による抑制を追加する。

## 2026-06-19（Session 46:repo cleanup / LOGBOOK archive）

### 今日やったこと

* main更新後、cleanupブランチでリポジトリ棚卸しを実施。
* runtime未使用の旧共有bundle、blueprints、GMCore stubをarchiveまたはfuture goalsへ移した。
* ルートの偶発生成物を整理。
* Session 30〜34の重複記録を既存archiveへのリンクに置き換えた。
* Session 35〜44を開発日誌からarchiveへ退避した。
* READMEのExit記述が「Director HUDではなくメインGUI下部入力欄へ `q`」となっていることを確認。
* `pytest -q` はall green。環境によりDirector HUDの1件がskipされる。

### 気づき

* runtime未使用のstubを`src/`に置くと、setuptoolsの自動探索で公開パッケージのように見える。
* 歴史資料は削除せずarchiveへ移すことで、runtime境界を明確にしつつ設計経緯を保持できる。

### 次回の最初の一手

* cleanup差分をレビューし、単一のchoreコミットとしてmainへ取り込む。

## 2026-06-18（Session 45: actor_id付きAI提案HUD / Demo Seed）

### 今日やったこと

* Action Proposal advisory pipeline に `actor_id` を追加した。

  * proposal
  * shadow record
  * advisory item
  * display item
  * provider
  * HUDCallbacks

* HUDCallbacksから`game_state["active_char"].name`をproviderへ渡し、現在操作中RCに一致するAI提案だけをHUDへ表示できるようにした。
* `src/action_proposal/demo_seed.py` を追加し、actor_id付きDemo Proposalを生成できるようにした。

  * 刑事向け: `compare_witness_timestamps` / 「証言時刻を照合する」
  * 愉快犯向け: `plant_false_trace` / 「偽の痕跡を残す」

* demo_seedを冪等化した。

  * 同一 `actor_id + proposal_id` の既知seedは重複追加されない。
  * 既に重複している既知seed recordも1件に正規化される。
  * seed以外のshadow recordは保持する。

### HUD確認

* `python -m src.action_proposal.demo_seed`
* `python -m src.simulation`

確認結果:

* 操作RC = 刑事: 「証言時刻を照合する」が1件表示。
* 操作RC = 愉快犯: 「偽の痕跡を残す」が1件表示。
* 二重表記は解消。

### 気づき

* `switch_character` と `actor_id` により、RCごとにAI提案を切り替える土台ができた。
* 現時点ではAI提案欄のみactor_id対応。将来的には全HUDアクションを現在操作中RCに応じて切り替える方向が自然。
* AI提案実行化の前に、TPOコンテンツを最低1本は縦切りで整える。

### 次回の最初の一手

* all greenを維持した状態でmainへ取り込み、次の機能作業へ進む。

## Archive

- [Session 29-34 summary](../general_documents/diary/session29-34_summary_2026-06-08.txt)
- [Session 35-44: Action Proposal DSL to HUD](../general_documents/diary/session35-44_action_proposal_dsl_to_hud_2026-06-19.md)
- [Earlier diary entries](../general_documents/diary/)
- [ICEBOX: GM-AI世界を用いた人工エージェントの自己連続性 C(t) 研究構想](../general_documents/future_goals/RESEARCH_NOTES.md)
