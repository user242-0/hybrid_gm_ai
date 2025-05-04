


### どう整理するのがベターか？

| 配置案                                                                             | 具体例                                                                                     | 長所                                       | 短所                                                       |
| ------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------- | ---------------------------------------- | -------------------------------------------------------- |
| **A. 既存 `utility.py` に追記**<br>(＝フラット構成のまま)                                      | `src/utility.py` に `get_contextual_target()` を追加                                        | *ファイルを増やさない*・import が短い                  | ユーティリティが増えてくると 1 ファイルが肥大化                                |
| **B. `src/utility/` サブパッケージを作る**<br>（`utility/__init__.py` + `targeting.py` など） | `text\nsrc/\n ├─ utility/\n │    ├─ __init__.py\n │    └─ targeting.py   # ← 関数をここに\n ` | 機能ごとにファイル分割 → 可読性◎<br>ユーティリティが増えても整理しやすい | フォルダと import パスが 1 階層増える                                 |
| **C. `actions/utility.py` に置く**                                                 | `src/actions/utility.py`                                                                | “ゲーム内ロジック” 系ユーティリティを actions 配下で完結       | `actions` は “プレイヤーが選ぶ行動” という粒度で使うことが多く、汎用関数を入れると意味が混ざりがち |

---

### 推奨：**B. `src/utility/` サブパッケージ**

理由

1. **今後ユーティリティが増える**（ターゲティング、ダイスロール、文字装飾、日付など）
2. **actions と役割が違う**
   `actions/` は “ゲームコマンド” の実装置き場、ユーティリティは “あらゆる層で再利用する汎用関数”
3. **import が整理しやすい**

   ```python
   from src.utility.targeting import get_contextual_target
   ```

---

## 実装手順

```bash
# 1. ディレクトリ作成
mkdir src/utility
touch src/utility/__init__.py     # 空でOK
touch src/utility/targeting.py
```

**`src/utility/targeting.py`**

```python
def get_contextual_target(action_key, actor, game_state, *args):
    if action_key == "switch_character" and args:
        return args[0]            # <target_name>
    if action_key == "戦う" and game_state.get("enemy"):
        return game_state["enemy"].name
    return game_state.get("current_target")
```

**メインループ（simulation.py）**

```python
from src.utility.targeting import get_contextual_target
...
target_for_log = get_contextual_target(action_key, actor, game_state, *args)
logger.log_action(actor=actor.name,
                  action_key=action_key,
                  target=target_for_log)
```

---

### 既存 `utility.py` との兼ね合い

* **小規模プロジェクトのうちは** フラットでも構いません。
  ただ、`utility.py` が 400 行を超えたら **機能ごとにサブパッケージへ切り出し**を検討すると保守が楽です。
* すでに `src/utility.py` がある場合は

  * **“汎用だけど独立性が高いもの” → 新しい `utility/*.py` に移動**
  * **“2 行程度で他が依存していない便利関数” → 既存ファイルに残す**
    とレベル分けするとスッキリします。

---

## import 例（最終形イメージ）

```python
# 汎用
from src.utility.targeting import get_contextual_target
from src.utility.randomtools import roll_dice

# アクション定義
from src.actions.combat import engage_combat
from src.actions.social import talk_to_statue
```

この構成なら **役割が URL のように読めて**、IDE の “フォルダ一覧” でも分かりやすくなります。
