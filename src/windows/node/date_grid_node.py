from __future__ import annotations

"""
DateGridNode

- 他ノードを「自ノードの矩形領域内」にスナップさせて保持するコンテナノード。
- つねに最背面に描画される（他ノードの背景として振る舞う）。
- 他ノードがドラッグ＆ドロップで移動され、位置確定したときに
  自ノード領域と重なっていれば自動で内部にスナップし、
  子ノードの配置に合わせて自ノードのサイズ（高さ中心）を伸縮させる。
"""

from typing import Iterable, List, Optional

from PySide2.QtCore import QRectF
from NodeGraphQt import BaseNode, NodeGraph

from .base_nodes import ToolBaseNode


class DateGridNode(ToolBaseNode):
    """
    日付（または任意のグループ）単位で他ノードをまとめるための背景ノード。

    - ToolBaseNode を継承しているが、ポート自体は使わなくてもよい想定
    - 自身は「背景」として常に最背面に描画
    - graph 上で他ノードが動かされたときに、自領域と重なっていれば
      自動的に内部へスナップして縦に整列させる
    """

    __identifier__ = ToolBaseNode.__identifier__
    NODE_NAME = "Date"

    # ------------------------------------------------------------------ #
    #  初期化
    # ------------------------------------------------------------------ #
    def __init__(self) -> None:
        super(DateGridNode, self).__init__()

        # デフォルト名
        self.set_name("Date")

        # 背景っぽく見えるように幅・高さをやや大きめに
        self.set_property("width", 260.0)
        self.set_property("height", 180.0)

        # スナップ関連プロパティ
        # children: 内部にスナップしているノードの id リスト
        self.create_property("children", [])  # type: ignore[func-returns-value]
        self.create_property("padding_x", 20.0)
        self.create_property("padding_y", 30.0)
        self.create_property("spacing_y", 10.0)

        # DateGrid は背景なので常に最背面へ
        # （他ノードよりかなり小さい Z 値にしておく）
        if self.view is not None:
            self.view.setZValue(-10000.0)

    # ------------------------------------------------------------------ #
    #  ヘルパー
    # ------------------------------------------------------------------ #
    @staticmethod
    def _node_scene_rect(node: BaseNode) -> Optional[QRectF]:
        """
        ノードの「シーン座標系での矩形」を取得する。
        """
        item = getattr(node, "view", None)
        if item is None:
            return None
        # QGraphicsItem.sceneBoundingRect() をそのまま利用
        return item.sceneBoundingRect()

    def _children_ids(self) -> List[str]:
        """
        プロパティ上の children を常に list[str] として返す。
        """
        value = self.get_property("children")
        if isinstance(value, list):
            return list(value)
        return []

    # ------------------------------------------------------------------ #
    #  ノード移動時のスナップ処理（ToolBaseNode から呼ばれる）
    # ------------------------------------------------------------------ #
    @classmethod
    def on_node_moved(cls, graph: NodeGraph, moved_node: BaseNode) -> None:
        """
        他ノードが移動したときに、全ての DateGridNode に対して
        「そのノードを受け入れるかどうか」を判定させるクラスメソッド。

        Parameters
        ----------
        graph:
            NodeGraph インスタンス。
        moved_node:
            位置が更新されたノード。
        """
        if graph is None or moved_node is None:
            return

        # DateGrid 自身が動いたときは、ここでは何もしない
        if isinstance(moved_node, cls):
            return

        for node in graph.all_nodes():
            if isinstance(node, cls):
                node._update_membership(moved_node)

    # ------------------------------------------------------------------ #
    #  個々の DateGrid 側での membership 判定
    # ------------------------------------------------------------------ #
    def _update_membership(self, moved_node: BaseNode) -> None:
        """
        指定された moved_node を「自分の子として扱うか」を判定し、
        必要であれば children リストを更新して全子ノードを再レイアウトする。
        """
        graph = self.graph
        if graph is None:
            return

        my_rect = self._node_scene_rect(self)
        other_rect = self._node_scene_rect(moved_node)
        if my_rect is None or other_rect is None:
            return

        children_ids = self._children_ids()
        is_child = moved_node.id in children_ids

        intersects = my_rect.intersects(other_rect)

        updated = False

        if intersects and not is_child:
            # 新しく自分の子として受け入れる
            children_ids.append(moved_node.id)
            updated = True
        elif (not intersects) and is_child:
            # 領域から外れたので子リストから除外
            children_ids.remove(moved_node.id)
            updated = True

        # 交差状態に変化がなければ何もしない
        if not updated:
            return

        # 実際に存在するノードだけに絞る
        child_nodes: List[BaseNode] = []
        for nid in children_ids:
            node = graph.get_node_by_id(nid)
            if node is None or node is self:
                continue
            child_nodes.append(node)

        # 子ノード id を再保存
        self.set_property("children", [n.id for n in child_nodes])

        # 子ノードがいなくなった場合は高さだけ最小値にして終了
        if not child_nodes:
            self._shrink_to_min_height()
            return

        # 子ノードを縦に並べて、自分のサイズを合わせる
        self._layout_children(child_nodes)

    # ------------------------------------------------------------------ #
    #  レイアウト処理
    # ------------------------------------------------------------------ #
    def _layout_children(self, children: Iterable[BaseNode]) -> None:
        """
        children 内のノードを自分の内部に縦に整列させ、
        その結果に合わせて自ノードの幅・高さを更新する。
        """
        graph = self.graph
        if graph is None:
            return

        rect = self._node_scene_rect(self)
        if rect is None:
            return

        padding_x = float(self.get_property("padding_x") or 0.0)
        padding_y = float(self.get_property("padding_y") or 0.0)
        spacing_y = float(self.get_property("spacing_y") or 0.0)

        # 子ノード配置開始位置（自分の左上からのオフセット）
        x = rect.left() + padding_x
        y = rect.top() + padding_y

        max_right = rect.right()
        max_bottom = rect.bottom()

        # 再配置中は ToolBaseNode.set_pos からの再帰を防ぐ
        children_list = list(children)
        for n in children_list:
            setattr(n, "_kdm_snapping", True)

        try:
            for node in children_list:
                # 子ノードを順番に縦に並べる
                node.set_pos(x, y)

                child_rect = self._node_scene_rect(node)
                if child_rect is None:
                    continue

                max_right = max(max_right, child_rect.right() + padding_x)
                y = child_rect.bottom() + spacing_y
                max_bottom = max(max_bottom, y)
        finally:
            for n in children_list:
                setattr(n, "_kdm_snapping", False)

        # 自分自身のサイズを、子ノードの末端 + パディング に合わせて更新
        new_width = max_right - rect.left()
        new_height = max_bottom - rect.top() + padding_y

        # NodeGraphQt では width / height プロパティを書き換えることで
        # ノードのサイズを制御できる 
        self.set_property("width", float(new_width))
        self.set_property("height", float(new_height))

    def _shrink_to_min_height(self) -> None:
        """
        子ノードがなくなったときに最小高さまで戻す。
        """
        padding_y = float(self.get_property("padding_y") or 0.0)
        min_height = max(120.0, 2 * padding_y + 40.0)
        self.set_property("height", float(min_height))
