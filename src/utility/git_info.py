# src/utility/git_info.py
import subprocess

def get_commit_hash(default: str = "unknown") -> str:
    """
    現在のGitコミットハッシュを返す。Gitが無い/ワークツリー外なら 'unknown'。
    """
    try:
        return subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip()
    except Exception:
        return default
