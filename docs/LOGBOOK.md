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
