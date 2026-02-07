# LOGBOOK.md - 開発日誌（雑談OK）

ルール:
- 1エントリは短くていい（箇条書きでもOK）
- 「気持ち」+「技術メモ」+「次回の最初の一手」を1つ入れると最強
- 長文になったら、`general_documents/diary/` に退避してリンクを貼る

---

## 2026-01-31（Session 22）
### 気分 / 雑談
- 数週間ぶりにVibe Codingしたけど、Claude Codeでこんなに簡単に出来ると知って、もっと早く始めればよかった。
- でもモチベの炎はいつ小さくなるか分からない。

### 今日やったこと（結果）
- simulation.pyを大幅リファクタ（860→535行）
- GameContext導入、HUDCallbacks分離、不要コード削除
- pytestオールグリーン / シミュレーション動作確認

### 発見（次にも効く）
- Claude Codeは「現物を読んでまとめて直す」能力が強い。引き継ぎはファイルに固定すると勝ち。

### 痛み / ひっかかり
- 初期game_stateがHero/Lunaのまま
- RC挙動がrunと混ざっている気がする（明示起動に分離したい）

### 次回の最初の一手（15分でやる）
- `python -m src.simulation` を通す → その上で game_state 初期設定を刑事/愉快犯に変更する

### リンク / 詳細ログ
- `general_documents/diary/session22_summary_2026_1_31.txt`

---

## 2026-02-01（Session 23）
### 気分 / 雑談
- Claude Codeが一気に作業してくれて、世界が急に「喋りだした」感じ。
- MicroGoalをやり尽くした寂しさに、手応えのある対策が入って安心。
- でも日替わりでもMicroGoalが復活しない……？履歴のリセットと復活は違う……？今度要相談。
- 今日の作業で「何もしてないのに時間だけ進む」違和感と、「誰かいる(Anyone else?)」感が同居してる。

### 今日やったこと（結果）
- **タスク0**: Session23作業ブランチ `feature/session23-conversation-microgoal` を作成して作業
- **タスク1**: 初期stateを `cop_trickster` パック準拠へ（刑事/愉快犯、関係性タグ、ロケーション/ターゲット）
- **タスク2**: `talk` アクション追加（テンプレ選択、`last_dialogue` をstateへ格納）
- **タスク3**: 日替わりで MicroGoal 消費履歴をリセット（枯渇対策MVP）
- **タスク4**: Choice自動生成 + action_key/label分離 + heart退避
  - `ui_visible`、`heart`（axis/value）を ActionSpec に追加
  - `choice_definitions` から自動生成へ移行（手動登録不要に）
  - 旧キー（日本語）→ 新action_key（英語）の互換マップ追加

コミット:
- 64adfe9: 初期state変更（cop_trickster pack参照、刑事/愉快犯、関係性タグ）
- 7e599e2: 会話MVP（talkアクション、テンプレート選択、last_dialogue）
- d159c89: 枯渇対策（日替わりで履歴リセット）
- b1db9e8: Choice自動生成（action_key/label分離、ui_visible、heart移植）

### 発見（次にも効く）
- 会話は生成AIなしでも「テンプレ×関係性タグ」で十分"ゲームっぽい"。
- packを素材（roles/locations/targets）に寄せて、init_stateが組み立てるのは拡張しやすい。
- Choiceを自動生成にすると、新アクション追加時に choice_definitions をいじらなくて済む。

### 追加作業（続き）
- **HUD_DEBUGログ整理**: デフォルトOFF、`config.yml` or 環境変数 `HUD_DEBUG=1` で有効化
  - `is_hud_debug_enabled()` を config_loader に追加
  - hud_callbacks.py / game_context.py / simulation.py の該当箇所をラップ
- **time_min統一**: GUI/HUD共通で action_definitions の time_min を反映
  - ActionPipeline: `function=None` のアクションでも `action_executed=True` にして時間進行を有効化
  - hud_callbacks: record.time_min → spec.time_min のフォールバック優先順位を修正
  - DoD: wait(5) で +5分、observe(3) で +3分、check_tip(5) で +5分

