from __future__ import annotations

"""
DateGridNode

- 他ノードを「背景グリッド」上に縦方向へスナップ配置するノード。
- DateGridNode 自身は常に他ノードの背面に描画される（Z 値を低く設定）。
- スナップされたノードの情報はプロパティとして保持し、
  Inspector の note から一覧を確認できる。
"""

from typing import List, Dict, Optional

from .base_nodes import ToolBaseNode  # 共通ベースノード :contentReference[oaicite:3]{index=3}


class DateGridNode(ToolBaseNode):
    """
    タイムライン用の「背景グリッド」ノード。

    - 常にほかのノードより背面に描画される
    - 横幅は他ノードと同一幅で固定（最初にスナップされたノードを基準）
    - 縦方向に自由に伸縮できる
    - 上辺付近の「スナップエリア」にドラッグして近づけたノードを
      自動で縦方向に整列させ、内部でその情報を保持する
    - DateGridNode 同士の入れ子は許可しない
    """

    __identifier__ = ToolBaseNode.__identifier__
    NODE_NAME = "Date Grid"

    # スナップエリアの高さ（ピクセル）
    SNAP_AREA_HEIGHT = 40
    # グリッドの最小高さ
    MIN_HEIGHT = 120
    # ノード同士の縦間隔
    V_SPACING = 10
    # 左側マージン
    H_MARGIN = 10

    def __init__(self) -> None:
        super().__init__()

        # 背景ノードっぽい色
        self.set_color(60, 60, 80)

        # 初期サイズ（他ノードと同じくらいの幅）
        self.set_property("width", 220.0)
        self.set_property("height", float(self.MIN_HEIGHT))

        # 常に背面に描画
        if self.view is not None:
            try:
                self.view.setZValue(-1000)
            except Exception:
                pass

        # スナップされたノード ID のリスト（シリアライズ対象・UI は出さない）
        self.create_property(
            name="snap_nodes",
            value=[],
            widget_type=None,
            widget_tooltip="Date Grid にスナップされているノードの ID 一覧。",
            tab="Date Grid",
        )

        # インスペクタ初期文言（note は Inspector で表示される）:contentReference[oaicite:4]{index=4}
        self.set_property("note", "スナップされたノード: なし")

        # ツールチップでスナップエリアを説明
        try:
            self.set_tooltip("上部 40px がスナップエリアです。近づけると自動で整列します。")
        except Exception:
            pass

    # ------------------------------------------------------------------
    #  Graph 側から呼ばれるクラスメソッド（ドラッグ時の自動スナップ）
    # ------------------------------------------------------------------
    @classmethod
    def handle_node_moved(cls, graph, moved_node) -> None:
        """
        NodeGraph.property_changed("pos") から呼ばれる想定の処理。

        - moved_node が DateGridNode 自身 … ぶら下がっているノードを再レイアウト
        - moved_node が ToolBaseNode     … DateGrid へのスナップ / 解除を判定
        """
        if graph is None or moved_node is None:
            return

        # すべての DateGridNode を取得
        date_nodes: List[DateGridNode] = [
            n for n in graph.all_nodes()
            if isinstance(n, DateGridNode)
        ]
        if not date_nodes:
            return

        # DateGridNode 自身が動いた場合 → 自分の子だけ再レイアウト
        if isinstance(moved_node, DateGridNode):
            moved_node._layout_snapped_nodes()
            return

        # それ以外で、ToolBaseNode 以外はスナップ対象外
        if not isinstance(moved_node, ToolBaseNode):
            return
        # DateGridNode は入れ子禁止
        if isinstance(moved_node, DateGridNode):
            return

        moved_id = moved_node.id

        # もともとどの DateGrid に属していたか
        current_parent: Optional[DateGridNode] = None
        for dn in date_nodes:
            if moved_id in dn._get_snap_ids():
                current_parent = dn
                break

        # 現在位置でどの DateGrid のスナップエリア内にいるか
        target_parent: Optional[DateGridNode] = None
        for dn in date_nodes:
            if dn._is_in_snap_area(moved_node):
                target_parent = dn
                break

        # どこにも入っていない → 以前の親から外すだけ
        if target_parent is None:
            if current_parent is not None:
                ids = current_parent._get_snap_ids()
                if moved_id in ids:
                    ids.remove(moved_id)
                    current_parent._set_snap_ids(ids)
                    current_parent._layout_snapped_nodes()
            return

        # 別の DateGrid に移動した場合：元から削除して新しい DateGrid に追加
        if current_parent is not None and current_parent is not target_parent:
            ids = current_parent._get_snap_ids()
            if moved_id in ids:
                ids.remove(moved_id)
                current_parent._set_snap_ids(ids)
                current_parent._layout_snapped_nodes()

        # target_parent へ登録
        ids = target_parent._get_snap_ids()
        if moved_id not in ids:
            ids.append(moved_id)
            target_parent._set_snap_ids(ids)
        target_parent._layout_snapped_nodes()

    # ------------------------------------------------------------------
    #  内部ユーティリティ
    # ------------------------------------------------------------------
    def _get_size(self) -> (float, float):
        w = self.get_property("width")
        h = self.get_property("height")
        if not isinstance(w, (int, float)):
            w = 220.0
        if not isinstance(h, (int, float)):
            h = float(self.MIN_HEIGHT)
        return float(w), float(h)

    def _grid_rect(self) -> Dict[str, float]:
        """
        現在の DateGrid の矩形情報を返す。
        """
        x, y = self.pos()
        w, h = self._get_size()
        return {"x": float(x), "y": float(y), "w": w, "h": h}

    def _is_in_snap_area(self, node: ToolBaseNode) -> bool:
        """
        ノードの中心が DateGrid のスナップエリア付近にあるか判定。

        - X 方向: DateGrid の幅内
        - Y 方向: DateGrid 上端から SNAP_AREA_HEIGHT 以内
        """
        rect = self._grid_rect()
        nx, ny = node.pos()
        # ヘッダ高さをざっくり 30px として中心を推定
        cx = float(nx) + rect["w"] * 0.5
        cy = float(ny) + 30.0

        in_x = rect["x"] <= cx <= rect["x"] + rect["w"]
        in_y = rect["y"] <= cy <= rect["y"] + self.SNAP_AREA_HEIGHT
        return in_x and in_y

    def _get_snap_ids(self) -> List[str]:
        ids = self.get_property("snap_nodes") or []
        if not isinstance(ids, list):
            return []
        return [str(i) for i in ids]

    def _set_snap_ids(self, ids: List[str]) -> None:
        self.set_property("snap_nodes", list(ids))
        self._update_note_from_snap_ids()

    def _update_note_from_snap_ids(self) -> None:
        """
        snap_nodes の内容から note テキストを組み立て、インスペクタに表示する。
        """
        graph = self.graph
        ids = self._get_snap_ids()
        if graph is None or not ids:
            self.set_property("note", "スナップされたノード: なし")
            return

        lines: List[str] = ["スナップされたノード:"]
        for idx, nid in enumerate(ids, start=1):
            node = graph.get_node_by_id(nid)
            if node is None:
                continue
            lines.append(f"{idx}: {node.name()} (id={nid})")

        self.set_property("note", "\n".join(lines))

    # ------------------------------------------------------------------
    #  スナップ済みノードのレイアウト処理
    # ------------------------------------------------------------------
    def _layout_snapped_nodes(self) -> None:
        """
        snap_nodes に登録されているノードを

        - 左端位置を揃え
        - 縦方向にきれいに並べ
        - その結果に合わせて DateGrid 自身の高さを自動調整し
        - 横幅は「最初にスナップされたノードの幅」で固定する

        というレイアウトを行う。
        """
        graph = self.graph
        if graph is None:
            return

        ids = self._get_snap_ids()
        if not ids:
            # 何もないときは高さだけ最低値に戻す
            w, _ = self._get_size()
            self.set_property("width", w)
            self.set_property("height", float(self.MIN_HEIGHT))
            self._update_note_from_snap_ids()
            return

        # 実在するノードだけ抽出（削除されたノードをクリーンアップ）
        nodes: List[ToolBaseNode] = []
        for nid in ids:
            node = graph.get_node_by_id(nid)
            if node is None:
                continue
            if isinstance(node, DateGridNode):
                # 入れ子禁止
                continue
            if not isinstance(node, ToolBaseNode):
                continue
            nodes.append(node)

        if not nodes:
            self._set_snap_ids([])
            return

        # Y 位置でソートして縦並び順を決定
        nodes.sort(key=lambda n: n.pos()[1])

        # 基準幅：最初のノードの現在 width（なければ 220）
        first_w = nodes[0].get_property("width")
        if not isinstance(first_w, (int, float)):
            first_w = 220.0
        base_width = float(first_w)

        # DateGrid 自身の幅もそれに合わせる
        self.set_property("width", base_width)

        rect = self._grid_rect()
        x = rect["x"]
        y = rect["y"]

        current_y = y + self.SNAP_AREA_HEIGHT + self.V_SPACING
        max_bottom = current_y

        # 実際にノードを縦に並べる
        for node in nodes:
            # ノードの高さ（view.height があれば利用）
            nh = getattr(node.view, "height", 60.0)
            nh = float(nh)

            # 横幅を揃える
            try:
                node.set_property("width", base_width - self.H_MARGIN * 2.0)
            except Exception:
                pass

            target_x = x + self.H_MARGIN
            node.set_pos(target_x, current_y)

            current_y += nh + self.V_SPACING
            max_bottom = max(max_bottom, current_y)

        # DateGrid の高さを子ノードの終端まで伸ばす
        new_height = max(float(self.MIN_HEIGHT), max_bottom - y + self.V_SPACING)
        self.set_property("height", new_height)

        # note 更新
        self._update_note_from_snap_ids()
