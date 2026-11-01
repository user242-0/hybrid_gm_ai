# LOGBOOK.md - 開発日誌（雑談OK）

ルール:

- 1エントリは短くていい（箇条書きでもOK）
- 「気持ち」+「技術メモ」+「次回の最初の一手」を1つ入れる
- 長文になったら、`general_documents/diary/` に退避してリンクを貼る

---

## 2026-11-01（Session 61: 遊べる事件1本へ）

- 所感／方針: ユーザーが「遊んで楽しい体験」を優先し、事件1本の選択・結果を設計 → 最小実装で試遊 → 同じ事件で外部AI版RCを比較する方針を採用した。必要なリファクタは体験に合わせて行う。
- Session60-4完了コミット `afcb51d` から `feature/session61-playable-case-v01` をGitHub上で作成し、STATE/LOGBOOKへ方針を記録。今回の変更は文書のみ。ゲーム実装・API接続・手元のcheckoutは未実施。
- 叩き台は5〜10分の聞き込み事件。訪問順・聞き方と、愉快犯の隠蔽／誘導による展開・結末の違いを目指す。個別の事件内容や分岐はこれから決める。
- 技術メモ: CharacterStatusにはHP/スタミナがあるが、現行RCContextBundleには明示的に含まれず、perceived_worldにも天気・空腹はない。「空腹だが雨なのでテイクアウトより入店する」という例を、Operation・身体状態・環境・利用可能行動の相互作用の検討材料とする。情報追加だけで実行可能にはならず、候補・条件・効果が必要。空腹とスタミナの関係、天気の認識、Operationを保持した休息／中断／再開、既存Operation優先判断との関係は未決。
- 外部AIは本人向けcontextと候補から行動・理由を提案し、人間が採用、既存経路で検証・実行するところから試す。
- 次回の最初の一手: 事件の導入・目的・選択・結果・結末を一枚にまとめ、必要な状態と実装範囲を決める。Operation反復が必要なら固有instance IDを先に扱う。

## 2026-10-31（Session 60-4: チェックポイント2・接続）

- 所感: 型の導入を開始・進行へ接続しつつ、読取APIと保存形式を維持できた。
- fetch後にHEAD/originが基準e7f91f7で一致することを確認。既存ユーザー変更を保持し、DATA_OWNERSHIPの責務表追記も残して現行契約を更新する。
- StoreのInstance取得/保存APIを追加し、開始・進行から利用。Runtime、reader、Memory/Beliefの処理順序と例外境界は維持する。
- 変更前の全体831件成功。sandbox内では一時ファイル権限エラーのため、許可された制限外実行で確認した。実装後の関連201件、全体847件成功（新規16件、skip/failureなし）。`git diff --check`成功。config/GLOSSARY/AGENTSのハッシュ一致も確認。
- GUI手動確認済み（2026-10-31、ユーザー報告）: 開始・進行・save/load・actor切替を確認。チェックポイント2完了として、ユーザー指示により実装・テスト・文書をcommit/pushする。次の最初の一手: Contents Probの内容・範囲を検討し、同種Operation反復前の固有instance ID導入を計画する。

## 2026-09-27（Session 60-4: チェックポイント1・型と相互変換）

- 所感: まず本番経路から独立した変換部品を作り、旧データを変えないことを確認できた。
- OperationInstanceを追加。入力・出力・フィールド取得はdeepcopy、変更はwith_changesで別Instanceを作る。dict内部の不正値も勝手に修復せず、欠落とNone、未知metadataを含めて保持する。進行可否の判断や保存は持たない。
- 新規19件とStore/所有境界/既存Operationの関連32件、計51件成功。全体テスト・GUI再確認は未実施。本番Store/Runtimeには未接続。ユーザー指示により実装・テスト・STATE・LOGBOOKを `feat: add detached OperationInstance conversion` としてcommit/pushする。他のローカル編集は含めない。
- Contents Probで同種Operationを反復する前に固有instance IDを導入するチェックポイントをSTATEへ明記した。
- 次の最初の一手: Storeの型変換と開始・進行処理へ接続し、既存readerと保存形式を維持する。

## 2026-09-27（Session 60-4: 開始・ブランチ作成）

- 所感／進め方: 利用制限に工程を合わせず、意味のある区切りに再開可能なチェックポイントを残す。音声と文章を適宜併用する。
- STATE・LOGBOOK・Operation所有境界・Store/reader実装を確認。fetch後、60-3のローカル／originが `c3b981f` で一致し、前回成果がcommit/push済みであることを確認した。
- `refactor/session60-4-operation-instance-v01` を作成しoriginへpush、upstream設定済み。開始時の既存ローカル変更は保持。実装・テスト再実行は未着手。
- ユーザーから、前回最後のローカルsimulation動作確認は問題なしとの報告を受けた（2026-09-27）。
- 60-4は既存保存形式・ID・進行挙動を保つOperationInstance型導入と合意。Store境界の変換、readerのdetached dict、変更後Instanceの明示保存、既存部分成功契約を維持する。型と変換／更新接続／回帰検証で区切る。固有instance IDは将来のContents Probで同種Operationを反復する要件に合わせて検討する。
- 次の最初の一手: OperationInstanceの型導入と保存／読取境界の仕様を確認する。

## 2026-09-21（Session 60-3: OperationStore導入・読取/更新経路分離）

