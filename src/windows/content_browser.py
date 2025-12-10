"""
コンテンツブラウザ Dock を定義するモジュール。

NodeGraphQt の NodesTreeWidget を用いて、登録済みノード一覧をツリー表示し、
ドラッグ＆ドロップでノードグラフ上にノードを生成できるようにする。

選択された項目の情報はシグナル経由で外部（インスペクタなど）へ通知する。
"""

from typing import Optional

from PySide2.QtCore import Qt, Signal
from PySide2.QtWidgets import QDockWidget, QWidget, QVBoxLayout, QTreeWidgetItem

from NodeGraphQt import NodeGraph, NodesTreeWidget


class ContentBrowserDockWidget(QDockWidget):
    """
    ノードタイプ一覧を表示するコンテンツブラウザ DockWidget。

    内部で NodeGraphQt.NodesTreeWidget を利用し、
    ユーザーはツリー項目をドラッグ＆ドロップしてノードを作成できる。

    また、選択中の項目が変化したときに selection_changed シグナルを発行し、
    インスペクタなどへ「どの項目が選択されたか」を伝える。
    """

    # content_id, display_label を送る
    selection_changed = Signal(str, str)

    def __init__(
        self,
        graph: NodeGraph,
        parent: Optional[QWidget] = None,
    ) -> None:
        """
        ContentBrowserDockWidget のインスタンスを初期化する。

        Parameters
        ----------
        graph : NodeGraphQt.NodeGraph
            NodesTreeWidget に関連付ける NodeGraph インスタンス。
        parent : QWidget, optional
            親ウィジェット。
        """
        super().__init__("Content Browser", parent)

        self._graph = graph

        container = QWidget(self)
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)

        self._nodes_tree = NodesTreeWidget(parent=container, node_graph=self._graph)
        layout.addWidget(self._nodes_tree)

        container.setLayout(layout)
        self.setWidget(container)

        # ツリーの選択変更をフック
        self._nodes_tree.itemSelectionChanged.connect(
            self._on_tree_selection_changed
        )

        self._setup_dock_behavior()

    # ------------------------------------------------------------------
    # 内部処理
    # ------------------------------------------------------------------
    def _on_tree_selection_changed(self) -> None:
        """
        ツリー上の選択が変更されたときに呼び出されるスロット。

        現在の項目から ID とラベルを取得し、selection_changed シグナルで通知する。
        """
        item: Optional[QTreeWidgetItem] = self._nodes_tree.currentItem()
        if item is None:
            return

        # 一列目のテキストを表示名とする
        label = item.text(0)

        # NodeGraphQt の実装詳細には依存せず、
        # UserRole に何か入っていればそれを ID として利用し、
        # 無ければ表示名をそのまま ID として扱う。
        content_id = item.data(0, Qt.UserRole) or label

        self.selection_changed.emit(str(content_id), label)

    def _setup_dock_behavior(self) -> None:
        """
        DockWidget としての許可エリアや挙動を設定する。

        左右だけでなく上下にもドッキングできるようにする。
        """
        self.setAllowedAreas(
            Qt.LeftDockWidgetArea
            | Qt.RightDockWidgetArea
            | Qt.TopDockWidgetArea
            | Qt.BottomDockWidgetArea
        )
        self.setFeatures(
            QDockWidget.DockWidgetMovable
            | QDockWidget.DockWidgetFloatable
            | QDockWidget.DockWidgetClosable
        )
