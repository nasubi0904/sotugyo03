# windows/menu_ext/rez_env_manager.py
#
# 「Setting > Rez Environment Manager...」メニューを追加し、
# ローカルディレクトリ内の rez パッケージを管理する。
#
# 機能:
#   - DCC / ツールをスキャンして package.py を自動生成
#     - Autodesk: Maya / 3ds Max / MotionBuilder / Mudbox などを含む
#       Autodesk 配下のほぼすべての DCC 実行ファイル
#     - Adobe: After Effects / Photoshop / Premiere / Illustrator / Substance など
#       Adobe 配下のほぼすべての製品
#     - Houdini / Blender / Unreal / Nuke / Python も対象
#   - パッケージ一覧の再読み込み
#   - 実体(TOOL_PATH)の存在チェック
#   - 選択パッケージの削除
#   - 選択パッケージフォルダを開く
#   - 任意の exe を手動選択してパッケージとして追加

import os
import re
import sys
import shutil
from pathlib import Path
from typing import List, Optional, Tuple

from PySide2.QtCore import Qt, QUrl
from PySide2.QtGui import QDesktopServices
from PySide2.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
    QFileDialog,
    QInputDialog,
)

from ..menu_api import MenuRegistrar  # type: ignore


# ------------------------------------------------------------
# 定数
# ------------------------------------------------------------

_USER_ROLE_DIR = Qt.UserRole
_USER_ROLE_LABEL = Qt.UserRole + 1
_USER_ROLE_MISSING = Qt.UserRole + 2


# ------------------------------------------------------------
# ユーティリティ
# ------------------------------------------------------------

def _get_packages_root() -> Path:
    """
    ローカルの rez パッケージを保存するルートディレクトリを返す。

    - 環境変数 REZ_LOCAL_ROOT があればそれを利用
    - なければユーザーホーム配下 ~/.rez_local/packages を利用
    """
    env_root = os.environ.get("REZ_LOCAL_ROOT")
    if env_root:
        base = Path(env_root)
    else:
        base = Path.home() / ".rez_local"

    packages_dir = base / "packages"
    packages_dir.mkdir(parents=True, exist_ok=True)
    return packages_dir


def _extract_version_from_name(name: str) -> str:
    """
    ディレクトリ名などから数字部分を抽出してバージョン文字列にする簡易ヘルパー。
    見つからなければ "1.0.0" を返す。
    """
    matches = re.findall(r"\d+(?:\.\d+)*", name)
    if not matches:
        return "1.0.0"
    return matches[0]


def _ensure_package_dir(name: str, version: str) -> Path:
    """
    packages/<name>/<version>/ ディレクトリを作成し、そのパスを返す。
    """
    root = _get_packages_root()
    package_dir = root / name / version
    package_dir.mkdir(parents=True, exist_ok=True)
    return package_dir


def _generate_generic_package(
    name: str,
    version: str,
    bin_path: Path,
    exe_path: Path,
) -> str:
    """
    PATH を追加するだけのシンプルな package.py 本文を生成する。

    package.py の先頭行に TOOL_PATH=... のコメントを残しておき、
    実体チェック時に利用する。
    """
    bin_norm = bin_path.as_posix()
    exe_norm = exe_path.as_posix()
    body = f'''# TOOL_PATH={exe_norm}
# Auto-generated rez package

name = "{name}"
version = "{version}"

def commands():
    # 実行バイナリのディレクトリを PATH の先頭に追加
    env.PATH.prepend(r"{bin_norm}")
'''
    return body


def _find_program_files_dirs() -> List[Path]:
    """
    Program Files 相当のディレクトリ候補を返す。
    (PROGRAMFILES, PROGRAMFILES(X86) を見る)
    """
    dirs: List[Path] = []
    for key in ("PROGRAMFILES", "PROGRAMFILES(X86)"):
        v = os.environ.get(key)
        if v:
            p = Path(v)
            if p.is_dir():
                dirs.append(p)

    # 重複排除
    unique: List[Path] = []
    seen = set()
    for d in dirs:
        rp = str(d.resolve()).lower()
        if rp in seen:
            continue
        seen.add(rp)
        unique.append(d)
    return unique


