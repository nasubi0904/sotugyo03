"""
メニュー拡張用の API とローダを定義するモジュール。

- MenuRegistrar: QMainWindow に対してメニューやアクションを追加するための薄いラッパ
- load_menu_extensions(window): windows.menu_ext パッケージ配下の
  register_menus(registrar) を探して順に呼び出す
"""

from __future__ import annotations

import importlib
import pkgutil
from typing import Callable

from PySide2.QtWidgets import QMainWindow, QMenu, QAction


class MenuRegistrar:
    """
    メニュー拡張用のシンプルなラッパクラス。

    拡張モジュール側では、このクラスを通じてメニューやアクションを追加する。
    """

    def __init__(self, window: QMainWindow) -> None:
        """
        MenuRegistrar を初期化する。

        Parameters
        ----------
        window:
            メニューを追加する対象の QMainWindow。
        """
        self._window = window

    @property
    def window(self) -> QMainWindow:
        """
        メニューを追加する対象のウィンドウを返す。
        """
        return self._window

    def get_or_create_menu(self, path: str) -> QMenu:
        """
        'File/Export' のようなパス表現から QMenu を取得または作成する。

        例
        ---
        registrar.get_or_create_menu("Tools")
        registrar.get_or_create_menu("File/Export")
        """
        parts = [p for p in path.split("/") if p]
        menu_bar = self._window.menuBar()
        parent_menu: QMenu | None  # type: ignore[annotation-unchecked]

        parent_menu = None
        for i, part in enumerate(parts):
            if i == 0:
                # ルートレベルのメニュー
                menu = None
                for existing_menu in menu_bar.findChildren(QMenu):
                    if existing_menu.title() == part:
                        menu = existing_menu
                        break
                if menu is None:
                    menu = menu_bar.addMenu(part)
                parent_menu = menu
            else:
                # サブメニュー
                assert parent_menu is not None
                sub_menu = None
                for action in parent_menu.actions():
                    w = action.menu()
                    if w is not None and w.title() == part:
                        sub_menu = w
                        break
                if sub_menu is None:
                    sub_menu = parent_menu.addMenu(part)
                parent_menu = sub_menu

        assert parent_menu is not None
        return parent_menu

    def add_action(
        self,
        menu_path: str,
        label: str,
        callback: Callable[[], None],
        shortcut: str | None = None,
    ) -> QAction:
        """
        指定されたメニューパスにアクションを追加する。

        Parameters
        ----------
        menu_path:
            'File' や 'Tools/Debug' のようなメニュー階層。
        label:
            メニューに表示するラベル。
        callback:
            アクションがトリガーされたときに呼ぶコールバック。
        shortcut:
            ショートカット文字列（例: 'Ctrl+S'）。不要なら None。

        Returns
        -------
        QAction
            追加された QAction。
        """
        menu = self.get_or_create_menu(menu_path)
        action = menu.addAction(label)
        if shortcut:
            action.setShortcut(shortcut)
        action.triggered.connect(callback)
        return action


def load_menu_extensions(window: QMainWindow) -> None:
    """
    windows.menu_ext パッケージ配下のメニュー拡張モジュールを読み込み、
    各モジュールの register_menus(registrar) を実行する。

    これにより、NodeEditorWindow 本体のコードを変更せずに
    メニュー拡張を行うことができる。
    """
    # menu_api の __package__ は 'windows'（または 'window'）を想定
    package_name = f"{__package__}.menu_ext"
    try:
        package = importlib.import_module(package_name)
    except ImportError:
        # 拡張パッケージが存在しない場合は何もしない
        return

    registrar = MenuRegistrar(window)

    for module_info in pkgutil.iter_modules(package.__path__):
        if module_info.name.startswith("_"):
            continue

        module_fullname = f"{package_name}.{module_info.name}"
        module = importlib.import_module(module_fullname)
        register = getattr(module, "register_menus", None)
        if callable(register):
            register(registrar)