- 所感: 正本の置き場所を保ったまま、取得結果を編集してもゲーム状態が変わらない境界を作れた。
- 段階①: OperationStoreに正本アクセスと初期化を集約し、取得・保存入力・開始の新規/既存両戻り値をdeepcopy。world defaultsのOperationマージもStoreへ移し、既存優先と参照分離を固定した。既存dict/YAML形式を維持し、OperationInstance独立クラスは今回追加していない。
- 段階②: 読取利用者はoperation_reader、Runtime統括下の開始・進行はStoreへ明示保存。進行条件・transition履歴・Memory/Belief・GCS順序・部分成功契約は維持。旧公開ensureを内部化し、旧get/format/set/clearは互換経路を残した。正本キーとwriter依存の再発を検知する静的検査を追加した。
- 文書: ユーザー編集中のDATA_OWNERSHIP.mdの既存内容を保ってルールを追記し、AGENTS.md末尾に参照を追加。config.yml / GLOSSARY.mdは未変更。汎用world保存復元は維持し、共有dictやPython動的機能まで書込を封鎖するものではない旨も明記。
- 検証: 段階①関連142件、段階②関連285件成功。初期化マージhelperへ渡す入力の参照分離も検証し、最終全体810 passed / 2 skipped（既存Tkinter display依存）、git diff --check成功。GUI手動確認は未実施。コミット・pushは未実施。
- 次回の最初の一手: WindowsでOperation開始・進行・save/load・actor切替を確認し、Store/reader境界をレビューする。OperationInstanceの独立型導入は次回の検討候補。

## 2026-08-22（Session 60-2: GameCommandService導入）

- 気持ち／所感: Session 60-1のOperationRuntime境界を壊さず、その一段上に1回のCommand全体を通すApplication境界を置けた。Python HUD、将来のUnity／Mobile等が同じ入口へ接続するための土台になった。
- 技術メモ: `GameCommand`、正式な`ActionOutcome`、内部`ActionExecutionResult`、detachedな`GameCommandResult`、`StageFailure`を追加した。`ActionPipeline`をeffects確定までの`execute_action()`と、time／emotion／Director／MicroGoal／affordance／log／RO／sceneを現行順で行う`finalize_post_action()`へ分割した。
- Application flow: `GameCommandService`がAction execution、既存`OperationRuntime`、committed transitionからのMemory／Belief投影、post-action lifecycle、終了後active actorのfresh RCContextBundle生成を順に一回ずつ呼ぶ。GCS自身は正本を所有・直接更新せず、domain ruleやHUD／Tkinterを持たない。
- 互換性: productionの`simulation.dispatch_action()`をGCS入口へ変更し、legacy raw valueと`ActionExecutionOutcome`を維持した。`ActionPipeline.request_action()`はLegacyGUI／既存test向けの一時的full-lifecycle入口として残した。`switch_character`後のBundleは新active actorを対象とし、`move_to_location`の特殊経路、RC_AI advisoryのHuman adoption、actor分離、Session 59黄金経路を維持した。
- 部分成功: OperationRuntime内部failureは従来どおり`[]`との区別を推測しない。Memory／Belief／Bundle failureはrollbackせず、GCSが直接観測したprojection／Bundle failureだけを`StageFailure`へ記録する。Result内のtransition、Memory、Belief、Bundleは正本から切り離したsnapshotとした。
- テスト: 変更前baseline `764 passed / 2 skipped / 0 failed`。GCS単体・integration 15件、指定関連384件、full suite `781 passed / 2 skipped / 0 failed`。simulationは既知の`PYTHONPATH=.;.\src`で起動入口まで到達し、Codex環境のTcl/Tk `init.tcl`不足でGUI生成のみ未完了。legacy simulation import-path依存は別課題のまま残す。
- 次回の最初の一手: Chat（設計）でSession 60-2の実コードと境界を確認し、legacy `request_action()`、post-action subsystem分離、Bundle二重read-only build等をどのSessionで扱うか決める。

## 2026-08-22（Session 60-1: OperationRuntime抽出）

- 気持ち／所感: Session 59で閉じた認知行動ループの意味を変えず、ActionPipelineが抱えていたOperation lifecycle統括を明示的な境界へ切り出せた。今後GameCommandServiceへ上位統括を移すための最初の足場ができた。
- 技術メモ: `src/operation_runtime.py`を追加し、ActionPipelineから`OperationRuntimeInput`を一成功Actionにつき一度渡す。Runtimeはprogression、commit済みtransition記録、Operation startを現行順序・部分成功境界のまま統括し、保存済み`OperationTransition[]`だけを返す。Memory／Belief投影はActionPipeline側に残した。
- 維持事項: `start_inquiry_operation`のprogression→`no_active_operation`→start、`choose_first_inquiry_target`のtransition→Memory→Belief、`switch_character`のprogression除外、actor分離、冪等性、save/load、既存`ActionExecutionOutcome` contractを維持した。OperationStarted eventやOperationStore等は導入していない。
- テスト: OperationRuntime単体14件、必須関連233件、full suite `764 passed / 2 skipped / 0 failed`。simulationは既知の`PYTHONPATH=.;.\src`でimport／Director初期化まで到達し、同梱PythonのTcl/Tk不足でGUI生成は未完了。legacy simulation import-path依存は別課題のまま残す。
- 次回の最初の一手: Session 60-2でGameCommandService導入を設計し、ActionPipeline、OperationRuntime、Memory／Belief projection、fresh ContextBundleの上位統括境界を検討する。

## 2026-08-02 — Portfolio production and temporary pacing change

ゲーム会社の障害者採用3D職への応募を見据え、
非AI高品質キャラクター「冥砂の女戦士」の制作へ着手した。

GM-AIを中止・縮小する判断ではない。
GM-AIは引き続きライフワークとして従来に近い比重で扱うが、
ポートフォリオ上では3D職として読みやすい配分に編集する。

Session 60-1は、Chat(Work)へOperationRuntime調査プロンプトを
送る直前で一度安全に停止可能な状態とした。