def _pick_main_executable(candidates: List[Path]) -> Optional[Path]:
    """
    ある製品フォルダ配下の exe 群から「メインっぽい」実行ファイルを 1 つ選ぶ簡易ロジック。

    - アンインストーラ・インストーラ系は除外
    - よくある DCC 名（maya, 3dsmax, houdini, blender, unreal, nuke, afterfx,
      photoshop, illustrator, premiere, substance など）を優先
    - それでも決まらなければ最も浅いパス（親に近い）を採用
    """
    if not candidates:
        return None

    skip_keywords = ("uninstall", "unins", "setup", "installer", "service", "helper", "crash")
    filtered = []
    for exe in candidates:
        low = exe.name.lower()
        if any(k in low for k in skip_keywords):
            continue
        filtered.append(exe)
    if not filtered:
        filtered = candidates[:]

    # 優先したい exe 名の断片
    priority_keywords = [
        "maya",
        "3dsmax",
        "motionbuilder",
        "mudbox",
        "houdini",
        "blender",
        "unreal",
        "editor",          # UnrealEditor, UE4Editor など
        "nuke",
        "afterfx",
        "photoshop",
        "illustrator",
        "premiere",
        "substance",
        "designer",
        "painter",
        "sampler",
        "stager",
    ]

    # キーワードマッチがあるものを優先
    for kw in priority_keywords:
        for exe in filtered:
            if kw in exe.name.lower():
                return exe

    # それでも決まらなければ、パスの長さが短い順 = フォルダ直下に近いものを優先
    filtered.sort(key=lambda p: len(str(p)))
    return filtered[0] if filtered else None


# ------------------------------------------------------------
# DCC スキャン
# ------------------------------------------------------------

def _find_autodesk_all() -> List[Tuple[str, str, Path, Path, str]]:
    """
    Autodesk 配下の製品フォルダをすべて走査し、
    メインと思われる exe を 1 つ選んで返す。

    戻り値:
        (name, version, bin_path, exe_path, human_label)
    """
    results: List[Tuple[str, str, Path, Path, str]] = []

    for pf in _find_program_files_dirs():
        autodesk_root = pf / "Autodesk"
        if not autodesk_root.is_dir():
            continue

        for prod_dir in autodesk_root.iterdir():
            if not prod_dir.is_dir():
                continue

            # 製品名（表示用）
            human_label = prod_dir.name

            # exe 候補を集める（フォルダ直下と bin, win64 など 1 階層程度）
            candidates: List[Path] = []

            # 直下
            for exe in prod_dir.glob("*.exe"):
                if exe.is_file():
                    candidates.append(exe)

            # bin 配下
            bin_dir = prod_dir / "bin"
            if bin_dir.is_dir():
                for exe in bin_dir.glob("*.exe"):
                    if exe.is_file():
                        candidates.append(exe)

            # さらに 1 階層下（bin/win64 など）を少し見る
            for sub in prod_dir.glob("*"):
                if sub.is_dir() and sub.name.lower() in ("win64", "win32", "x64"):
                    for exe in sub.glob("*.exe"):
                        if exe.is_file():
                            candidates.append(exe)

            main_exe = _pick_main_executable(candidates)
            if not main_exe:
                continue

            name = main_exe.stem.lower()
            version = _extract_version_from_name(prod_dir.name)
            bin_path = main_exe.parent

            results.append((name, version, bin_path, main_exe, human_label))

    return results


def _find_houdini() -> List[Tuple[str, str, Path, Path]]:
    """
    Houdini のインストールを簡易スキャンする。
    """
    results: List[Tuple[str, str, Path, Path]] = []
    for pf in _find_program_files_dirs():
        root = pf / "Side Effects Software"
        if not root.is_dir():
            continue
        for child in root.iterdir():
            if not child.is_dir():
                continue
            if "houdini" not in child.name.lower():
                continue
            exe = child / "bin" / "houdini.exe"
            if exe.is_file():
                version = _extract_version_from_name(child.name)
                name = "houdini"
                bin_path = exe.parent
                results.append((name, version, bin_path, exe))
    return results


