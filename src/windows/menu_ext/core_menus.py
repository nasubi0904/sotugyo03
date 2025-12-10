"""
NodeEditor 標準の File / Setting メニューを登録する拡張モジュール。

- File
    - Save
    - Open
- Setting
    - （見出しのみ。将来ここに項目を足す）
"""

from typing import cast

from ..menu_api import MenuRegistrar
from ..nodeEditor import NodeEditorWindow


def register_menus(registrar: MenuRegistrar) -> None:
    """
    MenuRegistrar を用いて、標準の File / Setting メニューを登録する。
    """
    # QMainWindow を NodeEditorWindow として扱う
    window = cast(NodeEditorWindow, registrar.window)

    # File メニュー
    registrar.add_action(
        menu_path="File",
        label="Save",
        callback=window._on_action_save_project,
        shortcut="Ctrl+S",
    )
    registrar.add_action(
        menu_path="File",
        label="Open",
        callback=window._on_action_open_project,
        shortcut="Ctrl+O",
    )

    # Setting メニュー（見出しだけ作っておく）
    registrar.get_or_create_menu("Setting")