再開時の最初の作業は、
保存済みの調査プロンプトをChat(Work)へ送ることである。

## 2026-07-19（Session59-C: RC Belief Update / Context Feedback v0.1 実装）

- 気持ち／所感: 客観event→主観Memory→現在Belief→次の判断Bundleまでを一方向に接続し、三層を混ぜずに構造上の認知行動ループv0.1を閉じられた。Beliefを作ることと、Beliefで行動を変えることを分離できたのもよい。
- 技術メモ: `src/rc_belief.py` にpure builder、current snapshot updater、live coordinator、manual-load catch-up、actor別readerを分離した。刑事のexact Memory一件だけから `actor_beliefs[actor_id][belief_id]` を生成し、同じsourceはno-op、同一内容の別sourceは末尾追加、conflict／malformed既存recordは非上書きとした。eventやOperationは再参照しない。
- live失敗ではrollbackしない。eventとMemoryまでが残ればBeliefは後で決定的に再投影でき、Action effectsやauthoritative Operation進行を戻す方が既存成功契約を壊すためである。manual loadではMemory catch-upとBelief catch-upを別境界にし、loadとHUD refreshを継続する。catch-up後の自動Saveは行わない。
- `RCContextBundle.beliefs` はfull recordのdeepcopyで、BeliefをAction gate、Operation、discovery、perceived worldへ逆流させない。RC_AI ruleは変えず、進行後はMemory＋Beliefがあっても `no_safe_action`。`_to_safe_value()`のfloat正規化契約はSession 60へ残した。
- YAMLメモ: `source_memory_ids` のようなコロン入りIDのlistは、repository内軽量parserが引用済みscalarをinline mapと誤認していた。引用済みlist scalarの判定順だけを直し、新規Belief subtreeのsafe roundtripと既存YAML回帰を固定した。
- Session59-BのWindows手動確認は完了済み。`director_world.yml` の `actor_memories.刑事` に `rc_memory_v0.1` recordが保存されることを確認した。
- テスト: `747 passed / 2 skipped`。Session59-CのWindows手動確認も完了した。`choose_first_inquiry_target` 実行後の `director_world.yml` で、`operation_transition_history`、`actor_memories.刑事`、`actor_beliefs.刑事` を確認し、Beliefの `value=true`、`confidence=1.0`、`source_memory_ids` に刑事Memory IDが一件保存されること、愉快犯bucketへ刑事Beliefが混入していないことを確認した。
- Session59総括: 構造上の認知行動ループv0.1は閉じた。Action結果がOperation transition event、RC Memory、RC Beliefへ変換され、次のRCContextBundleおよびRC_AI判断入力へ戻る配線が成立した。Beliefを利用した行動分岐は未実装。
- 次回の最初の一手: Session59-CデブリーフをChatGPTへ持ち帰る。Session 60へ勝手に進まず、Fresh／Continue lifecycle、共通world adoption、hook整理、Belief revision／Belief-driven RC_AI、Operation instance identity、serialization boundaryを次設計で扱う。

## 2026-07-19（Session59-B: RC Memory Projection v0.1 実装）

- 気持ち／所感: 客観transition eventを直接Beliefへせず、まずactor本人の主観Memoryへ一方向に投影できた。客観事実・経験・信念の三層を保ったまま、Session59の認知ループをもう一段閉じられたのがよい。
- 技術メモ: `src/rc_memory.py` にpure builder、actor別recorder、history catch-up、recent readerを分離した。刑事の最初の聞き込み先選択eventだけをstructured fields完全一致で決定的Memoryへ変換し、`actor_memories[actor_id]` へappendする。IDは `memory:{actor_id}:{source_event_id}`、v0.1は一source event・一actor・一Memoryで、live／catch-up／reloadを跨いで冪等にした。
- event IDはrule selectorにせず、event構造との整合性確認とsource参照に限定した。これにより、将来Operation instance identityを拡張してもruleの意味条件をID文字列の解析へ閉じ込めずに済む。
- live projection失敗時はrollbackしない。Action effects、authoritativeなOperation進行、客観eventはすでに成立しており、Memoryは再構築可能なprojectionだからである。専用ログを出してAction成功を維持し、残ったeventをmanual load時などのcatch-upで回復できるようにした。
- catch-upはmanual loadでworldを正式採用した直後だけ実行し、startupやread pathには入れていない。catch-up直後の自動Saveも行わず、既存の明示Save契約へ任せる。RCContextBundleはactor別Memory record全体の直近5件を古い順→新しい順でdeepcopyするだけで、worldを変更しない。
- simulation clock、Belief、observer Memory、汎用projector registry、Memory UI、検索／忘却は追加していない。現行RC_AI ruleも変えず、Memoryを受け取った進行後Bundleは引き続き `no_safe_action` になる。
- テスト: `641 passed / 2 skipped`、`git diff --check`成功。Windows手動確認も完了し、実行と明示Save後の `director_world.yml` に `actor_memories.刑事` の `rc_memory_v0.1` recordが保存されることを確認した。
- 次回の最初の一手: ChatGPTへSession59-Bデブリーフを持ち帰り、Memoryからactor別Beliefへ更新するSession59-Cのruleと保存境界を設計する。Session59-Cへは勝手に進まない。

## 2026-07-18（Session59-A: Operation Transition Record v0.1 実装）

