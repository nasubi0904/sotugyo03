"""
インスペクタ Dock を定義するモジュール。

- ノード選択中は「ノードページ」を表示し、そのノードの名前・label・note を
  閲覧 / 編集できる。
- コンテンツブラウザ選択中は「コンテンツページ」を表示し、
  選択中項目の情報 + メモを表示 / 編集できる。
- 何も選択していない場合は両ページをグレーアウトし、編集できない状態にする。
"""

from typing import Dict, Optional

from PySide2.QtCore import Qt
from PySide2.QtWidgets import (
    QDockWidget,
    QWidget,
    QStackedWidget,
    QFormLayout,
    QLabel,
    QLineEdit,
    QTextEdit,
)

from NodeGraphQt import NodeGraph, NodeObject


class InspectorDockWidget(QDockWidget):
    """
    ノード／コンテンツの情報を表示・編集するインスペクタ DockWidget。

    内部に 2 ページを持ち、状況に応じて表示内容と有効 / 無効状態を切り替える。
    """

    def __init__(self, graph: NodeGraph, parent: Optional[QWidget] = None) -> None:
        """
        InspectorDockWidget を初期化する。

        Parameters
        ----------
        graph:
            対象となる NodeGraph インスタンス。
        parent:
            親ウィジェット。
        """
        super().__init__("Inspector", parent)

        self._graph = graph

        # 現在選択中のノード / コンテンツ ID
        self._current_node: Optional[NodeObject] = None
        self._current_content_id: Optional[str] = None
        self._content_notes: Dict[str, str] = {}

        # ページ切り替え用スタック
        self._stack = QStackedWidget(self)
        self.setWidget(self._stack)

        # --- ノードページ ---
        self._node_page = QWidget(self)
        self._setup_node_page(self._node_page)

        # --- コンテンツページ ---
        self._content_page = QWidget(self)
        self._setup_content_page(self._content_page)

        self._stack.addWidget(self._node_page)     # index 0
        self._stack.addWidget(self._content_page)  # index 1

        # 初期状態：何も選択されていないので両ページをグレーアウト
        self._stack.setCurrentWidget(self._node_page)
        self._set_node_page_enabled(False)
        self._set_content_page_enabled(False)

        self._setup_dock_behavior()

    # ------------------------------------------------------------------
    # ページ構築
    # ------------------------------------------------------------------
    def _setup_node_page(self, page: QWidget) -> None:
        """
        ノード情報表示用ページの UI を構築する。
        """
        form = QFormLayout(page)

        # Node 名（タイトルに出る名前）
        self._node_name_edit = QLineEdit(page)
        form.addRow("Node Name", self._node_name_edit)

        # label プロパティ
        self._node_label_edit = QLineEdit(page)
        form.addRow("label", self._node_label_edit)

        # note プロパティ
        self._node_note_edit = QTextEdit(page)
        self._node_note_edit.setMinimumHeight(80)
        form.addRow("note", self._node_note_edit)

        # 編集反映
        self._node_name_edit.editingFinished.connect(self._on_node_name_edited)
        self._node_label_edit.editingFinished.connect(self._on_node_label_edited)
        self._node_note_edit.textChanged.connect(self._on_node_note_changed)

    def _setup_content_page(self, page: QWidget) -> None:
        """
        コンテンツ情報表示用ページの UI を構築する。
        """
        form = QFormLayout(page)

        self._content_id_label = QLabel("-", page)
        self._content_label_label = QLabel("-", page)
        self._content_note_edit = QLineEdit(page)
        self._content_desc_edit = QTextEdit(page)
        self._content_desc_edit.setReadOnly(True)
        self._content_desc_edit.setPlaceholderText(
            "このコンテンツに紐づく説明文を今後表示する予定の領域です。"
        )

        form.addRow("ID / 種別", self._content_id_label)
        form.addRow("表示名", self._content_label_label)
        form.addRow("メモ", self._content_note_edit)
        form.addRow("説明", self._content_desc_edit)

        self._content_note_edit.editingFinished.connect(self._on_content_note_edited)

    # ------------------------------------------------------------------
    # モード切り替え系 API
    # ------------------------------------------------------------------
    def clear_all(self) -> None:
        """
        ノード / コンテンツの情報をすべてクリアし、両ページをグレーアウトする。

        何も選択されていない状態に対応する。
        """
        self._current_node = None
        self._current_content_id = None

        # ノードページのクリア
        self._node_name_edit.clear()
        self._node_label_edit.clear()
        self._node_note_edit.blockSignals(True)
        self._node_note_edit.clear()
        self._node_note_edit.blockSignals(False)
        self._set_node_page_enabled(False)

        # コンテンツページのクリア
        self._content_id_label.setText("-")
        self._content_label_label.setText("-")
        self._content_desc_edit.clear()
        self._content_note_edit.clear()
        self._set_content_page_enabled(False)

        # 表示はとりあえずノードページ側を見せておく
        self._stack.setCurrentWidget(self._node_page)
        self._stack.update()

    def show_node(self, node: NodeObject) -> None:
        """
        ノードページに切り替え、指定ノードの情報を表示する。

        ノードが持っていないプロパティに対応するテキストボックスは
        グレーアウト（無効化）する。
        """
        self._current_node = node

        # Node 名は常に編集可能
        self._node_name_edit.setText(node.name())
        self._node_name_edit.setEnabled(True)

        # label プロパティ
        if node.has_property("label"):
            text = str(node.get_property("label") or "")
            self._node_label_edit.setText(text)
            self._node_label_edit.setEnabled(True)
        else:
            self._node_label_edit.clear()
            self._node_label_edit.setEnabled(False)

        # note プロパティ
        if node.has_property("note"):
            note = str(node.get_property("note") or "")
            self._node_note_edit.blockSignals(True)
            self._node_note_edit.setPlainText(note)
            self._node_note_edit.blockSignals(False)
            self._node_note_edit.setEnabled(True)
        else:
            self._node_note_edit.blockSignals(True)
            self._node_note_edit.clear()
            self._node_note_edit.blockSignals(False)
            self._node_note_edit.setEnabled(False)

        self._set_node_page_enabled(True)
        self._set_content_page_enabled(False)

        self._stack.setCurrentWidget(self._node_page)
        self._stack.update()

    def show_content_info(self, content_id: str, label: str, description: str = "") -> None:
        """
        コンテンツページに切り替え、指定項目の情報を表示する。

        Parameters
        ----------
        content_id:
            コンテンツを一意に識別する ID。
        label:
            表示名。
        description:
            追加説明文。
        """
        self._current_content_id = content_id

        self._content_id_label.setText(content_id or "(不明)")
        self._content_label_label.setText(label or "(不明)")
        self._content_desc_edit.setPlainText(description or "")

        note = self._content_notes.get(content_id, "")
        self._content_note_edit.setText(note)

        self._set_content_page_enabled(True)
        self._set_node_page_enabled(False)

        self._stack.setCurrentWidget(self._content_page)
        self._stack.update()

    # ------------------------------------------------------------------
    # ノード編集用スロット
    # ------------------------------------------------------------------
    def _on_node_name_edited(self) -> None:
        if not self._current_node:
            return
        self._current_node.set_property("name", self._node_name_edit.text())

    def _on_node_label_edited(self) -> None:
        if not self._current_node or not self._current_node.has_property("label"):
            return
        self._current_node.set_property("label", self._node_label_edit.text())

    def _on_node_note_changed(self) -> None:
        if not self._current_node or not self._current_node.has_property("note"):
            return
        self._current_node.set_property("note", self._node_note_edit.toPlainText())

    # ------------------------------------------------------------------
    # コンテンツ編集用スロット
    # ------------------------------------------------------------------
    def _on_content_note_edited(self) -> None:
        if not self._current_content_id:
            return
        self._content_notes[self._current_content_id] = self._content_note_edit.text()

    # ------------------------------------------------------------------
    # enable / disable 共通処理
    # ------------------------------------------------------------------
    def _set_node_page_enabled(self, enabled: bool) -> None:
        """
        ノードページ全体の有効 / 無効を切り替える。
        """
        self._node_page.setEnabled(enabled)

    def _set_content_page_enabled(self, enabled: bool) -> None:
        """
        コンテンツページ全体の有効 / 無効を切り替える。
        """
        self._content_page.setEnabled(enabled)

    # ------------------------------------------------------------------
    # Dock 設定
    # ------------------------------------------------------------------
    def _setup_dock_behavior(self) -> None:
        """
        DockWidget の挙動（ドッキング可能方向・機能）を設定する。
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
