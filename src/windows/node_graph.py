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
        self._setup_graph()
        self._setup_layout()

    # --------------------------------------------------------------
    # 内部セットアップ
    # --------------------------------------------------------------
    def _setup_graph(self) -> None:
        """
        内部で保持する NodeGraph の初期設定とノード登録を行う。

        ここでこのツール用のノードクラスをまとめて登録する。
        """
        # ここでツール内のカスタムノードを登録
        from .node.test_node import TestNode

        self._graph.register_node(TestNode)

        # 必要であれば、今後ここで他のノードも register_node していく想定。

    def _setup_layout(self) -> None:
        """
        NodeGraph.widget をこの QWidget のレイアウトに追加する。
        """
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self._graph.widget)

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