- 気持ち／所感: Action結果、客観event、RC Memory、Beliefの境界を崩さず、Session58の縦切りへ小さい永続記録を足せた。次の認知ループへ渡す事実が、表示や主観表現から独立した形になったのがよい。
- 技術メモ: progression成功resultから決定的な `operation_transition_v0.1` eventを構築し、director world rootの `operation_transition_history` へ遅延生成・冪等appendする。現在のactive Operation post-stateをactor/id/type/to_phase/next MiniGoalまで照合し、重複時は既存eventのdeepcopyを返す。不正入力や不正historyではworldを変更しない。
- ActionPipelineではeffects成功後のprogression直後、Operation start / time advance前にrecordする。progression失敗とrecord失敗の例外境界を分け、recordだけ失敗した場合もeffectsとauthoritativeなOperation進行を巻き戻さない。v0.1でtransactionを導入すると既存のAction成功契約と副作用全体のrollback設計まで広がるため、専用ログを出す部分成功を選んだ。
- simulation clockは保存しなかった。対象Actionが `time_min: 0` で、既存clock形式とpre/post time advance契約をこのSessionで固定する必要がなく、event順序はappend-only listで保持できるため。将来は時間契約を整理した上でoptional fieldとして追加できる。
- 固定Operation IDのため同actor・同typeを再開始するとevent IDが衝突し得る。instance ID / sequence / migrationはOperation完了・再開始設計と合わせて扱い、59-Aには持ち込んでいない。Memory / Belief / RCContextBundle、汎用event bus、rollbackも未実装。
- テスト: `586 passed / 2 skipped`、`git diff --check`成功。自動テスト完了、Windows手動確認待ち。
- 次回の最初の一手: ChatGPTへSession59-Aデブリーフを持ち帰り、客観transition eventをactor別Memoryへ投影するSession59-Bのsource event契約を確認する。Session59-Bへは勝手に進まない。

## 2026-07-18（Session58-B: Operation phase / MiniGoal progression 実装）

- 58-A確定HEAD `b49a521` から作成した `feature/session58b-operation-minigoal-progression` 上で実装した。既知の `config.yml` と未追跡 `AGENTS.md` は変更・stageしていない。
- `src/operation_progression.py` にactor別の小さい進行関数を追加した。`ActionPipeline.request_action()`のeffects成功後だけ呼び、刑事のactive inquiry / phase=start / 初期MiniGoal / exact actor discovery `inquiry_target_chosen` が揃った時だけ `target_selected` / `mini_goal_take_first_testimony` へ更新する。進行resultはJSON-safeで、既存`ActionExecutionOutcome`には混ぜない。
- cop_trickster packの新規Operationは `mini_goal_choose_first_inquiry_target`（聞き込み先を一件選ぶ）から始まる。既存RC_AI intent `advance_inquiry_first_testimony` と `choose_first_inquiry_target` は維持し、旧 `mini_goal_first_testimony` はread-time mutationなしのlegacy aliasとして受理する。
- Operation更新はdeep copy後に行い、status、id、target、parent MicroGoal、created_from、notes等を保持する。二回目、別actor、別Operation、別phase、discovery未達、不完全stateはworld非変更のno-op。次MiniGoalには未実装advisoryを追加せず、既存refreshでRC_AI欄が空になる。
- HUD widget/setter、58-A手動採用、水平ペイン、AFFECT、RO／External、geometry、event loopは変更していない。Operation history、Memory / Belief、Operation完了、中断・arbitration、具体的な聞き込み対象、GUI Action Compileも対象外。
- テスト: `498 passed / 2 skipped`、`git diff --check`成功。単体の冪等性・legacy互換・actor分離・JSON/YAML roundtripと、Pipeline成功／gate拒否／effects失敗／progression例外、58-A実行、HUD before/after、進行後save/loadを固定した。
- Windows手動確認で、「聞き込みを始める」後の初期MiniGoalから「採用して実行」し、`target_selected` / 「最初の証言を取る」への表示遷移とRC_AI欄消去を確認した。`investigation_progress +1`は手動での確認方法が不明だったため未確認だが、実Pipelineテストで1回だけ増え、二重実行で増えないことを保証している。
- 次回の最初の一手: Session59のMemory / Beliefへ進む前に、Session58-A/Bをcheckpoint化し、Action結果とOperation transitionをどの粒度でMemory eventへ渡すか調査する。

## 2026-07-14（Session58-A: RC advisory手動採用・実行 実装）

- Session57.5のHEAD `5ab44e3` を `staging/session57-5-hud-intelligence-panel` としてoriginへpushし、そこから `feature/session58a-rc-advisory-manual-execution` を作成した。
- RC COGNITIONの折りたたみ内へ「採用して実行」buttonとstatus表示を追加した。実行allowlistは `choose_first_inquiry_target` だけで、愉快犯、RO、External Proposalは実行可能化していない。
- 現行RC cacheへschema / actor / selected_intent / action / layer / paramsだけをdeepcopyした非永続snapshotを追加した。クリック時はfresh Bundle/advisoryを必ず再生成し、snapshot完全一致時だけ既存 `source="HUD"` のdispatchを1回呼ぶ。switch、stale、no_safe_action、例外では実行しない。
- ActionPipelineには既存戻り値を変えないopt-in `ActionExecutionOutcome` を追加し、TPOの成功と拒否をHUDCallbacksが区別できるようにした。TPO実行gateはactive actor、HUD layer/source、ActorMode、discovery、Operation、locationを現在stateで再確認する。
- `choose_first_inquiry_target`の二重実行は、packの `forbidden_discoveries: [inquiry_target_chosen]` をDirectorの列挙・実行gate双方で評価して防いだ。1回目はdiscovery追加とprogress +1、2回目は効果なしとなり、実行後のfresh advisoryもno_safe_actionになる。
- Operation / MiniGoal / phaseは実行前後で不変に固定した。全475件は473 passed / 2 skippedで成功し、`git diff --check`も成功した。
- Windows手動確認で、刑事のactive inquiry Operationから「採用して実行」を押すと `[EFFECTS] action=choose_first_inquiry_target applied=2` が出力され、advisory消去と二重実行拒否が成立した。愉快犯advisoryは実行不可で、Operation / MiniGoal / phaseも不変だった。Session58-Aの受け入れ条件は達成。
- 気づき: advisoryの再生成は意図の鮮度を保証し、ActionPipeline gateは実行権限を保証する。両者を分けることでRCの提案とプレイヤー承認、世界状態の最終権限を混同せずに済む。
- 次回の最初の一手: Session58-Bで `inquiry_target_chosen` を達成条件として読み、Operation.MiniGoalまたはphaseを最小進行させる仕様を詰める。
- 将来課題: Operation interruption / arbitration（suspend / resume / cancel / replace、urgent discoveryとの競合）は58-A対象外。58-Bでinquiry_target_chosenを達成条件としてOperation.MiniGoal / phaseの最小進行を扱う。

