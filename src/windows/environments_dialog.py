"""
rez 環境設定用のダイアログを定義するモジュール。

現時点ではプレースホルダ実装として、環境一覧領域と説明テキスト、
閉じるボタンのみを持つシンプルなモーダルダイアログを提供する。

将来的には rez のパッケージ一覧表示や、環境の追加・削除・
有効化／無効化などの機能をここに追加していく想定とする。
"""

from typing import Optional

from PySide2.QtCore import Qt
from PySide2.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QLabel,
    QListWidget,
    QVBoxLayout,
    QWidget,
)


class EnvironmentsDialog(QDialog):
    """
    rez パッケージ管理用の「Environments...」ダイアログ。

    現時点では以下のみを提供する。

    - 仮の環境リスト表示（QListWidget）
    - 説明ラベル
    - Close ボタン

    rez 実環境との連携は、今後このクラス内に機能を追加していく。
    """

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        """
        EnvironmentsDialog のインスタンスを初期化する。

        Parameters
        ----------
        parent:
            親ウィンドウ。通常は NodeEditorWindow。
        """
        super().__init__(parent)
        self.setWindowTitle("Environments")
        self.setModal(True)
        self.resize(480, 360)

        self._setup_ui()

    def _setup_ui(self) -> None:
        """
        ダイアログ内部の UI を構築する。
        """
        layout = QVBoxLayout(self)

        info_label = QLabel(
            "rez パッケージ環境の管理画面（プレースホルダ）です。\n"
            "将来的に、ここに利用可能な環境の一覧や、"
            "環境の追加・削除・切り替えなどの機能を実装します。",
            self,
        )
        info_label.setWordWrap(True)

        self._env_list = QListWidget(self)
        self._env_list.addItem("example_env_01  (placeholder)")
        self._env_list.addItem("example_env_02  (placeholder)")

        button_box = QDialogButtonBox(
            QDialogButtonBox.Close,
            orientation=Qt.Horizontal,
            parent=self,
        )
        button_box.rejected.connect(self.reject)
        button_box.accepted.connect(self.accept)

        layout.addWidget(info_label)
        layout.addWidget(self._env_list)
        layout.addWidget(button_box)