def _find_blender() -> List[Tuple[str, str, Path, Path]]:
    """
    Blender のインストールを簡易スキャンする。
    """
    results: List[Tuple[str, str, Path, Path]] = []
    for pf in _find_program_files_dirs():
        root = pf / "Blender Foundation"
        if not root.is_dir():
            continue
        for child in root.iterdir():
            if not child.is_dir():
                continue
            if "blender" not in child.name.lower():
                continue
            exe = child / "blender.exe"
            if exe.is_file():
                version = _extract_version_from_name(child.name)
                name = "blender"
                bin_path = exe.parent
                results.append((name, version, bin_path, exe))
    return results


def _find_unreal() -> List[Tuple[str, str, Path, Path]]:
    """
    Unreal Engine のインストールを簡易スキャンする。
    """
    results: List[Tuple[str, str, Path, Path]] = []
    for pf in _find_program_files_dirs():
        root = pf / "Epic Games"
        if not root.is_dir():
            continue
        for child in root.iterdir():
            if not child.is_dir():
                continue
            # UE_5.0, UE_4.27 など
            if not child.name.startswith("UE_"):
                continue
            ue_exe = child / "Engine" / "Binaries" / "Win64" / "UnrealEditor.exe"
            if not ue_exe.is_file():
                ue_exe = child / "Engine" / "Binaries" / "Win64" / "UE4Editor.exe"
            if ue_exe.is_file():
                version = _extract_version_from_name(child.name)
                name = "unreal"
                bin_path = ue_exe.parent
                results.append((name, version, bin_path, ue_exe))
    return results


def _find_nuke() -> List[Tuple[str, str, Path, Path]]:
    """
    Nuke のインストールを簡易スキャンする。
    """
    results: List[Tuple[str, str, Path, Path]] = []
    for pf in _find_program_files_dirs():
        for child in pf.iterdir():
            if not child.is_dir():
                continue
            low = child.name.lower()
            if not low.startswith("nuke"):
                continue
            for exe in child.glob("Nuke*.exe"):
                if exe.is_file():
                    version = _extract_version_from_name(child.name)
                    name = "nuke"
                    bin_path = exe.parent
                    results.append((name, version, bin_path, exe))
    return results


def _find_adobe_all() -> List[Tuple[str, str, Path, Path, str]]:
    """
    Adobe 配下の製品フォルダをすべて走査し、
    メインと思われる exe を 1 つ選んで返す。

    Illustrator / Substance 系も含め、Adobe フォルダ配下の製品を
    できる限り拾う。
    戻り値:
        (name, version, bin_path, exe_path, human_label)
    """
    results: List[Tuple[str, str, Path, Path, str]] = []

    for pf in _find_program_files_dirs():
        root = pf / "Adobe"
        if not root.is_dir():
            continue

        for prod_dir in root.iterdir():
            if not prod_dir.is_dir():
                continue

            human_label = prod_dir.name

            # exe 候補を集める
            candidates: List[Path] = []

            # フォルダ直下
            for exe in prod_dir.glob("*.exe"):
                if exe.is_file():
                    candidates.append(exe)

            # 1 階層下（Support Files / Plug-ins など多い）
            for sub in prod_dir.glob("*"):
                if not sub.is_dir():
                    continue
                # サブフォルダ名はあまり絞らずに見る
                for exe in sub.glob("*.exe"):
                    if exe.is_file():
                        candidates.append(exe)

            main_exe = _pick_main_executable(candidates)
            if not main_exe:
                continue

            name = main_exe.stem.lower()
            version = _extract_version_from_name(prod_dir.name)
            bin_path = main_exe.parent

            results.append((name, version, bin_path, main_exe, human_label))

    return results


def _find_python() -> List[Tuple[str, str, Path, Path]]:
    """
    Python のインストールを簡易スキャンする。
    - 現在の python.exe
    - LOCALAPPDATA/Programs/Python 以下
    """
    results: List[Tuple[str, str, Path, Path]] = []

    # このプロセス自身
    this_python = Path(sys.executable)
    if this_python.name.lower() == "python.exe" and this_python.is_file():
        version = _extract_version_from_name(this_python.parent.name)
        name = "python"
        bin_path = this_python.parent
        results.append((name, version, bin_path, this_python))

    # よくあるユーザーローカル Python
    local_root = os.environ.get("LOCALAPPDATA")
    if local_root:
        py_root = Path(local_root) / "Programs" / "Python"
        if py_root.is_dir():
            for child in py_root.iterdir():
                if not child.is_dir():
                    continue
                exe = child / "python.exe"
                if exe.is_file():
                    version = _extract_version_from_name(child.name)
                    name = "python"
                    bin_path = exe.parent
                    results.append((name, version, bin_path, exe))

    # 重複除去
    unique: List[Tuple[str, str, Path, Path]] = []
    seen = set()
    for n, v, b, e in results:
        key = (n, v, str(b.resolve()).lower())
        if key in seen:
            continue
        seen.add(key)
        unique.append((n, v, b, e))
    return unique


