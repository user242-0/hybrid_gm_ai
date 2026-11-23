project_pending

何を示す：
投影元はあるが、対応する投影先がまだ存在しない
project_pending_~~は~~の投影元はあるが、投影先として~~が存在しないかを調べる。
投影元はあるのに投影先~~が何もない場合、投影する。
投影元があり、投影先~~もある場合、処理をskip

いつ生成される：
hud_callbackがセーブデータをロードして、ゲームコンテクストのdirector_worldをゲームコンテクスト.gsの"director_world","world"
に保存した直後。つまり、ロード直後。

誰が書く：
project_pending_……
_rc_memory：rc_memory.py

_rc_beliefs：rc_beliefs.py

誰が読む：
HUDでl,Lを押す、つまりロードすると、DirectorHUDが実行。


いつ解除される：
project_pending_……
_rc_memory："operation_transition_history"の各 transition_eventからメモリーを組み立てて、director_worldの所持するアクターメモリと一致するメモリがあるかないかを調べ、ない場合のみrecord_actor_memoryでメモリを記録する。"operation_transition_history"を走査し終わったら終了。

_rc_beliefs："(director_)world"からactor_memoriesを読み込み、各メモリからbeliefを組み立てる。そこにdirector_worldの所持するアクターbeliefと一致するbeliefがあるかないかを調べ、ない場合(source_memory_idsが完全一致しない場合も)のみ、update_actor_beliefでbeliefを更新する。"actor_memories"を走査し終わったら終了。


存在理由：
開発途中など、セーブデータに投影元があるが、投影先がない、という状況が発生しうる（メモリやビリーフがあるか分からない）


間違って残ると何が起きる：
セーブデータから、投影先が拾える可能性を閉じてしまう。
将来Operation transitionが増えても、Memory projectorに対応ruleがなければ、
Operation進行
eventあり
対応Memoryなし
という状況はあり得る。
その時、これらで正しく走査すれば、復元することができる。
---------------------------------------------------
GameCommandService

何を示す：
 1回のゲームCommandを最後まで通すApplication Service
GCSは意味の所有者ではなく、Application Flowの所有者。ゲームCommandの管制塔。

各domain/application処理を正しい順序で呼び、最終結果まで運ぶ。
「ゲームCommand全体の管制塔」で合っています。
ただし、
管制塔だからといって、自分で滑走路を書き換えたり飛行機を操縦したりはしない。


1. Owner
GCS自身はゲーム正本を所有しない。正本は各domainにあり、GCSはそれらを統括する。

2. Writer
GCS自身がworldを直接書かず、ActionPipeline、OperationRuntime、MemoryProjection、BeliefProjectionなど正規writerを呼ぶ。

3. Coordinator
GCSが1 GameCommandの処理順を所有し、各stageのresultを契機に次stageへ進める。

4. Observer
HCPがGameCommandから各stageのresultとcommit状況を観察し、「どこまで変更済みか」を人間へ示す。

GCSは
× UIを知らない
× HUDを更新しない
× Operation ruleを知らない
× Memoryの意味を知らない
× Belief ruleを知らない
× authoritative worldを直接編集しない

○ 各stageの順序を知る
○ 各stageのresultを知る
○ 次stageへ進めるか判断する
○ 最終resultをまとめる

GameCommandService

意味
1回のGameCommandをAction→Operation→Memory→Belief→fresh Contextまで通すApplication Service。

いつ生成される
application起動時にcomposition rootで構築され、原則application lifetime中存在する。

誰が構築する
当面はsimulation.py等のcomposition root候補。将来は専用bootstrap層でもよい。

誰が呼ぶ
Python HUD／CLI等のAdapter。将来Unity／Mobile Adapter。RC_AIは現在直接呼ばない。

何を書く
authoritative worldを直接書かない。各domain writerを順番に呼ぶ。必要ならGameCommandResultという一時的な実行結果を構築する。

いつ解除される
GCS本体はapplication終了時。Command単位の一時stateはexecute()完了時に終了する。

存在理由
入力元とゲーム処理の実行順を分離し、すべてのCommandを同じApplication Flowへ通すため。

誤ってstateを保持すると
stale ActionOutcome、transition二重処理、actor混線、Memory／Belief重複などが起こり得る。