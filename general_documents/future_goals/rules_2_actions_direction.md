

今後の展望を整理してお伝えします。

---

## 📌①【rules.json → action（s_function）.py への登録の展望】

### 🧩 想定されるワークフロー（案）

**step 1：AI提案ルールをJSON化（完了済）**  
- AIが自然言語で提案したルールをパーススクリプトを使い、`rules.json`へ変換。

**step 2：rules.jsonを元に`actions.py`や`action_functions.py`へ登録**  
- 今後の目標はここを **自動化 or 半自動化** することです。

具体的には、次のような方法を検討します：

---

### ⚙️【方法A：テンプレートベースの半自動化（現実的な短期的目標）】

- JSONファイルの各ルールの`requirements`や`effects`などのフィールドを使い、あらかじめ準備したテンプレート（関数）に自動的に当てはめる方法です。

**例：**
```json
{
  "name": "石像との会話クールダウン延長",
  "requirements": {"action_count": 3, "time_span": 30},
  "effects": {"extend_cooldown": 300}
}
```

- このJSONをテンプレートに流し込み、以下のようなPythonコードを生成します。

**自動生成例：**
```python
def statue_talk_extended_cooldown(character_status, game_state):
    recent_actions = game_state.get_recent_actions("石像に話す（クールダウン）", 30)
    if len(recent_actions) >= 3:
        game_state["cooldown_status"]["古代の石像"] = time.time() + 300
```

---

### ⚙️【方法B：LLMを使った動的スクリプト生成（中〜長期目標）】

- **LLMを利用してPythonスクリプトを動的に生成** します。
- GPT-4o（などの強力なLLM）にrules.jsonのルールを渡し、  
  「このJSONルールをPythonの関数として実装してください」と依頼します。

**この場合、LLMはどうやって理解する？**

- LLMは `rules.json` 内の項目（name、trigger_condition_text、requirements、effectsなど）を読み取り、それらを自然言語的に理解します。
- 事前にテンプレートを与えることで、具体的なコード生成を促します。

**プロンプト例：**
```
次のルールJSONを読み込み、以下のテンプレートに従ってPython関数を生成してください。

ルールJSON：
{
  "name": "アクション多様性ボーナス",
  "requirements": {"diverse_actions_count": 3},
  "effects": {"give_bonus": true}
}

テンプレート：
def action_diversity_bonus(character_status, game_state):
    # ここに実装を書いてください。
```

- LLMはプロンプトに従い、JSONを元に具体的なスクリプトを自動生成します。

---

### 📌【結論（現実的なロードマップ）】

**短期的な目標（次回のセッション）**
- まず『方法A』のテンプレートベースの半自動化を確立し、安定性を確保します。

**中長期的な目標（その後のセッション）**
- 『方法B』を実験的に取り入れ、自動化の範囲を広げ、徐々にAI主導のコード生成へと移行します。

---