def _scan_all_dcc() -> List[Tuple[str, str, Path, Path, str]]:
    """
    複数の DCC / ツールをまとめてスキャンし、
    (name, version, bin_path, exe_path, human_label) のリストを返す。
    """
    collected: List[Tuple[str, str, Path, Path, str]] = []

    # Autodesk 全般
    for name, version, bin_path, exe, label in _find_autodesk_all():
        collected.append((name, version, bin_path, exe, f"Autodesk: {label}"))

    # Houdini / Blender / Unreal / Nuke / Python
    for name, version, bin_path, exe in _find_houdini():
        collected.append((name, version, bin_path, exe, "Houdini"))

    for name, version, bin_path, exe in _find_blender():
        collected.append((name, version, bin_path, exe, "Blender"))

    for name, version, bin_path, exe in _find_unreal():
        collected.append((name, version, bin_path, exe, "Unreal"))

    for name, version, bin_path, exe in _find_nuke():
        collected.append((name, version, bin_path, exe, "Nuke"))

    for name, version, bin_path, exe in _find_python():
        collected.append((name, version, bin_path, exe, "Python"))

    # Adobe 全般（After Effects / Photoshop / Premiere / Illustrator / Substance など）
    for name, version, bin_path, exe, label in _find_adobe_all():
        collected.append((name, version, bin_path, exe, f"Adobe: {label}"))

    return collected


# ------------------------------------------------------------
# ダイアログ本体
# ------------------------------------------------------------

