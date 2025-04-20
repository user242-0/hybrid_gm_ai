import json
import re

def parse_ai_response_to_json(ai_text):
    parsed_rules = []

    # まず、どちらの形式かをチェック（番号付きか、-ルール名か）
    if re.search(r"\d+\.\s*\*\*ルール名\*\*", ai_text):
        rules_texts = re.split(r"\d+\.\s*\*\*ルール名\*\*[:：]?\s*", ai_text.strip())
        name_pattern = r"(.*?)\n"
        trigger_pattern = r"\*\*トリガー条件\*\*[:：]\s*(.+?)(?:\n\s*-\s*\*\*期待される効果\*\*[:：]|$)"
        effect_pattern = r"\*\*期待される効果\*\*[:：]\s*(.+)"
    else:
        rules_texts = re.split(r"-\s*ルール名[:：]\s*", ai_text.strip())
        name_pattern = r"(.*?)\n"
        trigger_pattern = r"トリガー条件[:：]\s*(.+?)(?:\n\s*-\s*期待される効果[:：]|$)"
        effect_pattern = r"期待される効果[:：]\s*(.+)"

    for rule_text in rules_texts:
        if not rule_text.strip():
            continue

        name_match = re.match(name_pattern, rule_text.strip())
        trigger_match = re.search(trigger_pattern, rule_text, re.DOTALL)
        effect_match = re.search(effect_pattern, rule_text, re.DOTALL)

        if not (name_match and trigger_match and effect_match):
            continue

        rule = {
            "name": name_match.group(1).strip(),
            "trigger_condition_text": trigger_match.group(1).strip(),
            "effect_description": effect_match.group(1).strip(),
            "requirements": {},
            "effects": {},
            "available_to": ["player"],
            "confidence": 0.9
        }

        parsed_rules.append(rule)

    return parsed_rules


# ここから変更：ファイルから読み込んで解析するように変更
if __name__ == "__main__":
    with open("data/rules/raw/ai_rules_raw_v2.txt", "r", encoding="utf-8") as file:
        ai_response = file.read()

    parsed_json = parse_ai_response_to_json(ai_response)
    print(json.dumps(parsed_json, ensure_ascii=False, indent=2))

    with open("data/rules/blue_v2.json", "w", encoding="utf-8") as f:
        json.dump(parsed_json, f, ensure_ascii=False, indent=2)
