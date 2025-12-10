"""
アプリケーションのエントリポイント。

src/start.py を直接実行すると UI（NodeEditorWindow）が起動する。
相対パスのみを使用し、外部環境に依存しない構成とする。
"""

import os
import sys
from PySide2.QtWidgets import QApplication


def _append_local_packages() -> None:
    """
    カレントディレクトリ（src）の windows パッケージを import 可能にする。

    start.py と同階層の windows ディレクトリを sys.path に追加することで、
    相対パスのみで UI コンポーネントをロードできるようにする。
    """
    current_dir = os.path.dirname(os.path.abspath(__file__))

    if current_dir not in sys.path:
        sys.path.insert(0, current_dir)


def main() -> None:
    """
    PySide2 を初期化し、NodeEditorWindow を表示するメイン関数。
    """
    _append_local_packages()

    # windows パッケージをインポート（相対パス完全準拠）
    from windows.nodeEditor import NodeEditorWindow  # type: ignore

    app = QApplication.instance() or QApplication(sys.argv)

    window = NodeEditorWindow()
    window.show()

    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
