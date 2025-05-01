### 📝 「editable install（編集可能インストール）」とは？

> **pip install -e .** と打つと入る、  
> “ソースをそのまま **site-packages** にリンクして使う” 開発用インストール方式です。  

---

## 1. 仕組み

| 通常の `pip install .` | `pip install -e .`（editable） |
|-----------------------|--------------------------------|
| パッケージをビルド → wheel を site-packages に**コピー** | site-packages に **`.egg-link` ファイル** だけ置き、<br>中身は *作業ディレクトリへのパス* |
| コピーされたコードは **読み取り専用**（編集しても反映されない） | エディタで src を編集すると **即 import に反映** |
| 単体実行は `python -m パッケージ名` が基本 | `python your_package/…` でも動く（sys.path 上にいるため） |

内部的には `easy-install.pth` に  
```
E:\hybrid_gm_ai
```
のような行が追加され、Python が検索パスとしてあなたのプロジェクトルートを常に見る、というだけの仕組みです。

---

## 2. どうやって使う？

### 🔸 最小 pyproject.toml 例（PEP 621）

```toml
[project]
name = "hybrid_gm_ai"     # パッケージ名
version = "0.1.0"
requires-python = ">=3.10"

[build-system]
requires = ["setuptools>=61.0"]
build-backend = "setuptools.build_meta"
```

ルートで:

```bash
python -m pip install --upgrade pip             # 一応最新版に
pip install -e .                                # ← これが editable install
```

> *`setup.py` 時代* でも同じく `pip install -e .` で動きます。

---

## 3. 利点と注意点

### ✅ 利点
1. **ホットリロード感覚**：コードを直して保存 ▶︎ 次の import で即反映  
2. **import パス問題が消える**：どこから実行しても `import src.simulation` が解決  
3. **CI・仮想環境で同一手順**：開発もテストも `pip install -e .[dev]` だけ

### ⚠️ 注意
| 問題 | 対策 |
|------|------|
| **本番環境**では普通 wheel を使うので `-e` を入れない | デプロイ用は `pip install .` かビルド済み wheel |
| `pip uninstall <name>` しないと egg-link が残る | 仮想環境を作って作業すると安全 |
| `name` が他ライブラリと衝突しないように | PyPI に公開予定ならユニークな名前を |

---

## 4. 実行例

```bash
(venv) E:\hybrid_gm_ai> pip install -e .
Obtaining file:///E:/hybrid_gm_ai
...
Successfully installed hybrid-gm-ai-0.1.0
```

以後どこでも:

```bash
python - <<'PY'
from src.simulation import main
print("動く！")
PY
```

---

### 🏁 まとめ

- **editable install = “作業フォルダをそのまま Python パッケージとして認識させる” 開発モード**  
- `pip install -e .` 一発で、**絶対 import** が安定しテスト起動も楽になる  
- 本番環境とは切り分け、仮想環境 & アンインストール忘れに注意

これで「`python src\simulation.py` を直接叩きたい」問題もパス設定を意識せず解決できます！