## 2026-07-14（Session57.5: HUD Intelligence Panel実装）

- 57-AでRC_AI長文がActionsを押し下げた問題に対し、Director HUDを `tk.PanedWindow` の水平2ペインへ分割した。左をゲーム状態と操作、右をRC / RO / External Proposalの知性チャンネルとして整理した。
- Intelligence Panelはnormal / demo / debugすべてで利用可能にし、normalだけRC_AI判断を初期折りたたみにした。advisory更新で勝手に開かず、単純なbutton切替だけで展開する。
- RC_AI判断は「現在文脈から生成された潜在意図・継続候補」と注記した。AFFECTは判断原因ではなくRCContextBundle入力snapshotとして表示し、debugのみRGB数値を出す。
- 既存3 setterとactor付きRC cacheを維持し、Bundle生成済みならadvisory生成失敗時もAFFECTを残す一方、Bundle失敗時はRC/AFFECTだけをclearする境界をテストした。
- 新しいtimer / after / polling / animationは追加せず、geometryも初期化時の1回だけを維持した。全460件は458 passed / 2 skippedで成功。2件はheadless環境のTk widget生成テスト。
- 気づき: normalで潜在意図の存在だけ示して詳細をユーザー選択に委ねると、RC内部候補を観察可能にしつつプレイヤーへの過度な誘導を抑えられる。
- WindowsでSession57.5の手動確認を完了した。水平2ペインの表示と操作を確認し、Session57.5の受け入れ条件を達成した。
- 次回の最初の一手: Session58-AでRC COGNITION sectionへ手動採用controlsを追加し、Bundle/advisory再生成とActionPipeline再検証を経て1件だけ実行する。

## 2026-07-12（Session57-B: Trickster FLEE reactive intent rule 仕様策定）

- 57-Aの確定HEADから `feature/session57b-trickster-flee-intent` を作成した。57-Aの全テスト成功追記は既に `1653e63` でコミット済みだった。
- 愉快犯の `FLEE + perceived unsafe_route_identified` を、Operationがない場合だけ評価するreactive intent ruleとして追加する仕様を確定した。
- active Operationがある場合はOperation rule未対応でもreactiveへ降りず、安全に無回答とする。completed/suspended等の明示的な非active statusはreactive評価を許可する。
- `change_escape_route`と日本語labelはpack/ActionSpecに既にあり、複数候補中のID完全一致も既存matcherで可能。安全性のためeligibility/layerは明示一致へ締める。
- HUD表示・actor付きcache・switch再生成は57-Aをそのまま再利用する。次回の最初の一手は `src/rc_ai.py` のresolver最小分割と単体/Bundle/HUD switchテスト。
- Operation優先resolverと愉快犯FLEE reactive resolverを実装し、action matcherのeligibility/layerを明示一致へ締めた。
- 57-Aのintent日本語label mappingへ「危険な逃走経路を避ける」を追加し、ActionSpecの「逃走経路を変更する」を既存adapter経由で表示できるようにした。
- 対象149件、全回帰446件（445 passed / 1 skipped）が成功。刑事→愉快犯→刑事の実Bundle switchでもadvisoryが再生成された。
- discovery消費、再推薦抑制、自動実行、HUD水平2ペイン化は意図どおり未実装のまま残した。
- `.venv`で手動確認し、愉快犯FLEEへ `unsafe_route_identified` を注入すると「危険な逃走経路を避ける」intent表示が成立した。Session57-Bは完了。
- 次の流れは、57.5候補としてHUD Intelligence Panel／水平ペイン、その後58-Aでadvisory手動採用とActionPipeline再検証による1件実行、58-BでOperation.MiniGoalまたはphaseの最小進行を想定する。

## 2026-07-12（Session57-A: Runtime RC_AI advisory HUD integration 仕様策定）

- Session56のHEADから `feature/session57a-runtime-rc-ai-hud-readonly` を作成し、実装前のコードフロー調査を行った。
- RCContext/advisoryは既存HUD action cache再計算後に生成し、actor_id付きの非永続・インスタンス内表示cacheを毎refreshで安全に反映する方針を確定した。
- 既存Action Proposalの `set_advisory_items()` と分離し、`set_rc_advisory()`、専用formatter、独立StringVar/rowを追加する仕様とした。
- switch_characterは `hud_cache_rev` を増やすが、actor mismatchも再計算条件・clear条件に含め、古い刑事表示を残さない。
- `HUDCallbacks`へactor付き非永続cacheと安全な生成/clear境界を実装し、`DirectorHUD`へ独立した `RC_AI判断` rowと通常/DEBUG formatterを追加した。
- ActionSpec日本語label、no_safe_action、switch往復、例外分離、Action Proposalとの独立性、非永続cacheを固定する専用テストを追加した。
- ActionPipeline、既存 `select_action()` / `pick_action()` は変更していない。
- `git diff --check` は成功。マシン上に利用可能なPythonがなく、既存 `.venv` も削除済みPython 3.10を参照しているためpytestは未実行。
- 手動確認では「聞き込みを開始する」実行後、RC_AI判断が期待どおり表示された。Session57-AはChatへ持ち帰れる状態。
- python -m pytest -q: all passed, 0 skipped. 実行環境では合計件数が表示されなかった
- 気づき: RC_AI判断の複数行表示でHUDの縦領域が圧迫される。機能不具合ではないため57-Aを閉じ、右ペイン化などの水平レイアウトを別課題として検討する。

