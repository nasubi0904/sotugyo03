"""
メニュー拡張の例: Debug ツールを追加するモジュール。
"""

from ..menu_api import MenuRegistrar


def register_menus(registrar: MenuRegistrar) -> None:
    """
    MenuRegistrar を通じてメニュー項目を追加する。

    ここでは "Tools" メニュー配下に "Print Node Count" を追加し、
    クリック時に現在のノード数をコンソールに表示する。
    """

    def on_print_node_count() -> None:
        window = registrar._window  # 内部用。きれいにやるなら accessor を用意してもよい。
        from .node_graph import NodeGraphWidget  # 循環 import に注意して設計する

        central = window.centralWidget()
        if isinstance(central, NodeGraphWidget):
            graph = central.graph
            print(f"現在のノード数: {len(graph.all_nodes())}")

    registrar.add_action("Tools", "Print Node Count", on_print_node_count)
