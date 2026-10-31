director_world：世界の真実を保持
perceived_world：RCごとの認識を保持
memory：RCが経験した出来事を保持
belief：RCが現在信じている内容を保持
Operation progress：進行中の行動状態を保持

(director_)world["actor_operations"]：
をOperationの永続化上の唯一の正本として維持する

OperationInstance：正本のdomain表現
OperationStore：正本への唯一の窓口
OperationRuntime：書き込みを命令できる者

---------------------------------------------------
正本所持者
---------------------------------------------------

World state
→ director_world

Operation
→ world["actor_operations"]

Operation history
→ world["operation_transition_history"]

Memory
→ world["actor_memories"]

Belief
→ world["actor_beliefs"]

## OperationInstanceの責務境界（2026-09-27追記）

| 観点 | 担当・境界 |
|---|---|
| **1. Owner** | 永続化上の正本は引き続き `world["actor_operations"]`。OperationInstanceは、そこから切り離して扱う一件のOperationのdomain表現。独立した第二の正本にはしない。 |
| **2. Writer** | 正本を直接更新するのはStoreだけ。更新の指揮はRuntimeが担当し、その配下の開始・進行処理がStoreへ保存する。Instance自身はworldへ書き込まない。 |
| **3. Coordinator** | Operation内の統括はRuntime。Actionのeffects確定を契機として進行判定→保存→transition記録→開始処理を呼ぶ。Command全体の順序は上位のGameCommandServiceが統括する。 |
| **4. Observer** | 呼び出し側が結果・失敗情報から「どこまで確定したか」を把握する境界。Instance単体では担当できず、Runtimeの結果とGameCommandResult、ログで扱う。 |


## Operationアクセス境界（2026-09-21実装）

- 実行時にOperation正本 `world["actor_operations"]` を直接読み書きするのは `src/operation_store.py` の `OperationStore` 内部だけ。保存先・actor bucket・既存dict/YAML形式は維持する。
- 読み取り側は `src/operation_reader.py` の `get_active_operation(world, actor_id)` を使う。戻り値はネストを含むdeepcopyで、変更しても正本へ反映されない。取得だけで初期化・修復は行わない。Storeインスタンスや保存関数は読み取り側へ渡さない。
- 更新はOperationRuntimeが統括する開始・進行の経路からStoreへ明示保存する。開始条件は `actor_operations.start_operation_once`、進行条件は `operation_progression.advance_operation_after_action` に残す。Storeは進行条件を判断しない。
- Storeの保存入力もdeepcopyする。開始の新規・既存同一IDの両成功経路もdetached snapshotを返す。正本の初期化用生参照はStoreのprivate helperに閉じ、旧公開 `ensure_actor_operations` は廃止した。
- `actor_operations` の旧get/formatはreaderの再公開、set/clearはStoreへの互換ラッパーとして残す。新しい読み取り利用者はこの互換モジュールをimportしない。

### 読む側／更新する側

| 利用者 | 入口 | 正本更新 |
| --- | --- | --- |
| HUD / Director / Perceived World / RCContext | operation_reader | しない |
| Operation transition recorder | operation_readerでpost-state照合 | Operationは更新しない。履歴への記録は従来どおり |
| Runtime配下の開始・進行処理 | OperationStore.get_active_instance / set_active_instance | 明示保存時だけ |
| world defaults適用 | OperationStore.merge_world_defaults | 新規world採用時の初期化 |

2026-10-31（Session60-4チェックポイント2）: 独立クラス `OperationInstance` をStore境界と開始・進行へ接続した。永続化上の正本は引き続きdictであり、Instanceは正本から切り離された一件のデータ表現。保存・開始条件・進行条件は持たない。

- `OperationStore.get_active_instance(actor_id)` は既存dict取得経路からInstanceへ変換する。読み取りで初期化・修復をしない。欠落項目・None・未知項目・不正なフィールド値を補正せず保持する。
- `set_active_instance(actor_id, instance)` は有効なworld/actorに対してInstance型を確認し、`to_dict()`の変換を完了してから既存dict保存経路へ渡す。変換失敗では正本やbucketを変更しない。型以外のdomain適格性は判定しない。None等はTypeErrorで、clearは従来の明示APIを使う。world/actorが無効なら既存writer同様no-op。
- 旧 `get_active_operation` / `set_active_operation` / clearは従来の互換性を維持する。readerは引き続きdetached dict/Noneを返し、Instanceやwriterを公開しない。
- 開始は新規Instanceを構築してStoreへ保存する。新規・既存同一IDとも公開戻り値はdetached dict。進行は取得Instanceを判定し、`with_changes`でphaseとmini_goalを置き換えた別Instanceを保存する。
- 入出力と変更前後のネスト参照を分離する。保存済みdictとInstanceの二重正本は作らない。既存ID・保存schema・部分成功契約は維持し、transaction/rollbackは追加していない。Operation更新後にtransition記録が失敗しても更新は残る。Runtimeの失敗通知構造化は対象外。

### world採用・保存復元

`world_defaults.apply_world_defaults` はOperation subtreeをStoreへ委譲する。Store内部で既存Operation優先のマージを行い、既存world・pack defaults双方から参照を切る。他world項目のマージ方針は維持する。defaultsを適用しない既存の早期returnは維持する。

`simulation.save_director_world` / `load_director_world` はworld全体をYAMLで輸送し、`HUDCallbacks.on_load` は復元worldを採用する。これらの汎用serialize／deserialize／world参照差し替えは許容し、Operation subtreeを個別に取得・編集する例外は作らない。新worldを渡すたびにStoreを構築し、旧worldに紐づくStoreをキャッシュしない。Memory→Belief catch-upと保存形式も従来どおり。

### 保証の範囲と検査

snapshotの可変性は許容するが、正本との参照共有は許容しない。共有world自体は依然としてdictなので、Pythonの動的importやprivate属性経由まで絶対に禁止するセキュリティ機構ではない。

`tests/test_operation_access_boundary.py` はsrc内の正本キーリテラルをStore以外で使うこと、および許可した境界以外からStore／開始・進行モジュールをimportすることを検知する。動的文字列構築・reflection・汎用world輸送の安全性まで証明する検査ではない。tests内のfixture準備・破損データ作成は対象外。

### 二段階の完了条件

1. 集約とコピー保証: Store、互換ラッパー、world defaults境界、`tests/test_operation_store.py`。取得／保存入力／開始両経路／明示保存／actor分離／保存復元を検証。
2. 読取・更新経路の分離: reader、各読取利用者のimport変更、progressionのStore利用、境界検査。Runtime→進行→transition記録→開始、GCS→Memory→Belief→post-action→fresh Bundleの順序と部分成功契約は維持。
