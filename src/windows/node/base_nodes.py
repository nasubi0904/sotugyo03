"""
このツールで共通して利用するノードの基底クラスを定義するモジュール。

NodeGraphQt の BaseNode を継承し、共通の identifier や
基本ポート／プロパティをまとめておく。
"""

from NodeGraphQt import BaseNode
from NodeGraphQt.constants import NodePropWidgetEnum


class ToolBaseNode(BaseNode):
    """
    ツール内で利用するノードの共通ベースクラス。

    - identifier ドメインを 'sotugyo.nodes' に統一
    - in/out ポートを 1 本ずつ持つ
    - label / note という 2 つの文字列プロパティを持つ
    """

    # ノードタイプのドメイン（クラス名と組み合わせてフルパスになる）
    __identifier__ = "sotugyo.nodes"

    # デフォルトのノード名
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

        # プロパティ（PropertiesBin で編集可能）
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
            widget_type=NodePropWidgetEnum.QTEXT_EDIT.value
            if hasattr(NodePropWidgetEnum, "QTEXT_EDIT")
            else NodePropWidgetEnum.QLINE_EDIT.value,
            widget_tooltip="備考メモ。",
            tab="General",
        )
