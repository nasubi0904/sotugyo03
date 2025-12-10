# windows/node/date_grid_node.py

from __future__ import annotations

from typing import Dict, List

from PySide2.QtCore import QRectF, QPointF

from .base_nodes import ToolBaseNode


class DateGridNode(ToolBaseNode):
    """
    ・常に他ノードの背面に描画される背景ノード
    ・grid_width / grid_height プロパティで自由にスケール
    ・内部のスナップ領域に他ノードを吸着させ、その情報を保持
    """

    __identifier__ = ToolBaseNode.__identifier__
    NODE_NAME = "Date Grid"

    def __init__(self) -> None:
        super().__init__()

        # 表示用
        self.set_property("label", "Date Grid")
        self.set_property("note", "背景グリッドとして使用")

        # QGraphicsItem 側の Z 値を下げて常に背面に
        view = getattr(self, "view", None)
        if view is not None and hasattr(view, "setZValue"):
            view.setZValue(-1000.0)

        # スケール用プロパティ
        self.create_property("grid_width", 800.0)
        self.create_property("grid_height", 300.0)

        # スナップ領域（ノードローカル座標）
        self.create_property(
            "snap_region",
            {
                "x": 100.0,
                "y": 80.0,
                "w": 400.0,
                "h": 150.0,
            },
        )

        # スナップ中ノードの情報保持用
        # [{"uuid": str, "x": float, "y": float}, ...]
        self.create_property("snap_nodes", [])  # type: ignore[arg-type]

        # 初期サイズ反映
        self._apply_size_from_properties()

    # --------------------------------------------------
    # ノードの見た目サイズをプロパティから反映
    # --------------------------------------------------
    def _apply_size_from_properties(self) -> None:
        w = float(self.get_property("grid_width"))
        h = float(self.get_property("grid_height"))

        # BaseNode に set_size はないので、Backdrop と同じパターンで
        # view / model の width / height を直接更新する。
        if self.graph:
            # undo 対応
            self.view.prepareGeometryChange()
            self.graph.begin_undo('date grid size')
            self.set_property("width", w)
            self.set_property("height", h)
            self.graph.end_undo()
            self.view.update()
        else:
            # グラフ未所属の場合のフォールバック
            self.view.width, self.view.height = w, h
            self.model.width, self.model.height = w, h

    # --------------------------------------------------
    # スナップ枠
    # --------------------------------------------------
    def _get_snap_rect(self) -> QRectF:
        r: Dict[str, float] = self.get_property("snap_region")
        return QRectF(r["x"], r["y"], r["w"], r["h"])

    # --------------------------------------------------
    # 指定ノードがスナップ領域内かどうか
    # --------------------------------------------------
    def _is_in_snap_area(self, target_node: ToolBaseNode) -> bool:
        # 自ノード左上（ワールド座標）
        my_pos = QPointF(*self.pos())
        snap_rect = self._get_snap_rect()

        # 対象ノードの中心座標（ワールド）
        tx, ty = target_node.pos()

        # サイズは view.width / height を利用
        tw = getattr(target_node.view, "width", 0.0)
        th = getattr(target_node.view, "height", 0.0)
        center = QPointF(tx + tw * 0.5, ty + th * 0.5)

        # 自ノードローカル座標へ変換
        local_center = QPointF(
            center.x() - my_pos.x(),
            center.y() - my_pos.y(),
        )

        return snap_rect.contains(local_center)

    # --------------------------------------------------
    # 実際のスナップ処理
    # --------------------------------------------------
    def _snap_node(self, target_node: ToolBaseNode) -> None:
        my_pos = QPointF(*self.pos())
        rect = self._get_snap_rect()

        # スナップ先（枠の中心：ワールド座標）
        snap_x = my_pos.x() + rect.x() + rect.width() * 0.5
        snap_y = my_pos.y() + rect.y() + rect.height() * 0.5

        tw = getattr(target_node.view, "width", 0.0)
        th = getattr(target_node.view, "height", 0.0)

        target_node.set_pos(snap_x - tw * 0.5, snap_y - th * 0.5)

        # 情報をプロパティに記録
        snap_list: List[dict] = self.get_property("snap_nodes") or []
        # 同じノードの古い情報は削除
        snap_list = [s for s in snap_list if s.get("uuid") != target_node.id]
        snap_list.append(
            {
                "uuid": target_node.id,
                "x": target_node.pos()[0],
                "y": target_node.pos()[1],
            }
        )
        self.set_property("snap_nodes", snap_list)

    # --------------------------------------------------
    # プロパティ変更時（サイズ変更など）
    # --------------------------------------------------
    def on_property_changed(self, name, value) -> None:
        super().on_property_changed(name, value)

        if name in ("grid_width", "grid_height"):
            self._apply_size_from_properties()

    # --------------------------------------------------
    # 他ノード移動時に NodeGraph 側から呼び出してもらう用フック
    # --------------------------------------------------
    def on_other_node_moved(self, node: ToolBaseNode) -> None:
        """
        NodeGraph 側でノード移動イベントをフックできるようになったら、
        そこからこのメソッドを呼ぶ想定のフック。

        ここでは「スナップ領域内に入ったら吸着する」だけを担当。
        """
        if self._is_in_snap_area(node):
            self._snap_node(node)
