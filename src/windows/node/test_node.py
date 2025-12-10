"""
テスト用ノードを定義するモジュール。

ToolBaseNode を継承し、このツールでのノード定義・登録の
基本的な流れを確認するためのシンプルなノードを提供する。
"""

from .base_nodes import ToolBaseNode


class TestNode(ToolBaseNode):
    """
    動作確認用のシンプルなテストノード。

    - ToolBaseNode の in/out ポートと label / note プロパティをそのまま利用
    - デフォルト値だけ上書き
    """

    # ここではあえてベースと同じ identifier を使う。
    __identifier__ = ToolBaseNode.__identifier__
    NODE_NAME = "Test Node"

    def __init__(self) -> None:
        """
        TestNode のインスタンスを初期化する。

        共通プロパティに初期値をセットする。
        """
        super().__init__()

        self.set_property("label", "Test Node")
        self.set_property("note", "テスト用ノードです。")