## 2026-07-10（Session56: RC_AI read-only advisory v0.1）

### 今日やったこと

- `src/rc_ai.py` にread-onlyな `generate_rc_advisory(bundle)` を追加した。
- 刑事のactive inquiry Operationと `mini_goal_first_testimony` から、`advance_inquiry_first_testimony` / `choose_first_inquiry_target` を返す最小縦切りを実装した。
- RCContextBundleへactor別RGB snapshotとOperation MiniGoal IDを追加した。
- advisoryは候補を実行せず、ActionPipelineやOperation stateを更新しない。
- RCContextBundleからadvisoryまでの統合テストを含む対象テスト26件と全回帰テストを実行し、全体は398 passed / 1 skippedだった。

### 気づき

- Operation typeとMiniGoal IDに明示一致するHUD候補を優先すれば、汎用スコアエンジンなしでも「意図を先に作る」縦切りを成立させられる。
- `world["emotion"]` はactive actor互換ビューなので、非active RCの判断材料にはactor別emotion snapshotが必要。
- `start_inquiry_operation` が開始後も候補に残っていても、意図に対応する `choose_first_inquiry_target` を明示選択することで再開始を避けられる。

### 次回の最初の一手

- Session57としてadvisoryをread-only表示経路へ接続するか、愉快犯FLEEの小さなfallback ruleを別縦切りで追加する。
- 自動実行、Operation phase進行、RGB tie-breaker、RO strategy patchは引き続き分離する。

## 2026-07-10（Session55.5: HUDウィンドウ位置リセット修正）

### 今日やったこと

- Director HUDの生成、refresh、tick、enqueue、geometry指定をリポジトリ全体で追跡した。
- geometry指定は生成時の1回だけで、HUDの再生成やrefresh時の位置上書きは無いことを確認した。
- simulation側の協調 pump() 中にHUDの after コールバックが再度 root.update() を呼ぶ、Tkイベントループの再入を解消した。
- run_async() は初回描画だけを行い、以後は既存のsimulation側 pump() に一本化した。
- 内部タイマーを登録しないheadless回帰テストを追加し、pytest -q は381 passedだった。
- Session56のRC_AI/advisory選択ロジックには触れていない。

### 気づき

- geometry再適用が無くても、Windowsのタイトルバードラッグ中にTkのネストしたイベントループが走ると、タイミング依存の位置戻りとして現れ得る。
- UI更新源を協調 pump() に一本化すると、既存の別スレッドenqueueを保ったままドラッグとの競合を除去できる。

### 次回の最初の一手

- Windows上でHUD移動後のrefresh、Actor切替、advisory更新を手動確認する。
- 確認後、Session56のRC_AI advisory v0へ進む。

## 2026-07-08（Session53-A-Fix-3: move_to_location logging）

### 今日やったこと

- GUI基礎動詞 `move_to_location(destination)` 成功時に、通常アクションと同じ行動ログへ記録されるようにした。
- 不正destinationで拒否された場合は、成功ログを残さないようにした。
- move_to_locationのGUI表示、actor_locations更新、switch_character、RCContextBundle分類は維持した。
- `pytest -q` all greenを確認した。

## 2026-07-08（Session55-A: RCContextBundle v0）

### 今日やったこと

- `src/rc_context.py` を新規作成した。
- `build_rc_context_bundle(actor_id, game_state, director)` v0 を実装した。
- RC_AIに渡すためのread-only文脈パッケージとして、perceived_world / actor_mode / micro_goal / active_operation / available_actions / recent_memory placeholder を束ねた。
- `available_actions` を gui / hud / meta に分類した。
- `move_to_location(destination)` は gui に分類した。
- `switch_character` / `set_emotion` は meta に分類し、`rc_ai_eligible: false` とした。
- Operation依存HUD候補は hud に含め、`required_operation_type` などで区別した。
- RCContextBundleは保存せず、毎回生成する派生ビューとして扱うことを確認した。
- rc_ai.py / LLM / 行動意図生成 / 自動実行 / Operation進行 / memory保存 / belief保存はまだ行っていない。
- `pytest -q` all greenを確認した。

### 気づき

- perceived_world が「RCから見えている世界」だとすると、RCContextBundleは「RC_AIに渡せる現在文脈一式」になる。
- available_actionsを gui / hud / meta に分けることで、GUI基礎動詞・HUD作戦候補・プレイヤー用メタ操作を混線させずに扱える。
- meta actionはRC_AIに選ばせないため、`rc_ai_eligible: false` を持たせるのが重要。

### 次回の最初の一手

- Session56として、RCContextBundleを入力にした rc_ai.py advisory v0 を検討する。
- その前または別枠で、`move_to_location` がログに記録されない問題を Session53-A-Fix-3 として調査する。

## 2026-07-08（Session54-A: RC別 perceived_world v0）

### 今日やったこと

