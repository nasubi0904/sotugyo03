"""
このツールで共通して利用するノードの基底クラスと、
ノードクラスの自動発見・登録ロジックを定義するモジュール。

- ToolBaseNode: すべてのツール用ノードのベースクラス
- iter_tool_node_classes(): windows.node パッケージ内からサブクラスを自動列挙
- register_all_tool_nodes(graph): NodeGraph に全ツールノードを一括登録
"""

from __future__ import annotations

import importlib
import inspect
import pkgutil
from typing import Iterable, List, Type

from NodeGraphQt import BaseNode, NodeGraph


class ToolBaseNode(BaseNode):
    """
    ツール内で利用するノードの共通ベースクラス。

    - identifier ドメインを 'sotugyo.nodes' に統一
    - in/out ポートを 1 本ずつ持つ
    - label / note という 2 つの文字列プロパティを持つ
    """

    __identifier__ = "sotugyo.nodes"
    NODE_NAME = "Tool Node"

    def __init__(self) -> None:
        """
        ToolBaseNode のインスタンスを初期化する。
        """
        super(ToolBaseNode, self).__init__()

        # シンプルな in / out ポート
        self.add_input("in")
        self.add_output("out")

        # 共通プロパティ
        self.create_property("label", "")
        self.create_property("note", "")

    # ------------------------------------------------------------------ #
    #  ノード移動フック
    # ------------------------------------------------------------------ #
    def set_pos(self, x: float, y: float) -> None:
        """
        ノードの位置が変わったときに DateGridNode 側へ通知するためのフック。

        - 通常の挙動: 親クラスの set_pos を呼んで位置を更新
        - その後、DateGridNode.on_node_moved を呼び出して
          スナップ処理・子ノードの再レイアウトを行う
        """
        from .date_grid_node import DateGridNode  # 循環 import 回避のためローカル import

        # いったん普通に位置を更新
        super(ToolBaseNode, self).set_pos(x, y)

        # スナップ処理中の再帰呼び出しは無視
        if getattr(self, "_kdm_snapping", False):
            return

        graph = self.graph
        if not graph:
            return

        # DateGrid 側に「このノードが動いた」という情報を通知
        DateGridNode.on_node_moved(graph, self)


# ---------------------------------------------------------------------- #
#  ノード自動発見 / 登録
# ---------------------------------------------------------------------- #
def iter_tool_node_classes() -> Iterable[Type[ToolBaseNode]]:
    """
    windows.node パッケージ内から ToolBaseNode のサブクラスを自動列挙する。

    新しいノードを追加する際は、単に windows/node/ 以下に
    ToolBaseNode を継承したクラスを定義した .py を追加するだけでよい。
    既存コード側の import 追記は不要となる。

    Returns
    -------
    Iterable[Type[ToolBaseNode]]
        発見された ToolBaseNode サブクラスのイテレータ。
    """
    # このモジュールは windows.node.base_nodes
    package_name = __name__.rsplit(".", 1)[0]
    package = importlib.import_module(package_name)

    for module_info in pkgutil.iter_modules(package.__path__):
        # 先頭が '_' のモジュールはスキップ
        if module_info.name.startswith("_"):
            continue

        module_fullname = f"{package_name}.{module_info.name}"
        module = importlib.import_module(module_fullname)

        # モジュール内のクラスから ToolBaseNode のサブクラスを列挙
        for _name, obj in inspect.getmembers(module, inspect.isclass):
            if not issubclass(obj, ToolBaseNode):
                continue
            if obj is ToolBaseNode:
                continue
            yield obj


def list_tool_node_classes() -> List[Type[ToolBaseNode]]:
    """
    ToolBaseNode サブクラスをリストとして取得する補助関数。
    """
    return list(iter_tool_node_classes())


def register_all_tool_nodes(graph: NodeGraph) -> None:
    """
    指定された NodeGraph に対して、すべてのツールノードクラスを登録する。

    Parameters
    ----------
    graph:
        登録先の NodeGraph インスタンス。
    """
    for node_cls in iter_tool_node_classes():
        graph.register_node(node_cls)
