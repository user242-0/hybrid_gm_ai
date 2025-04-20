import json
import re

def parse_ai_response_to_json(ai_text):
    # AI提案を「- ルール名:」の出現で区切る
    rules_texts = re.split(r"\s*-\s*ルール名[:：]\s*", ai_text.strip())
    parsed_rules = []

    for rule_text in rules_texts:
        if not rule_text.strip():
            continue  # 空文字はスキップ

        # 項目を明示的に抽出
        name = rule_text.split("\n")[0].strip()
        
        # 「トリガー条件」と「期待される効果」を明示的に探す
        trigger_match = re.search(r"トリガー条件[:：]\s*(.+?)(?:\n\s*-\s*期待される効果[:：]|$)", rule_text, re.DOTALL)
        effect_match = re.search(r"期待される効果[:：]\s*(.+)", rule_text, re.DOTALL)

        if not (trigger_match and effect_match):
            continue  # 必須項目が欠けている場合はスキップ

        rule = {
            "name": name,
            "trigger_condition_text": trigger_match.group(1).strip(),
            "effect_description": effect_match.group(1).strip(),
            "requirements": {},
            "effects": {},
            "available_to": ["player"],
            "confidence": 0.9
        }

        parsed_rules.append(rule)

    return parsed_rules

# 改めて動作確認
if __name__ == "__main__":
    ai_response = """
- ルール名: 休憩後のインタラクション制限
- トリガー条件: プレイヤーが「休む」アクションを「古代の石像」や特定のオブジェクトに対して行った直後
- 期待される効果: 「休む」アクション後、プレイヤーは少なくとも5秒間は同じオブジェクトまたは同じ場所での新たなアクションを実行できない。このルールにより、プレイヤーが休憩後に即座に新しいアクションを行うのではなく、ゲームの世界観と状況を一旦考慮する時間を持てるようになる。

- ルール名: 石像との対話クールダウン
- トリガー条件: プレイヤーが「石像に話す」アクションを行った直後
- 期待される効果: 一度「石像に話す」アクションが成功した後、同じ石像に対しては一定時間（例: 10秒）再度話しかけることができなくなる。このルールにより、プレイヤーは石像との対話を慎重に選択し、対話の内容をより深く理解する時間を得ることができる。
"""

    parsed_json = parse_ai_response_to_json(ai_response)
    print(json.dumps(parsed_json, ensure_ascii=False, indent=2))

    # 改善後のJSONファイルへ出力
    with open("data/rules/ai_generated_rules_auto_v2.json", "w", encoding="utf-8") as f:
        json.dump(parsed_json, f, ensure_ascii=False, indent=2)