### 次回の最初の一手（15分でやる）
- 起動して **(1)wait** を押す → 時刻が +5分 → **(2)observe** で +3分 → **(3)talk** を1回実行の動作確認。→確認済。

---

## 2026-02-02（Session 24）
### 気分 / 雑談
- RCが暴走して時間がどんどん進む問題に本格対策。
- LLMの呼び出し制御も入れて、将来の拡張に備えた。

### 今日やったこと（結果）
- **Task24-0**: ブランチ運用整備
  - Session23を安定ブランチにmerge
  - Session24作業ブランチ `feature/session24-rc-throttle-llm-gating` を作成
- **Task24-1**: RCの`switch_character`封印
  - `rc.excluded_actions` を config.yml に追加
  - rc_ai.py で除外リストを参照してフィルタ
- **Task24-2**: LLM呼び出しゲート制御
  - `llm.mode`: off/player_only/rc_only/all
  - `llm.allow_actions`: アクション単位許可リスト
  - `llm.rate_limit`: calls_per_minute / calls_per_turn
  - フォールバックテンプレート対応
- **Task24-3**: RC連打・時間暴走の制御（3レバー）
  - レバーA: `rc.decision_interval_sec` (最短実行間隔)
  - レバーB: `rc.max_advance_minutes_while_input_pending` (時間予算)
  - レバーC: 制限超過時はno-op
- **Task24-4**: 睡眠アクションの実装
  - `start_sleep`: RC用、2分、眠りの開始
  - `sleep`: プレイヤー用、480分（8時間）
  - available_toで相互排他

コミット:
- 0ee3d03: RC excluded_actions
- 2e2ee2b: LLM gating
- 29e2c86: RC throttle
- ba7c8e8: sleep actions

### 発見（次にも効く）
- configベースの制御は柔軟で、後から調整しやすい。
- available_toでプレイヤー/RC向けアクションを分離できる。

### 次回の最初の一手（15分でやる）
- 起動して、RCが連打しないか確認。input_pending中に時間が暴走しないか確認。

---

## 2026-02-04（Session 25）
### 気分 / 雑談
- GUIカラーバグの原因特定に時間がかかったが、根本原因を突き止められて達成感。
- actor別emotion管理が入って、キャラ切替してもemotionが保持されるようになった。

### 今日やったこと（結果）
- **Task25-0**: ブランチ整理
  - バックアップ作成（backup/pre-session25-20260203）
  - mainを安定ブランチ（cursor-trial/microgoal-logging）に追従
  - 不要ブランチ削除＋アーカイブタグ付け（session23, session24, codex-patch, pack-format-normalize）
  - Session25作業ブランチ作成（feature/session25-gui-color-rc-heart）
- **Task25-1**: GUIカラーバグ修正
  - `emotions_by_actor` 導入（actor別emotion管理の正）
  - set_emotion後のworld.emotionによる上書き防止
  - switch_character後のUI追従（hud_cache_rev bump）
  - switch_character後のemotion delta適用スキップ
  - switch_character後のemotion_color復元（emotions_by_actor → actor.emotion_color）

コミット:
- 9abc255: Add: actor-specific emotion tracking (emotions_by_actor)
- cd3cf2b: Fix: switch_character UI refresh and actor-specific emotion display
- bd0056b: Fix: set_emotion now correctly updates actor emotion without being overwritten
- 5470928: Fix: switch_character no longer overwrites actor emotions

### 発見（次にも効く）
- 「可変の正」を明確にする（今回は`emotions_by_actor`）と、どこで上書きが起きているか追いやすい。
- action_pipelineの汎用処理（emotion delta適用など）が特定アクションの結果を上書きするパターンに注意。

### 痛み / ひっかかり
- world.emotion（グローバル）とactor.emotion_color（インスタンス）の二重管理が複雑。将来的には統一したい。

### 次回の最初の一手（15分でやる）
- 起動して set_emotion(0,0,0) → switch×2 → 刑事が(0,0,0)のまま保持されるか確認。

