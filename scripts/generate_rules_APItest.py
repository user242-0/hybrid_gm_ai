import json
import openai
import os
from dotenv import load_dotenv

# .envから環境変数を読み込む
load_dotenv()

# .env内にあるAPIキーを使う
openai.api_key = os.getenv("OPENAI_API_KEY")

def load_logs(filename="data/logs/gameplay_log.json"):
    with open(filename, "r", encoding="utf-8") as file:
        logs = [json.loads(line) for line in file]
    return logs

def analyze_logs_with_ai(logs):
    prompt = f"""
    以下のゲームプレイログを分析し、新しいルールや改善点を提案してください。

    ゲームプレイログ：
    {json.dumps(logs, ensure_ascii=False, indent=2)}

    提案するルールは以下の形式でお願いします。
    - ルール名
    - トリガー条件
    - 期待される効果
    """

    response = openai.chat.completions.create(
        model="gpt-4o",  # 最新のモデル指定可能
        messages=[
            {"role": "system", "content": "あなたはゲームマスターAIとしてゲームログを分析し、適切なルールを提案します。"},
            {"role": "user", "content": prompt}
        ],
        temperature=0.7
    )

    # AIの回答を取得
    result = response.choices[0].message.content
    return result

# 実際に動かす
if __name__ == "__main__":
    logs = load_logs()
    ai_proposal = analyze_logs_with_ai(logs)
    print("AIが提案した新ルール:")
    print(ai_proposal)
