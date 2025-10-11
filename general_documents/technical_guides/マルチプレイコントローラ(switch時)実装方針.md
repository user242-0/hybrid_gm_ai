動くようになってよかったです！
ご相談の「**マルチプレイ（人間が複数）**」に向けた実装方針を、**ガッツリ書き換えず段階的に**進める形でまとめます。結論だけ先に：

> **結論（要点）**
>
> * バトン＝**“世界に1本のアクティブ”**ではなく、**“コントローラIDごとの制御トークン”**として扱う。
> * `active_char` を **コントローラID→キャラ**のマップに一般化（例：`active_by_controller["P1"] = Hero`）。
> * 切替は **「どのコントローラのバトンを誰に渡すか」** を明示して処理する。
> * 既存の `is_npc` / スケジューラ（AI tick）ロジックはそのまま活かし、**人間が持つトークンが外れたキャラだけ AI を再始動**させる。
> * 既存の単一プレイ互換のために `active_char` は **P1 の別名**として暫定維持。

---

## 1) 現状の整理（どこが単一プレイ前提か）

* 初期状態は `game_state["active_char"] = hero` と**単一のアクティブ**で保持しています。
* 切替は `switch_control(actor, game_state, target_name)` が担い、**旧アクティブをNPC化 → ターゲットをプレイヤー化**し、`game_state["active_char"]` を置き換え、**戻り値に「旧アクティブ（NPC化した側）」**を返しています（ここが “0.01秒でAI再開” の起点）。
* `rc_tick` は **結果が NPC なら 0.01s 後に再スケジュール**、その後 **AIキャラ自身も0.2sで再登録**という2段で回しています。

> つまり今は「**世界に1本**のバトン（`active_char`）を**奪い合う**」前提です。

---

## 2) マルチプレイ化の肝：**バトン＝コントローラIDの制御トークン**

バトンを**色分け**＝**コントローラID**で持たせます（P1=赤, P2=青…など）。世界にバトンが複数本あるイメージ。

### 推奨データ構造（最小限）

```python
game_state["controllers"] = {
    "P1": {"type": "human", "color": "red"},
    "P2": {"type": "human", "color": "blue"},
    # AIコントローラを分けたいなら "AI1": {"type": "ai"} など
}

# 各コントローラの“今”の担当（=色つきバトンの持ち主）
game_state["active_by_controller"] = {
    "P1": hero,
    "P2": luna,
    # ...
}

# 逆引き（誰が人間コントローラに掴まれているか）
game_state["control_map"] = {
    hero.name: "P1",
    luna.name: "P2",
    # NPCは None（または存在しない）で表現
}
```

* **`is_npc` の扱い**：
  「**どの人間コントローラにも持たれていなければ `True`**」という**派生属性**として扱うのがきれいです（移行期間中は、切替時に `is_npc` を今まで通り更新して互換維持でもOK）。現状の `rc_tick` は `is_npc` を見て AI を動かすので、そのまま活きます。

* **`is_active` の扱い**：
  いまは「世界に1人のアクティブ」を想定して `bool` 運用されていますが、**“誰かのコントローラに掴まれている”**の意味で **複数True** になってOK。`requirements_checker` の `has_rc_in_party` は「誰か**非アクティブ**（=今掴まれていない）なRCが居る？」の判定に使っており、このまま複数プレイで自然に機能します。

---

## 3) コアAPIの形（擬似コードレベル）

### 3.1 `switch_control` を「**どのコントローラのバトンを渡すか**」で明示

```python
def switch_control(actor, gs, target_name, controller_id=None, *, mode="assign"):
    """
    controller_id: どのコントローラの色バトンを移すか
      None → actor を現在握っている controller を自動推定（単一プレイ互換）
    mode:
      "assign" → controller_id の担当を target に一方的に付け替え
      "swap"   → actor と target が別々の controller を持っていれば交換
      "steal"  → NPCが他者の controller を奪う（ポリシーで許可時のみ）
    戻り値: 旧担当キャラ（= NPC化した側）※互換維持
    """
    with gs["lock"]:
        # 1) controller_id を確定
        if controller_id is None:
            controller_id = infer_controller_of(actor, gs)  # 既存互換（P1 相当）

        prev = gs["active_by_controller"].get(controller_id)   # その色の旧担当
        target = gs["party"][target_name]

        # 2) 付け替え（または交換）
        if mode == "swap" and has_other_controller(target, gs):
            # 例：P1=Hero, P2=Luna → swap で P1=Luna, P2=Hero
            swap_controllers(actor, target, gs)
            partner_for_log = target.name  # 表示的には相手名
            prev_for_ai = actor            # 自分がNPC化した側
        else:
            # assign/steal：controller_id の担当を target に付け替え
            set_controller(prev, None, gs)         # 旧担当を手放す → NPC化
            set_controller(target, controller_id, gs)  # 新担当 → プレイヤー化
            partner_for_log = (prev.name if target is actor else target.name)
            prev_for_ai = prev

        # 3) ログ（色表示すると気持ちいい）
        print(f"[{controller_id}] {actor.name}は操作キャラクターを{partner_for_log} に切り替えた")
        return prev_for_ai
```

* **戻り値を「NPC化した側」**にしておけば、既存の `rc_tick` が**0.01sで旧担当をAI再開**してくれるため、**現在の高速入れ替え特性**を自然に維持します。

### 3.2 `choose_target_for_switch` を「**ターゲットに加えて controller_id も決める**」

単一プレイでは `active_char` を見ていましたが、マルチでは**「どの色バトンを狙うか」**も選ぶ必要があります。

