✅ ローカルからGitHubへ更新する手順（基本3ステップ）
ローカルの変更をGitHubにアップロードするには、次の3つのコマンドを使います：

🧱 ① git add
変更したファイルを「ステージ（準備）」に追加：


git add ファイル名

例：
git add main.py

すべての変更をまとめて追加したい場合：

git add .

🧾 ② git commit
ステージされた変更にコメント（メッセージ）を添えて記録します：

git commit -m "作業内容の説明（例：初期のAIプロンプト作成）"

🚀 ③ git push
コミットした変更をGitHubにアップロード：

git push

これでGitHub上のレポジトリが最新になります！

🔄 GitHubからローカルに更新を反映したいとき（pull）
もし他のPCや後日GitHubで更新した内容を、ローカルに反映したいときは：

git pull
ただし、基本的にあなた1人で作業する場合は pull を使う機会は少ないです。

💡 よくある開発フロー（例）
# 作業前
git pull  ← 念のため最新にしておく

# 作業開始
# コードを書く・ファイルを編集

# 作業後
git add .
git commit -m "カード生成ロジックの初版を追加"
git push
🔒 補足：コミット内容は自由だけど丁寧に
コミットメッセージはあなた自身のログでもあります。

おすすめスタイル：

"Add basic card generator"

"Fix bug in PDF output"

"Update requirements.txt"

"Refactor prompt generation logic"

✅ まとめ
操作	        コマンド	        意味
ファイルを追加	git add .	        ステージに登録
内容を記録	git commit -m "説明"	変更を記録
GitHubに反映	git push      　　　アップロード
GitHubから取得	git pull        	同期（必要な場合）

これでもう立派なGitユーザーです！
もしブランチ運用・タグ付け・差分確認（git status, git diff）なども知りたければ、いつでも聞いてくださいね！