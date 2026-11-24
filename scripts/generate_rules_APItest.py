import json

# This historical experiment is isolated from the game's LLM settings.
_LEGACY_API_ENABLED = False

def load_logs(filename="data/logs/gameplay_log_v2.json"):
    with open(filename, "r", encoding="utf-8") as file:
        logs = [json.loads(line) for line in file]
    return logs

def analyze_logs_with_ai(logs):
    if not _LEGACY_API_ENABLED:
        raise RuntimeError("Legacy API experiment is disabled.")

    import os

    import openai
    from dotenv import load_dotenv

    load_dotenv()
    openai.api_key = os.getenv("OPENAI_API_KEY")

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
    if _LEGACY_API_ENABLED:
        logs = load_logs()
        ai_proposal = analyze_logs_with_ai(logs)
        print("AIが提案した新ルール:")
        print(ai_proposal)
    else:
        print("旧ルール生成API実験は無効です。")
