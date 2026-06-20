# LOGBOOK.md - 開発日誌（雑談OK）

ルール:

- 1エントリは短くていい（箇条書きでもOK）
- 「気持ち」+「技術メモ」+「次回の最初の一手」を1つ入れる
- 長文になったら、`general_documents/diary/` に退避してリンクを貼る

---

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
