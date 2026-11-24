# Kept as a historical reference. Never load or print credentials here.
if False:
    import os
    from dotenv import load_dotenv
    import openai

    # .envから環境変数を読み込む
    load_dotenv()

    # .env内にあるAPIキーを使う
    openai.api_key = os.getenv("OPENAI_API_KEY")

    # 動作確認
    print(openai.api_key)  # APIキーが表示されれば成功

if __name__ == "__main__":
    print("旧APIキー診断は無効です。")