- `src/perceived_world.py` を新規作成した。
- `build_perceived_world(actor_id, director_world)` v0 を実装した。
- RC別に actor_id / location / actor_mode / discoveries / active_operation / visible_routes / interpretations を持つviewを生成できるようにした。
- `visible_routes` は `location_graph` と `allowed_actors` を反映するようにした。
- `interpretations` はルールベースで、刑事と愉快犯で異なる見え方を返すようにした。
- HUD_DEBUG時に perceived_world の短いread-only要約を表示した。
- perceived_worldは保存せず、director_world等から毎回生成する派生ビューとして扱うことを確認した。
- CaseSeed / hidden_role / case_theory / clue真相役割 / arrest判定 / belief_world / memory / RC_AI / LLM / Operation進行 / GUI Action Compile はまだ行っていない。
- `pytest -q` all greenを確認した。

### 気づき

- actor_locations / actor_discoveries / actor_modes / active_operation が、RCごとの「世界の見え方」を作る材料になり始めた。
- discoveryは「何を知っているか」、interpretationは「それをどう意味づけているか」と分けて扱うのが重要。
- perceived_worldを保存しない派生ビューにしたことで、truth / discovery / belief の混線を避けやすくなった。

### 次回の最初の一手

- Session55として、perceived_world + actorMode + MicroGoal + ActiveOperation + memory placeholder を束ねる RCContextBundle v0 を検討する。

## 2026-07-06（Session53-A: GUI基礎動詞「移動する」縦切り）

### 今日やったこと

- `location_graph` v0 を導入した。
- GUI基礎動詞 `move_to_location(destination)` を追加した。
- `move_to_location(destination)` はHUD ActionsではなくGUIアクション欄に表示されるGUI基礎動詞として接続した。
- 実行本体は `ActionPipeline` + `location_graph.py` に寄せ、GUI候補の `params.destination` を選択経路から保持して渡すようにした。
- 移動実行時に active actor の `actor_locations[actor_id]` を更新し、legacy `current_location` も同期するようにした。
- `allowed_actors` により、actorごとに移動可能な出口を制限した。
- `酒場` / `情報源_夜の酒場` のlocation重複を整理し、Session53-Aでは `酒場` に統一した。
- `time_min` はedge metadataとして持たせたが、今回は時間消費には使わなかった。
- 移動してもOperation / Operation.MiniGoal / MicroGoalが勝手に変わらないことを確認した。
- perceived_world本実装、GUI Action Compile、自動移動、時間消費、経路探索、Operation phase進行はまだ行っていない。
- `pytest -q` all greenを確認した。

### 気づき

- GUI基礎動詞「移動する」により、RCが世界に触る最初の実行可能な導線ができた。
- `location_graph` は将来の perceived_world / RC_AI / GUI Action Compile の入力になり得る。
- `time_min` は定義したが未消費にしたことで、瞬間移動感を将来解消する余地を残しつつ、Session53-Aの責務を小さく保てた。

### 次回の最初の一手

- Session53-Bとして、移動結果とOperation中HUD候補の接続を検討する。

## 2026-07-05（Session52-C: required_operation_type によるHUD候補の最小接続）

### 今日やったこと

- `required_operation_type: inquiry` を導入し、inquiry Operation中だけ「聞き込み先を一件選ぶ」が出るようにした。
- 「聞き込みを始める」は既存挙動として維持し、刑事 + PURSUE/WITNESS + camera_skew_noticed で inquiry Operation を開始できることを確認した。
- Operationが無い時、他actorのOperationしか無い時、statusがactive以外の時はOperation依存候補が出ないことをテストした。
- Operation依存候補も実行時gateを通るようにした。
- OperationはHUD候補に1条件だけ影響するが、GUI候補には影響しないことを確認した。
- phase自動進行、自動実行、MicroGoal上書き、GUI Action Compile、RO接続はまだ行っていない。
- `pytest -q` all greenを確認した。

### 気づき

- Operationが初めてHUD候補の出方に影響した。
- ただし影響は `required_operation_type` という1条件だけに絞ったため、GUIやMicroGoalを壊さずに縦切りできた。
- 次に必要なのは、Operationを支えるGUI基礎動詞やactor_location更新経路の整理。

### 次回の最初の一手

- Session53として、Operationを支えるGUI基礎動詞補強とactor_location runtime移動経路を検討する。

## 2026-07-05（Session52-B: HUD actionからOperationを1本だけ開始）

### 今日やったこと

- 刑事HUD action「聞き込みを始める」から inquiry Operation を開始できるようにした。
- active_operationは actorごとに0..1で維持し、director_world["actor_operations"] に保存した。
- Operation.MiniGoalとして「最初の証言を取る」を表示できるようにした。
- 同じHUD actionを2回実行してもOperationが重複しないようにした。
- required_discovery未達や他actorからの直接requestではOperationが開始しないことを確認した。
- Operation開始後もGUI gatingに影響しないことをテストで固定した。
- OperationによるHUD候補変化、自動phase進行、自動実行はまだ行っていない。
- `pytest -q` all greenを確認した。

### 気づき

- Operationは、まずHUD actionから立つ文脈として扱えるようになった。
- まだGUIアクションへコンパイルせず、Operation表示と保存だけに留めたことで、安全に縦切りできた。
- GUI基礎動詞の補強は今後必要だが、Session52-Bではまだ扱わない方が安全。

### 次回の最初の一手

- Session52-Cとして、required_operation_typeでHUD候補に1条件だけ影響させる。

## 2026-07-05（Session52-A: active_operation保存・表示スケルトン）

### 今日やったこと

