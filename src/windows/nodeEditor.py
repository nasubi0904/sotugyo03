"""
ノードエディタ用メインウィンドウを定義するモジュール。

中央に NodeGraphQt のノードグラフを配置し、
左右（および上下）にインスペクタとコンテンツブラウザの DockWidget を追加する。

さらにメニューバーを実装し、File メニューからプロジェクトの
保存／読み込み、Setting メニューから rez 環境管理ダイアログを開けるようにする。
"""

from typing import Optional

from PySide2.QtCore import Qt
from PySide2.QtWidgets import (
    QMainWindow,
    QWidget,
    QFileDialog,
)

from .node_graph import NodeGraphWidget
from .inspector import InspectorDockWidget
from .content_browser import ContentBrowserDockWidget
from .environments_dialog import EnvironmentsDialog
from .menu_api import load_menu_extensions


class NodeEditorWindow(QMainWindow):
    """
    ノードエディタ全体のメインウィンドウ。

    - 中央: NodeGraphWidget（NodeGraphQt のラッパ）
    - Dock: InspectorDockWidget, ContentBrowserDockWidget
    - Menu:
        - File
            - Save: プロジェクト保存
            - Open: プロジェクト読み込み
        - Setting
            - Environments...: rez 環境管理ダイアログをモーダル表示
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
        self.resize(1400, 900)

        self._node_graph_widget: Optional[NodeGraphWidget] = None
        self._inspector_dock: Optional[InspectorDockWidget] = None
        self._content_browser_dock: Optional[ContentBrowserDockWidget] = None

        self._setup_central_node_graph()
        self._setup_docks()
        self._setup_dock_options()
        self._setup_menu_bar()
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

    def _setup_menu_bar(self) -> None:
        """
        メニューバーを初期化し、menu_ext パッケージからメニュー拡張を読み込む。

        File / Setting を含むすべてのメニューは、menu_ext 側の拡張モジュールから
        追加される前提とする。
        """
        # menuBar() を呼んでおけばメニューバー自体は必ず生成される
        self.menuBar()
        load_menu_extensions(self)


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

        # ノードグラフ側で選択が変わったら、インスペクタへ通知。
        graph.node_selection_changed.connect(self._on_graph_selection_changed)

        # コンテンツブラウザで選択が変わったら、インスペクタへ通知。
        self._content_browser_dock.selection_changed.connect(
            self._on_content_selection_changed
        )

    # ------------------------------------------------------------------
    # Menu Action ハンドラ
    # ------------------------------------------------------------------
    def _on_action_save_project(self) -> None:
        """
        File > Save が押されたときに呼び出されるスロット。

        NodeGraphQt.NodeGraph.save_session() を使用して、
        ノード配置・接続・プロパティを JSON ファイルとして保存する。
        """
        if self._node_graph_widget is None:
            return

        graph = self._node_graph_widget.graph

        dialog = QFileDialog(self, "Save Project")
        dialog.setAcceptMode(QFileDialog.AcceptSave)
        dialog.setNameFilters(["Project Files (*.json)", "All Files (*)"])
        dialog.setDefaultSuffix("json")

        if dialog.exec_() != QFileDialog.Accepted:
            return

        file_path = dialog.selectedFiles()[0]
        if not file_path:
            return

        graph.save_session(file_path)

    def _on_action_open_project(self) -> None:
        """
        File > Open が押されたときに呼び出されるスロット。

        既存の JSON プロジェクトファイルを読み込み、
        NodeGraphQt.NodeGraph.load_session() によりグラフを再構築する。
        """
        if self._node_graph_widget is None:
            return

        graph = self._node_graph_widget.graph

        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Open Project",
            "",
            "Project Files (*.json);;All Files (*)",
        )
        if not file_path:
            return

        graph.load_session(file_path)


    def _on_action_open_environments(self) -> None:
        """
        Setting > Environments... が押されたときに呼び出されるスロット。

        rez パッケージ管理用の環境設定ダイアログをモーダルで表示する。
        実際の rez 連携ロジックは EnvironmentsDialog 側で今後実装していく。
        """
        dialog = EnvironmentsDialog(self)
        dialog.exec_()

    # ------------------------------------------------------------------
    # グラフ / コンテンツ 連携スロット
    # ------------------------------------------------------------------
    def _on_graph_selection_changed(self, *_args, **_kwargs) -> None:
        """
        ノードグラフ上のノード選択が変化したときに呼び出される。

        選択ノードが 1 つ以上ある場合、先頭ノードをインスペクタに表示し、
        何も選択されていない場合はインスペクタをクリアする。
        """
        if self._node_graph_widget is None or self._inspector_dock is None:
            return

        selected = self._node_graph_widget.graph.selected_nodes()
        if not selected:
            self._inspector_dock.clear_all()
            return

        node = selected[0]
        self._inspector_dock.show_node(node)

    def _on_content_selection_changed(self, content_id: str, label: str) -> None:
        """
        コンテンツブラウザで選択中の項目が変化したときに呼び出される。

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
