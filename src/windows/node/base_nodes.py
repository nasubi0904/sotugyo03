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
from NodeGraphQt.constants import NodePropWidgetEnum


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

        共通の入出力ポートとプロパティを定義する。
        """
        super().__init__()

        # 共通のポート
        self.add_input("in")
        self.add_output("out")

        # 共通プロパティ
        self.create_property(
            name="label",
            value="",
            widget_type=NodePropWidgetEnum.QLINE_EDIT.value,
            widget_tooltip="ノードの表示用ラベル。",
            tab="General",
        )
        self.create_property(
            name="note",
            value="",
            widget_type=(
                getattr(NodePropWidgetEnum, "QTEXT_EDIT", NodePropWidgetEnum.QLINE_EDIT)
            ).value,
            widget_tooltip="備考メモ。",
            tab="General",
        )


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
    # このモジュールは windows.node.base_nodes なので、
    # 親パッケージ windows.node を特定する
    package_name = __name__.rsplit(".", 1)[0]  # -> 'windows.node'
    package = importlib.import_module(package_name)

    # パッケージ直下のモジュールを走査
    for module_info in pkgutil.iter_modules(package.__path__):
        # 自分自身（base_nodes.py）はスキップ
        if module_info.name == "base_nodes":
            continue
        # アンダースコア始まりのモジュールもスキップ（内部用想定）
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


def collect_tool_node_classes() -> List[Type[ToolBaseNode]]:
    """
    ToolBaseNode サブクラスをすべてリストにまとめて返すヘルパー。

    Returns
    -------
    list[Type[ToolBaseNode]]
        発見された ToolBaseNode サブクラスの一覧。
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
