# quit_helper.py など ---------------------------------------------
import sys

def handle_quit(raw: str, game_state) -> None:
    """
    raw : ユーザーが入力した文字列
    game_state["running"] を False にして SystemExit を送出する。
    呼び出し元で try/except しなくても、メインスレッドなら
    raise SystemExit で安全にプロセス終了できる。
    """
    if raw.lower() in {"q", "quit", "exit"}:
        print("\n⏹  終了コマンドを受信しました。ゲームを終了します。")
        game_state["running"] = False
        raise SystemExit
