"""
ノードエディタ用メインウィンドウを定義するモジュール。

中央に NodeGraphQt のノードグラフを配置し、
左右（および上下）にインスペクタとコンテンツブラウザの DockWidget を追加する。

ユーザーは Dock をドラッグ＆ドロップして自由にレイアウトを変更できる。
"""

from typing import Optional

from PySide2.QtCore import Qt
from PySide2.QtWidgets import QMainWindow, QWidget

from .node_graph import NodeGraphWidget
from .inspector import InspectorDockWidget
from .content_browser import ContentBrowserDockWidget


class NodeEditorWindow(QMainWindow):
    """
    ノードエディタ全体のメインウィンドウ。

    - 中央: NodeGraphWidget（NodeGraphQt のラッパ）
    - Dock: InspectorDockWidget, ContentBrowserDockWidget
    """

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        """
        NodeEditorWindow のインスタンスを初期化する。

        Parameters
        ----------
        parent : QWidget, optional
            親ウィジェット。
        """
        super().__init__(parent)
        self.setWindowTitle("Node Editor")

        self._node_graph_widget: Optional[NodeGraphWidget] = None
        self._inspector_dock: Optional[InspectorDockWidget] = None
        self._content_browser_dock: Optional[ContentBrowserDockWidget] = None

        self._setup_central_node_graph()
        self._setup_docks()
        self._setup_dock_options()
        self._setup_connections()

    # ------------------------------------------------------------------
    # セットアップ処理
    # ------------------------------------------------------------------
    def _setup_central_node_graph(self) -> None:
        """
        中央に配置する NodeGraphWidget を生成し、メインウィンドウへセットする。
        """
        self._node_graph_widget = NodeGraphWidget(self)
        self.setCentralWidget(self._node_graph_widget)

    def _setup_docks(self) -> None:
        """
        インスペクタ／コンテンツブラウザの DockWidget を生成して配置する。
        """
        if self._node_graph_widget is None:
            raise RuntimeError("NodeGraphWidget が初期化されていません。")

        graph = self._node_graph_widget.graph

        # 右側: インスペクタ
        self._inspector_dock = InspectorDockWidget(graph=graph, parent=self)
        self.addDockWidget(Qt.RightDockWidgetArea, self._inspector_dock)

        # 左側: コンテンツブラウザ
        self._content_browser_dock = ContentBrowserDockWidget(graph=graph, parent=self)
        self.addDockWidget(Qt.LeftDockWidgetArea, self._content_browser_dock)

    def _setup_dock_options(self) -> None:
        """
        DockWidget の全体的な振る舞いを設定する。

        タブ化やネストしたドッキング、アニメーションなどを有効にする。
        """
        self.setDockOptions(
            QMainWindow.AllowTabbedDocks
            | QMainWindow.AllowNestedDocks
            | QMainWindow.AnimatedDocks
        )

    def _setup_connections(self) -> None:
        """
        ノードグラフ・コンテンツブラウザとインスペクタの連携を設定する。
        """
        if (
            self._node_graph_widget is None
            or self._inspector_dock is None
            or self._content_browser_dock is None
        ):
            return

        graph = self._node_graph_widget.graph

        # ノードグラフ側で選択が変わったら、インスペクタをノードモードに。
        graph.node_selection_changed.connect(self._on_graph_selection_changed)

        # コンテンツブラウザで選択が変わったら、インスペクタに内容を表示。
        self._content_browser_dock.selection_changed.connect(
            self._on_content_selection_changed
        )

    # ------------------------------------------------------------------
    # スロット
    # ------------------------------------------------------------------
    def _on_graph_selection_changed(self, *_args, **_kwargs) -> None:
        """
        ノードグラフ上の選択が変わったときに呼び出される。

        ノードが 1 つ以上選ばれているときは先頭ノードをインスペクタに表示し、
        何も選ばれていないときはインスペクタをクリアしてグレーアウトする。
        """
        if self._node_graph_widget is None or self._inspector_dock is None:
            return

        graph = self._node_graph_widget.graph
        selected = graph.selected_nodes()

        if not selected:
            self._inspector_dock.clear_all()
            return

        node = selected[0]
        self._inspector_dock.show_node(node)


    def _on_content_selection_changed(self, content_id: str, label: str) -> None:
        """
        コンテンツブラウザの選択が変わったときに呼び出される。

        コンテンツ ID が空の場合はインスペクタをクリアし、
        そうでない場合はコンテンツ情報ページを表示する。
        """
        if self._inspector_dock is None:
            return

        if not content_id:
            self._inspector_dock.clear_all()
            return

        self._inspector_dock.show_content_info(
            content_id=content_id,
            label=label,
            description="",
        )



    # ------------------------------------------------------------------
    # プロパティ
    # ------------------------------------------------------------------
    @property
    def node_graph(self) -> NodeGraphWidget:
        """
        中央に配置されている NodeGraphWidget を返す。

        Returns
        -------
        NodeGraphWidget
            ノードエディタ本体のウィジェット。
        """
        if self._node_graph_widget is None:
            raise RuntimeError("NodeGraphWidget がまだ初期化されていません。")
        return self._node_graph_widget
