### Relative vs. Absolute imports – どちらを選ぶか？

|  | **絶対 import**<br>`from src.character_status import CharacterStatus` | **相対 import**<br>`from .character_status import CharacterStatus` |
|---|---|---|
| **PEP 8 の推奨** | ✅　第一候補（可読性が最も高い） | ◯　「同一パッケージ内」でのみ許容 |
| **実行形態** | *スクリプト直叩き* `python src\simulation.py` でも動く（PYTHONPATH を通す／editable-install する前提） | `python -m src.simulation` や `pip install -e .` 後の実行に向く<br>（単独実行だと “no parent package” エラー） |
| **可読性** | どこからでも「パッケージ階層」が一目で分かる | すぐ近くのモジュールと分かりやすいが、深いツリーになると「…」が増えて見づらい |
| **リファクタ耐性** | パッケージ名が変わらない限り安全 | フォルダ移動に強い（上位にドットを追加するだけ） |
| **ツール互換**<br>(mypy / IDE ジャンプ) | ほぼ確実に解決できる | IDE によっては誤認識することも |
| **テスト実行** | ルートを PYTHONPATH に入れれば OK（`pytest.ini` で固定可能） | `pytest` をパッケージルートから走らせればそのまま動く |

---

## あなたのプロジェクトでの実戦的な選択肢

| ニーズ | ベターな選択 | 理由 / 運用例 |
|-------|-------------|---------------|
| **「`python src\simulation.py` で気軽に回したい」** | **絶対 import** | ① `src` を *installable package* にする<br>&nbsp;&nbsp;・ルートで `pip install -e .`<br>&nbsp;&nbsp;・または `pytest.ini` に `pythonpath = .`<br>② VS Code なら `.env` に `PYTHONPATH=.` |
| **「将来 pip 配布 / CI で `-m` 起動へ統一したい」** | **相対 import** | エンドユーザーは `python -m src.simulation` で実行。<br>アプリ用に `main.py`（ルート）を用意し<br>`from src.simulation import main` へ委譲すると楽 |

> **実務の感覚**  
> 1. **ライブラリ志向（他プロジェクトから import したい）** ➜ 絶対 import  
> 2. **社内ツールやゲーム本体の“内部実装”** ➜ 相対 importでも可  
> 3. **どちらでも** “コード検索しやすい方” をチーム基準に決めて統一するのが最重要

---

## おすすめフロー（今回のケース）

1. ルートに **`pyproject.toml`** を置き *editable-install*  
   ```toml
   [project]
   name = "hybrid_gm_ai"
   version = "0.1.0"
   ```
   ```bash
   pip install -e .
   ```
   * これで **絶対 import** がどこでも解決
   * `python src\simulation.py` も `pytest` も環境変数不要
2. テスト実行を CI に載せる場合もパスいじりゼロ

> *移行コストを最小化* したいなら  
> **相対 import + `python -m src.simulation`** で走らせる形でも良いですが、  
> **「直叩き」習慣が強いなら絶対 import + editable-install** が後々ストレスが少ないです。

---

### まとめ

- **可読性とツール連携の安心感**を重視 ⇒ **絶対 import**（パッケージとして扱う）
- **フォルダの組み替えに強い最小構成**を保つ ⇒ **相対 import**  
  （ただし `-m` 起動が前提）

プロジェクトを **最終的に配布物／ライブラリ** として仕立てるつもりなら、  
今の段階で **絶対 import + editable-install** に寄せておくのが無難です。

### 結論だけ先に
- **“全部絶対 import に統一しなければ動かない” わけではありません**。  
- ただし **ルールを決めておかないと読みづらい & ミスが起きやすい** ので、  
  **「パッケージをまたぐ参照＝絶対」「同じサブパッケージ内＝相対」** くらいで揃えておくのが実務ではいちばんスムーズです。

---

## 1. PEP 8 が推奨する基本方針
| 推奨 ◎ | 許容 ◯ | 非推奨 △ |
|---------|--------|-----------|
| **絶対 import**<br>`from src.character_status import CharacterStatus` | **同一パッケージ内の相対 import**<br>`from .helpers import foo` | **階層をまたぐ相対 import**<br>`from ..utilities.helpers import foo` |

* **可読性とツール対応（IDE 補完 / mypy）** は“絶対”が最強。  
* 相対 import は “隣や子ディレクトリだけを指すときに短く書ける” のがメリット。  
* 上位階層へ `..` を何段もさかのぼる相対 import は可読性が落ちるので避ける。

---

## 2. ハイブリッド‐ゲームAIプロジェクトでの “おすすめ運用”
| ケース | 推奨書き方 | 理由 |
|--------|-----------|------|
| **サブパッケージをまたいで参照**<br>(例 `src.simulation → src.action`) | `from src.action.turn_manager import TurnManager` | どこから読んでも一目で場所がわかる |
| **同じサブパッケージ内でモジュール分割**<br>(例 `src/action/__init__.py → src/action/turn_manager.py`) | `from .turn_manager import TurnManager` | ファイル移動に強く短い |
| **トップレベル以外からユーティリティを呼ぶ**<br>(例 `src/npc/ai.py → src.utilities.helpers`) | 絶対：`from src.utilities.helpers import roll_dice` | 長くても検索しやすい |

> **ポイント**  
> - 「`src` 以降」を **プロジェクトの公開 API** と捉え、  
>   そこをまたぐときは絶対 import に固定する。  
> - “サブパッケージの内部実装” は相対でも OK。  
> - `python -m src.xxx` で実行する（editable‐install 済みなら直接でも可）前提なら、  
>   絶対 / 相対が混在していてもエラーにはならない。

---

## 3. いま残っている相対 import をどうする？
1. **頻繁にいじるファイル**だけ先に統一する  
   - 例：`src/action/__init__.py` で外部パッケージを参照しているなら絶対 import へ。  
2. **検索 (`grep` / VS Code 全文検索)** で `from ..` が 2 段以上出てくる場所を洗い出し、順次置き換える。  
3. **新規ファイルを書くときのガイドライン** を `CONTRIBUTING.md` に一行書いておくと混乱しない。  

---

## 4. 変換しても動かないときのチェックリスト
| 症状 | よくある原因 | 対応 |
|------|-------------|-------|
| `ModuleNotFoundError: No module named 'src'` | - venv に editable‐install していない<br>- `PYTHONPATH` にルートが無い | `pip install -e .` を 1 度走らせる |
| `attempted relative import with no known parent package` | スクリプトを直接 `python path/to/foo.py` で叩いている | ルートで `python -m src.foo` または `main.py` 経由で起動 |
| `ImportError: cannot import name ...` | サイクル import（依存が循環） | 設計を見直す or import 文を関数内に移動 |

---

### ✅ まとめ
- **「絶対 = 外から見える API」「相対 = サブパッケージ内部」** の 2 段ルールに揃えておけば、読み手もツールも迷いません。  
- 既存コードは急いで全部直さなくても OK。触るファイルから順に揃えていけば十分です。