- actorごとにactive_operationを0..1で持てる最小スケルトンを実装した。
- `director_world["actor_operations"]` にOperationを保存する方針にした。
- OperationはYAML roundtrip / HUD save-loadで残るようにした。
- `world_defaults` 適用時に `actor_operations` が潰れないようにした。
- Director HUDにactive actorのOperation / MiniGoalをread-only表示した。
- switch_characterでOperation表示がactive actorに追従するようにした。
- OperationがGUI gatingに影響しないことをテストで固定した。
- HUD actionからOperation開始、自動phase進行、自動実行はまだ行っていない。
- `pytest -q` all greenを確認した。

### 気づき

- Operationは最初から実行単位にせず、保存される文脈として置くだけでも大きな一歩。
- GUIアクションの厳格判定を守ったまま、Operation表示だけを足すことで安全に足場を作れた。
- 次はHUD actionからOperationを1本だけ開始する縦切りに進める。

### 次回の最初の一手

- Session52-Bとして、HUD actionからOperationを1本だけ開始する。

## 2026-07-02（Session52-0: Operation前提修理）

### 今日やったこと

- Fable5外部アーキテクチャレビューで指摘された重大リスク2件を、Operation実装前に修理した。
- discovery書き込み経路を actor bucket = `actor_discoveries[actor_id]` に寄せた。
- legacy `affordances.discoveries` はactive actor viewの互換キャッシュとして扱い、正本にしない方針を強めた。
- affordance_bridge / ActionPipeline 経由で獲得したdiscoveryがHUD refreshで消えないようにした。
- TPO HUD / pack actionの実行時ゲートを追加した。
- 表示時だけでなく実行時にも actor_id / ActorMode / discovery / interaction_scope を再チェックするようにした。
- 他actor用HUD actionを直接requestしても実行されず、effectsが適用されないことをテストした。
- `pytest -q` all greenを確認した。

### 気づき

- Operationを載せる前に、read側だけでなくwrite側もactor別化する必要があった。
- HUDに表示されているかどうかだけに頼らず、実行時にも必ずgateを通す必要がある。
- Operationは「誰の文脈か」が本質なので、actor_idの実行時検証はOperation前の必須条件だった。

### 次回の最初の一手

- Session52として、actorごとの `active_operation` 最小スケルトンを実装する。

## 2026-06-30（Session51-E: RC別discovery語彙 / HUD_DEBUG注入整理）

### 今日やったこと

- Session51-DでActorModeが整理された結果、discovery語彙の粗さが見えたため、RC別discovery語彙を整理した。
- actor別discovery catalogを導入した。
- 愉快犯用discoveryとして、挑発・撹乱・エスカレート系を起動する語彙を追加した。
- HUD_DEBUGのdiscovery注入候補をactive actorに応じて切り替えるようにした。
- PROVOKEで挑発系HUD候補が出るようにした。
- unsafe_route_identifiedへの依存を少し減らした。
- discovery inventoryでは、HUD_DEBUG dropdownが `discovery_rules` 由来のみを見ており、TPO HUD候補の `required_discoveries` が注入候補に出ていないことを確認した。
- 「Aが知ったことをBが知る」メタ認識は今回は実装せず、将来課題として残した。
- `pytest -q` all greenを確認した。

### 気づき

- ActorModeを整理すると、次に必要になるのはdiscovery語彙の整理だった。
- 愉快犯は、逃走だけでなく、顔を見られた危険・挑発の隙・偽装材料・エスカレート衝動などの内的/状況的discoveryを持つと、一気に別キャラクターらしくなる。
- メタ認識は面白いが、まずは明示discoveryで十分。

### 次回の最初の一手

- Session52に向けて、active_operationの最小スケルトンを検討する。

### 整理メモ

Session45〜Session50は、Prototype Demo #1前後の中核開発ログとして当面LOGBOOK.mdに残す。
将来的に肥大化した場合は、`general_documents/diary/` に「Demo #1開発アーカイブ」として退避する。

## 2026-06-30（Session51-D: Trickster mode taxonomy / HUD候補整理）

### 今日やったこと

- 愉快犯側のActorModeを FLEE / MISLEAD / PROVOKE / ESCALATE の4系統に整理した。
- FLEEに集中していたHUD候補を、逃走・撹乱・挑発・エスカレート系に分配した。
- 「偽の痕跡を残す」などの重複候補を整理した。
- 「目撃証言を撹乱する」をMISLEAD系候補として扱うようにした。
- DirectorModeは従来通り FREEZE / PURSUE / WITNESS / FLEE を維持した。
- GUI直接行動のsame-location gatingは維持した。
- `pytest -q` all greenを確認した。

### 気づき

- 愉快犯はFLEE一本では表現が狭く、逃走・撹乱・挑発・エスカレートに分けることでHUD候補の意味が見えやすくなった。
- Operation実装前にActorMode語彙を整理することで、後続のactive_operation設計が作りやすくなる。
- DirectorModeとActorModeは同じ語彙である必要はなく、当面はDirectorModeを主人公側・世界側の大きな空気として維持する。

### 次回の最初の一手

- Session52に向けて、active_operationの最小スケルトンを検討する。

## 2026-06-30（Session51-C: TPO HUD候補の小さな縦切り）

### 今日やったこと

- Session51-Bで直接行動が消えた空白に、packベースのTPO HUD候補を追加した。
- 刑事側に追跡・推理・証言照合・包囲寄りの候補を追加した。
- 愉快犯側に撹乱・逃走経路変更・偽痕跡寄りの候補を追加した。
- actor_id / ActorMode / location / discovery による出し分けを確認した。
- GUI直接行動のsame-location gatingは維持した。

### 気づき

- 別locationの相手とは直接戦えないが、物語的には追跡・推理・撹乱で戦える。
- 51-CはOperation前の前段階であり、HUD候補が作戦文脈へ育つための素材を増やす回になった。

### 次回の最初の一手

- Session52に向けて、active_operationの最小スケルトンを検討する。

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