---

## 2026-02-04（Session 25 続・根治）
### 今日やったこと（結果）
- **Task25-1 根治**: emotion上書き経路の完全遮断
  - **根本原因**: `action_pipeline.py`の`apply_emotion_delta`がグローバルな`world["emotion"]`(127,127,127等)にdeltaを適用し、その結果をSoT(`emotions_by_actor`)に書き戻していた
  - **修正1**: delta適用前に`emotions_by_actor[actor]` → `world["emotion"]`へロード（delta計算の入力を正しく）
  - **修正2**: emotionブロック末尾で常に`world["emotion"]`をアクティブactorのSoTと同期（director.tick等の読み取り用）
  - 変更ファイル: `src/ui/action_pipeline.py` のみ（最小修正）

### 発見（次にも効く）
- `world["emotion"]`はグローバル1個で、actor別ではなかった。delta適用の入力にこれを使うと、set_emotionの値が消える。
- SoTを明確にしたら「SoTからロード → 処理 → SoTへ書き戻し」のパターンを徹底すること。

### DoD確認手順
- 刑事で set_emotion(0,0,0) → observe → switch×2 → (0,0,0)のまま
- 愉快犯も同様に保持
- どのアクション後もemotions_by_actorが初期値に巻き戻らない

---

## 2026-02-07（Session 26）
### 気分 / 雑談
- RO（Reversible Operator）の最初の一歩。まだ助言を出すだけだが、ログ識別子の整備から入ったので基盤は堅い。
- 「誰が決めたか」をログに残す仕組みが入ったことで、将来の分析がずっと楽になるはず。

### 今日やったこと（結果）
- **Task26-0**: ログ識別子の最小改修
  - `logger.py` の `log_action()` に `controller_id` / `actor_rc_id` 自動付与ロジックを追加
  - RC_AI → `controller_id="RC_AI:刑事"`, GUI → `controller_id="PLAYER:GUI"` など
  - `actor_rc_id` = `actor_id` のコピー（将来の表示名分離に備える）
  - レガシー呼び出し（`actor` フィールド）にもfallback対応
  - 呼び出し側が明示的に `controller_id` を渡せば上書きしない（RO予約対応）
- **Task26-1 (Phase A)**: RO雛形（助言＋理由）
  - `src/ro/ro.py` 新規作成: `recommend()` がplayerログ直近N行を読みスコアリング
  - スコアリング: microgoal近接(+2.0) / 連打抑制(-2.0/-1.0) / 頻度ペナルティ
  - 出力: `action_id` + `why`（必須）+ `risk` / `plan_b`（任意）
  - `config.yml` に `ro.enabled: false` / `ro.log_window: 50` 追加
  - `action_pipeline.py`: playerアクション後に自動呼び出し、`game_state["ro_recommendation"]` に格納
  - RO日誌: `data/logs/ro_diary_latest.jsonl` に `controller_id="RO:<actor>"` 形式で出力

コミット:
- c72773e: Feat: auto-inject controller_id and actor_rc_id into all JSONL log lines
- 4d728c2: Feat: add RO (Reversible Operator) Phase A – advice from player log

### テスト
- `tests/test_logger_ids.py`: 6ケース（RC_AI/GUI/HUD、レガシーfallback、明示値保持、空入力）
- `tests/test_ro.py`: 7ケース（無効時None、microgoalブースト、連打抑制、diary出力、空候補、plan_b、空ログ）
- 既存テスト（test_director.py）含め全18テスト通過

### 発見（次にも効く）
- ログの一元化ポイント（`log_action`）に自動付与を入れると、呼び出し側の変更ゼロで全行に反映できる。
- ROは `try/except` でラップして「ROの障害がゲームプレイを止めない」を保証する設計が大事。
- `_ro_cfg()` を分離しておくとテストのmockが楽。

### 次回の最初の一手（15分でやる）
- `config.yml` の `ro.enabled: true` にして起動 → GUIでアクション実行 → `data/logs/ro_diary_latest.jsonl` にdiaryが書かれることを確認。