class RezEnvManagerDialog(QDialog):
    """
    ローカル rez パッケージを管理するダイアログ。

    - packages 以下の package.py を一覧表示
    - DCC / ツールをスキャンして package.py を自動生成
    - パッケージ一覧の再読み込み
    - 実体(TOOL_PATH)の存在チェック
    - 選択パッケージの削除 / フォルダを開く
    - 任意の exe を手動でパッケージ化
    """

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Rez Environment Manager")
        self.resize(780, 500)

        self._packages_root = _get_packages_root()

        self._setup_ui()
        self._refresh_package_list()

    # --------------------------------------------------------
    # UI
    # --------------------------------------------------------
    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)

        info_label = QLabel(
            "ローカルの rez パッケージを管理します。\n"
            "Autodesk / Adobe を含む DCC / ツールの自動スキャンと、任意 exe からの追加が可能です。",
            self,
        )
        info_label.setWordWrap(True)
        layout.addWidget(info_label)

        # パッケージ一覧
        self._list = QListWidget(self)
        layout.addWidget(self._list, 1)

        # ボタン行 1（スキャン・再読み込み・手動追加）
        row1 = QHBoxLayout()
        self._scan_button = QPushButton("DCC をスキャンしてパッケージ化", self)
        self._reload_button = QPushButton("一覧を再読み込み", self)
        self._manual_add_button = QPushButton("手動で追加", self)
        row1.addWidget(self._scan_button)
        row1.addWidget(self._reload_button)
        row1.addWidget(self._manual_add_button)
        row1.addStretch(1)
        layout.addLayout(row1)

        # ボタン行 2（チェック・削除・フォルダを開く）
        row2 = QHBoxLayout()
        self._validate_button = QPushButton("実体をチェック", self)
        self._delete_button = QPushButton("選択パッケージを削除", self)
        self._open_button = QPushButton("選択フォルダを開く", self)
        row2.addWidget(self._validate_button)
        row2.addWidget(self._delete_button)
        row2.addWidget(self._open_button)
        row2.addStretch(1)
        layout.addLayout(row2)

        # 下部 Close
        button_box = QDialogButtonBox(QDialogButtonBox.Close, parent=self)
        layout.addWidget(button_box)

        # シグナル
        self._scan_button.clicked.connect(self._on_scan_and_create)
        self._reload_button.clicked.connect(self._refresh_package_list)
        self._manual_add_button.clicked.connect(self._on_manual_add)
        self._validate_button.clicked.connect(self._on_validate_packages)
        self._delete_button.clicked.connect(self._on_delete_selected)
        self._open_button.clicked.connect(self._on_open_selected)
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)

    # --------------------------------------------------------
    # パッケージ一覧
    # --------------------------------------------------------
    def _refresh_package_list(self) -> None:
        """
        packages 以下の package.py を列挙して一覧を更新する。
        """
        self._list.clear()

        root = self._packages_root
        if not root.is_dir():
            return

        for name_dir in sorted(root.iterdir()):
            if not name_dir.is_dir():
                continue
            name = name_dir.name
            for ver_dir in sorted(name_dir.iterdir()):
                if not ver_dir.is_dir():
                    continue
                version = ver_dir.name
                pkg_file = ver_dir / "package.py"
                if not pkg_file.is_file():
                    continue

                label = f"{name}-{version}"
                item = QListWidgetItem(label)
                item.setData(_USER_ROLE_DIR, str(ver_dir))
                item.setData(_USER_ROLE_LABEL, label)
                item.setData(_USER_ROLE_MISSING, False)
                self._list.addItem(item)

    # --------------------------------------------------------
    # スキャン & パッケージ生成
    # --------------------------------------------------------
    def _on_scan_and_create(self) -> None:
        """
        DCC / ツールをスキャンし、未登録のものについて package.py を生成する。
        """
        dcc_list = _scan_all_dcc()
        if not dcc_list:
            QMessageBox.information(self, "Rez Environment Manager", "検出された DCC / ツールはありません。")
            return

        created: List[str] = []
        skipped: List[str] = []

        for name, version, bin_path, exe_path, label in dcc_list:
            pkg_dir = _ensure_package_dir(name, version)
            pkg_file = pkg_dir / "package.py"
            if pkg_file.is_file():
                skipped.append(f"{name}-{version} ({label})")
                continue

            body = _generate_generic_package(name, version, bin_path, exe_path)
            pkg_file.write_text(body, encoding="utf-8")
            created.append(f"{name}-{version} ({label})")

        self._refresh_package_list()

        lines: List[str] = []
        if created:
            lines.append("作成されたパッケージ:")
            lines.extend(f"  - {c}" for c in created)
        if skipped:
            if lines:
                lines.append("")
            lines.append("既に存在していたためスキップされたパッケージ:")
            lines.extend(f"  - {s}" for s in skipped)
        if not lines:
            lines.append("新しく作成されたパッケージはありません。")

        QMessageBox.information(self, "Rez Environment Manager", "\n".join(lines))

    # --------------------------------------------------------
    # 手動追加
    # --------------------------------------------------------
    def _on_manual_add(self) -> None:
        """
        任意の exe を選択し、名前とバージョンを指定して package.py を生成する。
        """
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "実行ファイルを選択",
            "",
            "実行ファイル (*.exe);;すべてのファイル (*)",
        )
        if not file_path:
            return

        exe_path = Path(file_path)
        if not exe_path.is_file():
            QMessageBox.warning(self, "Rez Environment Manager", "選択されたファイルが存在しません。")
            return

        # デフォルト候補
        default_name = exe_path.stem.lower()
        default_version = _extract_version_from_name(exe_path.parent.name)

        # パッケージ名入力
        name, ok = QInputDialog.getText(
            self,
            "パッケージ名",
            "rez パッケージ名:",
            text=default_name,
        )
        if not ok or not name.strip():
            return
        name = name.strip()

        # バージョン入力
        version, ok = QInputDialog.getText(
            self,
            "バージョン",
            "バージョン:",
            text=default_version,
        )
        if not ok or not version.strip():
            return
        version = version.strip()

        pkg_dir = _ensure_package_dir(name, version)
        pkg_file = pkg_dir / "package.py"
        if pkg_file.is_file():
            reply = QMessageBox.question(
                self,
                "Rez Environment Manager",
                f"既に {name}-{version} の package.py が存在します。\n上書きしますか？",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No,
            )
            if reply != QMessageBox.Yes:
                return

        body = _generate_generic_package(name, version, exe_path.parent, exe_path)
        pkg_file.write_text(body, encoding="utf-8")

        self._refresh_package_list()
        QMessageBox.information(
            self,
            "Rez Environment Manager",
            f"{name}-{version} のパッケージを作成しました。",
        )

    # --------------------------------------------------------
    # 実体チェック
    # --------------------------------------------------------
    @staticmethod
    def _read_tool_path_from_package(pkg_file: Path) -> Optional[Path]:
        """
        package.py 冒頭の TOOL_PATH コメントから実体パスを取得する。
        """
        try:
            text = pkg_file.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            return None

        m = re.search(r"^#\s*TOOL_PATH=(.+)$", text, flags=re.MULTILINE)
        if not m:
            return None
        path_str = m.group(1).strip()
        if not path_str:
            return None
        return Path(path_str)

    def _on_validate_packages(self) -> None:
        """
        各 package.py 内に記録した TOOL_PATH の存在を確認し、
        不足しているものを一覧表示、リスト上でも印を付ける。
        """
        missing: List[str] = []
        for i in range(self._list.count()):
            item = self._list.item(i)
            folder_str = item.data(_USER_ROLE_DIR)
            if not folder_str:
                continue
            folder = Path(folder_str)
            pkg_file = folder / "package.py"
            tool_path = self._read_tool_path_from_package(pkg_file)

            base_label = item.data(_USER_ROLE_LABEL) or item.text()
            item.setText(base_label)
            item.setData(_USER_ROLE_MISSING, False)

            if not tool_path or not tool_path.exists():
                item.setText(f"{base_label}  (missing)")
                item.setData(_USER_ROLE_MISSING, True)
                missing.append(base_label)

        if missing:
            msg = "実体が見つからないパッケージ:\n" + "\n".join(f"  - {m}" for m in missing)
            QMessageBox.warning(self, "Rez Environment Manager", msg)
        else:
            QMessageBox.information(self, "Rez Environment Manager", "すべてのパッケージについて実体が確認できました。")

    # --------------------------------------------------------
    # 削除
    # --------------------------------------------------------
    def _on_delete_selected(self) -> None:
        """
        選択中のパッケージディレクトリを削除する。
        """
        item: Optional[QListWidgetItem] = self._list.currentItem()
        if not item:
            QMessageBox.warning(self, "Rez Environment Manager", "パッケージが選択されていません。")
            return

        folder_str = item.data(_USER_ROLE_DIR)
        if not folder_str:
            return
        folder = Path(folder_str)
        if not folder.is_dir():
            QMessageBox.warning(self, "Rez Environment Manager", "フォルダが存在しません。")
            return

        reply = QMessageBox.question(
            self,
            "Rez Environment Manager",
            f"次のフォルダを削除しますか？\n{folder}",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if reply != QMessageBox.Yes:
            return

        try:
            shutil.rmtree(folder)
        except Exception as exc:
            QMessageBox.critical(self, "Rez Environment Manager", f"削除に失敗しました:\n{exc}")
            return

        self._refresh_package_list()

    # --------------------------------------------------------
    # フォルダを開く
    # --------------------------------------------------------
    def _on_open_selected(self) -> None:
        """
        選択中のパッケージフォルダを OS のファイルブラウザで開く。
        """
        item: Optional[QListWidgetItem] = self._list.currentItem()
        if not item:
            QMessageBox.warning(self, "Rez Environment Manager", "パッケージが選択されていません。")
            return

        folder_str = item.data(_USER_ROLE_DIR)
        if not folder_str:
            return

        path = Path(folder_str)
        if not path.is_dir():
            QMessageBox.warning(self, "Rez Environment Manager", "フォルダが存在しません。")
            return

        QDesktopServices.openUrl(QUrl.fromLocalFile(str(path)))


# ------------------------------------------------------------
# MenuRegistrar から呼ばれるエントリポイント
# ------------------------------------------------------------

def register_menus(registrar: MenuRegistrar) -> None:
    """
    menu_ext から呼ばれるメニュー登録関数。

    Setting メニュー配下に
        'Rez Environment Manager...'
    を追加し、RezEnvManagerDialog をモーダルで起動する。
    """

    def open_dialog() -> None:
        parent = getattr(registrar, "_window", None)
        dlg = RezEnvManagerDialog(parent=parent)
        dlg.exec_()

    registrar.add_action(
        "Setting",
        "Rez Environment Manager...",
        open_dialog,
    )