```python
def choose_switch_request(rc_char, gs):
    """
    返り値例: {"controller_id": "P1", "target_name": rc_char.name, "mode": "steal"}
    - セッション14のような“奪取”は: controller_id を選んで target=self
    - 純粋な交代は: controller_id = 自分の担当, target=他キャラ, mode="assign"/"swap"
    """
    if gs.get("allow_ai_to_seize_control"):      # 既存フラグを一般化
        controller_id = pick_human_controller(gs)  # 奪う色を選ぶ
        return {"controller_id": controller_id, "target_name": rc_char.name, "mode": "steal"}
    else:
        # 従来相当：自分が持つ controller で他の候補へ
        controller_id = infer_controller_of(rc_char, gs)  # なければP1想定
        target = pick_other_candidate(rc_char, gs) or rc_char
        return {"controller_id": controller_id, "target_name": target.name, "mode": "assign"}
```

> 既存の `allow_ai_to_seize_control`（セッション14用）を**コントローラ単位の許可**に拡張するなら
> `gs["seize_policy"] = {"P1": True, "P2": False, ...}` のように持たせれば柔軟です。

---

## 4) ログ表記＆UI（色つきバトン前提）

* 現在は `switch_control` 内で `print(f"{actor} は {target} に…")` を出していましたが、**マルチでは “どの色のバトンか” が鍵**なので、
  **`print(f"[{controller_id}] {actor} は {相手} に切り替え")`** のように **コントローラID（色）を必ず添える**のが実運用楽です。
* さらに、**“奪取”**（`target is actor`）と**“交代/交換”**（`target != actor`）で**メッセージを言い分け**ると混乱しません。
  例：

  * 奪取: `[P1] Luna は Hero からバトンを奪取 → Luna がP1担当 / Hero はAIへ`
  * 交代: `[P1] Hero は Luna にバトンを渡した`

---

## 5) 互換性を崩さない段階移行

1. **段階A（互換レイヤー）**

   * `active_by_controller["P1"]` を導入し、**`active_char` をそのエイリアス**として維持。
   * `switch_control(..., controller_id=None)` で、**未指定はP1扱い**にする。
2. **段階B（選択APIの拡張）**

   * AI側は `choose_switch_request` を使い、`controller_id` 付きで指示を返す。
   * 人間の CLI/GUI でも、**自分のコントローラID前提で target を選ぶ**UIに。
3. **段階C（テストの更新）**

   * 単体テストは `get_active("P1")` のように **コントローラIDで参照**するアサーションへ。
4. **段階D（`is_active`の意味整理）**

   * `is_active=True` を「**いずれかの人間コントローラに掴まれている**」に読み替え（複数True許容）。
   * 既存の `has_rc_in_party` ロジックはそのまま活用できます。

---

## 6) スケジューラ（AI tick）はそのままでOK

* これまで通り **「手放した側（NPC化した旧担当）」**を `switch_control` の戻り値にしておけば、`rc_tick` が **0.01sでAI再開** → **0.2sで巡回**の流れを維持できます。ロジック変更は不要。

---

## 7) ポリシーの設計（奪取／交換／占有禁止など）

* `mode="assign" | "swap" | "steal"` の3つを用意すると運用が分かりやすいです。
* `steal` の可否は **グローバル**でも**コントローラ単位**でも設定可能（例：`seize_policy["P1"]=True`）。
* 2つのNPCが同じ色を同時に奪う競合は、**既存の排他ロック**で `switch_control` を囲っているので、そこに乗せれば十分。

---

## 8) ミニサンプル（本当に最小限の差分感）

> 実装はしませんが、つながりだけイメージ

* **ゲーム状態**に `controllers / active_by_controller / control_map` を追加
* **切替**：

  * 旧：`switch_control(actor, gs, target_name)`
  * 新：`switch_control(actor, gs, target_name, controller_id="P1", mode="assign")`
* **AI**：

  * 旧：`target_name = choose_target_for_switch(rc_char, gs)`
  * 新：`req = choose_switch_request(rc_char, gs); switch_control(rc_char, gs, req["target_name"], req["controller_id"], mode=req["mode"])`
* **ログ**：

  * 旧：`{actor} → {target}`
  * 新：`[{controller_id}] {actor} → {partner_for_log}`

---

## 9) この方針が今のコードと噛み合う理由

* 現在の入れ替えの核は **「旧アクティブをNPC化→0.01sでAI再起動」**。この核はそのまま使えます。
* `allow_ai_to_seize_control` の思想も「**どのバトンを奪うか**」に拡張するだけで整合的です。

---

## 10) 参考：関連箇所へのリンク（あなたのリポジトリ内）

* `init_game_state()` が単一 `active_char` と `allow_ai_to_seize_control` をセット。
* `switch_control()` が切替とログ、戻り値で旧アクティブを返す。
* `rc_tick()` が **結果がNPCなら0.01s**、その後 **自分も0.2s** で再登録（入れ替えが高速に発生する要因）。
* `switch_character` のアクション定義や Choice 周りは既存のまま流用可能。

---

## p.s.) Gitのコミットメッセージ（簡潔案）

用途に合わせてどうぞ（どれか1つ）：

1. 日本語・最小

```
git commit -m "switchログを相手名に修正／マルチプレイはコントローラID(バトン)方式で設計"
```

2. 日本語・さらに短く

```
git commit -m "switch: 相手名で表示。マルチプレイ設計＝コントローラID化"
```

3. 英語派

```
git commit -m "switch log shows partner; outline multi-controller (baton) design"
```

---

この方針なら、**今の“セッション14”の気持ちよさ（高速入れ替え）を壊さず**に、**色分けバトン＝コントローラID**へスケールできます。必要になった段階で `controller_id` をパラメータに出していけば、滑らかに移行できます。
