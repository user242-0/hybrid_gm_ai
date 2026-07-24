決定：
intentをOperationより先に置く

理由：
目的と実行手段を分離し、同じintentから複数のOperation候補を選べるようにする

代替案：
intentとactionを直接結合する

採用しなかった理由：
将来ROや複数候補選択を追加したとき拡張しにくい