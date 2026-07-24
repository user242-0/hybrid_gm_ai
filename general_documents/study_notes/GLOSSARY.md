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