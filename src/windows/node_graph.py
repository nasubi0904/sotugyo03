"""
ノードグラフ UI を提供するモジュール。

NodeGraphQt の NodeGraph インスタンスをラップし、
QMainWindow の central widget として利用できる QWidget を定義する。
"""

from typing import Optional

from PySide2.QtWidgets import QWidget, QVBoxLayout

try:
    # NodeGraphQt がインストールされている前提
    from NodeGraphQt import NodeGraph
except ImportError as exc:  # pragma: no cover - 実行環境依存
    raise ImportError(
        "NodeGraphQt がインポートできません。 "
        "仮想環境や requirements の設定を確認してください。"
    ) from exc


from .node.base_nodes import register_all_tool_nodes
from .node.date_grid_node import DateGridNode


class NodeGraphWidget(QWidget):
    """
    NodeGraphQt の NodeGraph を内包する QWidget。

    - 内部に NodeGraph インスタンスを保持する
    - NodeGraph.widget をレイアウトに追加して表示する
    """

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        """
        NodeGraphWidget のインスタンスを初期化する。

        Parameters
        ----------
        parent:
            親ウィジェット。通常は QMainWindow。
        """
        super().__init__(parent)
        self._graph: NodeGraph = NodeGraph()

        # Node の property 変更（特に pos）の監視
        self._graph.property_changed.connect(self._on_graph_property_changed)

        self._setup_graph()
        self._setup_layout()

    # --------------------------------------------------------------
    # 内部セットアップ
    # --------------------------------------------------------------

    def _setup_graph(self) -> None:
        """
        内部で保持する NodeGraph の初期設定とノード登録を行う。
        """
        # windows.node パッケージ配下の ToolBaseNode サブクラスを自動登録
        register_all_tool_nodes(self._graph)
        # DateGridNode も ToolBaseNode を継承しているため、上記で自動登録される

    def _setup_layout(self) -> None:
        """
        NodeGraph.widget をこの QWidget のレイアウトに追加する。
        """
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self._graph.widget)

    # --------------------------------------------------------------
    # NodeGraph シグナルハンドラ
    # --------------------------------------------------------------

    def _on_graph_property_changed(self, node, prop_name, prop_value):
        """
        NodeGraph.property_changed シグナル用ハンドラ。

        - ノードの位置 (pos) が変化したときだけ DateGridNode に通知し、
          スナップ処理や DateGrid の自動レイアウトを行う。
        """
        if prop_name != "pos":
            return

        # DateGridNode 側にロジックをまとめているので、ここでは流すだけ
        try:
            DateGridNode.handle_node_moved(self._graph, node)
        except Exception as e:
            # デバッグ用に、クラッシュさせずにログだけ出す
            print("[DateGridNode] handle_node_moved error:", e)

    # --------------------------------------------------------------
    # プロパティ
    # --------------------------------------------------------------

    @property
    def graph(self) -> NodeGraph:
        """
        内部で保持している NodeGraph インスタンスを返す。

        Returns
        -------
        NodeGraph
            NodeGraphQt の NodeGraph オブジェクト。
        """
        return self._graph
