from __future__ import annotations

from dataclasses import dataclass
from typing import Dict

from PySide6.QtCore import Qt, QTimer, Slot
from PySide6.QtGui import QIntValidator
from PySide6.QtWidgets import QWidget, QGridLayout, QFrame, QMessageBox
from qfluentwidgets import (
    FluentWindow,
    FluentIcon as FIF,
    NavigationItemPosition,
    TitleLabel,
    LineEdit,
    PushButton,
    InfoBar,
    InfoBarPosition,
    SubtitleLabel,
    CardWidget,
    BodyLabel,
    ScrollArea,
    SmoothScroll,
    SmoothMode,
)

from .config import AppConfig
from .memory import ProcessMemory


@dataclass
class FieldWidgets:
    label: BodyLabel
    edit: LineEdit
    write_button: PushButton
    lock_button: PushButton


class MainWindow(FluentWindow):
    def __init__(self, config: AppConfig, memory: ProcessMemory) -> None:
        super().__init__()
        self.config = config
        self.memory = memory
        self._field_widgets: Dict[str, FieldWidgets] = {}
        self._name_edits: Dict[str, LineEdit] = {}

        self.setWindowTitle("100%鲜橙汁修改器")
        self.resize(980, 700)

        self._build_ui()

        self.timer = QTimer(self)
        self.timer.setInterval(self.config.poll_interval_ms)
        self.timer.timeout.connect(self.refresh_values)
        self.timer.start()
        self._attempt_attach(silent=True)

    def _build_ui(self) -> None:
        page = QWidget(self)
        page.setObjectName("home")
        page.setStyleSheet("background: transparent;")
        layout = QGridLayout(page)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setHorizontalSpacing(16)
        layout.setVerticalSpacing(12)

        title = TitleLabel("100%鲜橙汁专用修改器", page)
        subtitle = SubtitleLabel("仅用于单人模式，不对封号负责", page)
        layout.addWidget(title, 0, 0, 1, 4)
        layout.addWidget(subtitle, 1, 0, 1, 4)

        self.status_label = BodyLabel("状态：未附加", page)
        self.status_label.setStyleSheet("color: #cf000f;")
        layout.addWidget(self.status_label, 2, 0, 1, 2)

        header_card = CardWidget(page)
        header_layout = QGridLayout(header_card)
        header_layout.setContentsMargins(8, 8, 8, 8)
        header_layout.setHorizontalSpacing(8)
        header_layout.setColumnStretch(0, 1)
        header_layout.setColumnStretch(1, 1)

        self.round_label = BodyLabel("当前回合：第0回合", header_card)
        header_layout.addWidget(self.round_label, 0, 0, 1, 2)
        self.refresh_button = PushButton("刷新", header_card)
        self.refresh_button.clicked.connect(self.refresh_values)
        header_layout.addWidget(self.refresh_button, 0, 2, alignment=Qt.AlignRight | Qt.AlignBottom)

        self.kill_button = PushButton("关闭", header_card)
        self.kill_button.clicked.connect(self._confirm_kill_process)
        header_layout.addWidget(self.kill_button, 0, 3, alignment=Qt.AlignRight | Qt.AlignBottom)

        layout.addWidget(header_card, 3, 0, 1, 4)

        common_card = CardWidget(page)
        common_layout = QGridLayout(common_card)
        common_layout.setContentsMargins(16, 16, 16, 16)
        common_layout.setHorizontalSpacing(8)
        common_layout.setVerticalSpacing(8)

        common_layout.addWidget(BodyLabel("公共功能", common_card), 0, 0, 1, 4)
        self._add_field_row(common_layout, 1, "common_star", "星星数量")
        self._add_field_row(common_layout, 2, "common_orange", "橘子数量")

        layout.addWidget(common_card, 4, 0, 1, 4)

        match_card = CardWidget(page)
        match_layout = QGridLayout(match_card)
        match_layout.setContentsMargins(16, 16, 16, 16)
        match_layout.setHorizontalSpacing(8)
        match_layout.setVerticalSpacing(8)

        match_layout.addWidget(BodyLabel("对局修改", match_card), 0, 0, 1, 4)
        self._add_field_row(match_layout, 1, "dice", "骰子点数")
        self._add_field_row(match_layout, 2, "round_count", "回合数量")
        self._add_field_row(match_layout, 3, "attack_dice_left", "攻击骰子-左")
        self._add_field_row(match_layout, 4, "attack_dice_right", "攻击骰子-右")

        layout.addWidget(match_card, 5, 0, 1, 4)

        players_card = CardWidget(page)
        players_layout = QGridLayout(players_card)
        players_layout.setContentsMargins(16, 16, 16, 16)
        players_layout.setHorizontalSpacing(12)
        players_layout.setVerticalSpacing(12)

        players_layout.addWidget(BodyLabel("玩家修改", players_card), 0, 0, 1, 2)

        self._add_player_card(players_layout, 1, 0, 1)
        self._add_player_card(players_layout, 1, 1, 2)
        self._add_player_card(players_layout, 2, 0, 3)
        self._add_player_card(players_layout, 2, 1, 4)

        layout.addWidget(players_card, 6, 0, 1, 4)

        tips_card = CardWidget(page)
        tips_layout = QGridLayout(tips_card)
        tips_layout.setContentsMargins(16, 16, 16, 16)
        tips_layout.setHorizontalSpacing(8)
        tips_layout.setVerticalSpacing(8)

        tips_layout.addWidget(BodyLabel("提示", tips_card), 0, 0)
        tips_layout.addWidget(BodyLabel("本修改器仅支持 100orange.exe，偏移配置在 config.json 中。", tips_card), 0, 1, 1, 3)

        layout.addWidget(tips_card, 7, 0, 1, 4)

        scroll_area = SmoothScrollArea(self)
        scroll_area.setObjectName("home")
        scroll_area.setFrameShape(QFrame.NoFrame)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        scroll_area.setStyleSheet(
            "QScrollArea { background: transparent; }"
            "QScrollBar:vertical { width: 8px; margin: 4px 2px 4px 2px; }"
            "QScrollBar::handle:vertical { background: rgba(120,120,120,0.35); border-radius: 4px; }"
            "QScrollBar::handle:vertical:hover { background: rgba(120,120,120,0.55); }"
            "QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }"
            "QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical { background: transparent; }"
        )
        scroll_area.setWidgetResizable(True)
        scroll_area.setWidget(page)
        self.addSubInterface(scroll_area, FIF.GAME, "修改器")

        settings_page = self._build_settings_ui()
        settings_scroll = SmoothScrollArea(self)
        settings_scroll.setObjectName("settings")
        settings_scroll.setFrameShape(QFrame.NoFrame)
        settings_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        settings_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        settings_scroll.setStyleSheet(
            "QScrollArea { background: transparent; }"
            "QScrollBar:vertical { width: 8px; margin: 4px 2px 4px 2px; }"
            "QScrollBar::handle:vertical { background: rgba(120,120,120,0.35); border-radius: 4px; }"
            "QScrollBar::handle:vertical:hover { background: rgba(120,120,120,0.55); }"
            "QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }"
            "QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical { background: transparent; }"
        )
        settings_scroll.setWidgetResizable(True)
        settings_scroll.setWidget(settings_page)
        self.addSubInterface(
            settings_scroll,
            FIF.SETTING,
            "设置",
            position=NavigationItemPosition.BOTTOM,
        )

    def _build_settings_ui(self) -> QWidget:
        page = QWidget(self)
        page.setStyleSheet("background: transparent;")
        page.setObjectName("settings")
        layout = QGridLayout(page)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setHorizontalSpacing(16)
        layout.setVerticalSpacing(12)

        title = TitleLabel("设置", page)
        subtitle = SubtitleLabel("刷新频率与配置路径", page)
        layout.addWidget(title, 0, 0, 1, 4)
        layout.addWidget(subtitle, 1, 0, 1, 4)

        settings_card = CardWidget(page)
        settings_layout = QGridLayout(settings_card)
        settings_layout.setContentsMargins(16, 16, 16, 16)
        settings_layout.setHorizontalSpacing(8)
        settings_layout.setVerticalSpacing(8)

        settings_layout.addWidget(BodyLabel("刷新间隔(ms)", settings_card), 0, 0)
        self.poll_interval_edit = LineEdit(settings_card)
        self.poll_interval_edit.setValidator(QIntValidator(50, 5000, self))
        self.poll_interval_edit.setText(str(self.config.poll_interval_ms))
        settings_layout.addWidget(self.poll_interval_edit, 0, 1)

        self.save_settings_button = PushButton("保存设置", settings_card)
        self.save_settings_button.clicked.connect(self._save_settings)
        settings_layout.addWidget(self.save_settings_button, 0, 2)

        settings_layout.addWidget(BodyLabel("配置文件", settings_card), 1, 0)
        settings_layout.addWidget(BodyLabel(str(self.config_path()), settings_card), 1, 1, 1, 2)

        settings_layout.addWidget(BodyLabel("作者", settings_card), 2, 0)
        settings_layout.addWidget(BodyLabel("localhosts-A", settings_card), 2, 1, 1, 2)

        layout.addWidget(settings_card, 2, 0, 1, 4)

        return page

    def _attempt_attach(self, silent: bool) -> None:
        if self.memory.attached:
            return
        self.memory.process_name = self.config.process_name
        self.memory.module_name = self.config.module_name
        try:
            self.memory.attach()
            self.status_label.setText("状态：已检测到游戏")
            self.status_label.setStyleSheet("color: #2d7d46;")
            if not silent:
                InfoBar.success("成功", "进程附加成功", parent=self, position=InfoBarPosition.TOP)
        except Exception:
            self.status_label.setText("状态：等待游戏启动")
            self.status_label.setStyleSheet("color: #cf000f;")

    def _add_field_row(self, layout: QGridLayout, row: int, key: str, label: str) -> None:
        label_widget = BodyLabel(label, self)
        edit = LineEdit(self)
        edit.setValidator(QIntValidator(0, 2 ** 31 - 1, self))
        edit.setText("0")
        write_button = PushButton("写入", self)
        write_button.clicked.connect(lambda: self.write_field_value(key))
        lock_button = PushButton("锁定", self)
        lock_button.setCheckable(True)
        lock_button.setChecked(False)
        lock_button.clicked.connect(lambda checked: self._toggle_lock_state(checked, lock_button))

        if not self._is_key_configured(key):
            edit.clear()
            edit.setPlaceholderText("未配置")
            edit.setReadOnly(True)
            write_button.setEnabled(False)
            lock_button.setEnabled(False)

        layout.addWidget(label_widget, row, 0)
        layout.addWidget(edit, row, 1)
        layout.addWidget(write_button, row, 2)
        layout.addWidget(lock_button, row, 3)

        self._field_widgets[key] = FieldWidgets(label_widget, edit, write_button, lock_button)

    def _toggle_lock_state(self, checked: bool, button: PushButton) -> None:
        button.setText("已锁定" if checked else "锁定")

    def _add_player_card(self, layout: QGridLayout, row: int, col: int, player_index: int) -> None:
        card = CardWidget(self)
        card_layout = QGridLayout(card)
        card_layout.setContentsMargins(12, 12, 12, 12)
        card_layout.setHorizontalSpacing(8)
        card_layout.setVerticalSpacing(6)

        name_key = f"player{player_index}_name"
        name_label = BodyLabel(f"玩家 {player_index}", card)
        name_edit = LineEdit(card)
        name_edit.setReadOnly(True)
        name_edit.setPlaceholderText("读取中..." if self._is_name_configured(name_key) else "未配置")
        if not self._is_name_configured(name_key):
            name_edit.setReadOnly(True)
        self._name_edits[name_key] = name_edit

        card_layout.addWidget(name_label, 0, 0)
        card_layout.addWidget(name_edit, 0, 1, 1, 3)

        self._add_field_row(card_layout, 1, f"player{player_index}_hp", "HP")
        self._add_field_row(card_layout, 2, f"player{player_index}_win", "胜利次数")
        self._add_field_row(card_layout, 3, f"player{player_index}_star", "星数")

        layout.addWidget(card, row, col)

    @Slot()
    def toggle_attach(self) -> None:
        self._attempt_attach(silent=False)

    @Slot()
    def refresh_values(self) -> None:
        if not self.memory.attached:
            self._attempt_attach(silent=True)
            if not self.memory.attached:
                return

        for key, widgets in self._field_widgets.items():
            try:
                address = self._resolve_address(key)
                if widgets.lock_button.isChecked():
                    lock_text = widgets.edit.text().strip()
                    if lock_text:
                        value = int(lock_text)
                        self._write_value(key, address, value)
                value = self.memory.read_int(address)
                self._set_input_placeholder(widgets.edit, str(value))
                if key == "round_count":
                    self.round_label.setText(f"当前回合：第{value}回合")
            except Exception:
                widgets.edit.setText("0")
                self.memory.detach()
                self.status_label.setText("状态：等待游戏启动")
                self.status_label.setStyleSheet("color: #cf000f;")
                return

        self._refresh_player_names()

    def write_field_value(self, key: str) -> None:
        if not self.memory.attached:
            InfoBar.warning("提示", "请先附加进程", parent=self, position=InfoBarPosition.TOP)
            return
        widgets = self._field_widgets[key]
        try:
            text = widgets.edit.text().strip()
            if not text:
                InfoBar.warning("提示", "请输入要写入的数值", parent=self, position=InfoBarPosition.TOP)
                return
            value = int(text)
            address = self._resolve_address(key)
            self._write_value(key, address, value)
            InfoBar.success("成功", "写入完成", parent=self, position=InfoBarPosition.TOP)
        except Exception as exc:  # noqa: BLE001
            InfoBar.error("错误", f"写入失败：{exc}", parent=self, position=InfoBarPosition.TOP)

    def _set_input_placeholder(self, edit: LineEdit, value_text: str) -> None:
        if edit.hasFocus() and edit.text().strip():
            return
        edit.setText("")
        edit.setPlaceholderText(value_text)

    def _resolve_address(self, key: str) -> int:
        resolved_key = self._resolve_key(key)
        if resolved_key.startswith("player") and resolved_key.endswith("_hp"):
            derived = self._resolve_hp_chain(resolved_key)
            if derived is not None:
                return self.memory.get_address_from_chain(
                    self.config.base_offset,
                    derived,
                )
        if resolved_key.startswith("player") and resolved_key.endswith("_win"):
            derived = self._resolve_win_chain(resolved_key)
            if derived is not None:
                return self.memory.get_address_from_chain(
                    self.config.base_offset,
                    derived,
                )
        if resolved_key.startswith("player") and resolved_key.endswith("_star"):
            derived = self._resolve_star_chain(resolved_key)
            if derived is not None:
                return self.memory.get_address_from_chain(
                    self.config.base_offset,
                    derived,
                )
        if resolved_key in self.config.module_fields:
            return self.memory.get_module_address(self.config.module_fields[resolved_key])
        if resolved_key in self.config.pointer_chains:
            return self.memory.get_address_from_chain(
                self.config.base_offset,
                self.config.pointer_chains[resolved_key],
            )
        return self.memory.get_address(
            self.config.base_offset,
            self.config.fields.get(resolved_key, 0),
        )

    def _write_value(self, key: str, address: int, value: int) -> None:
        resolved_key = self._resolve_key(key)
        self.memory.write_int(address, value)
        if resolved_key in self.config.double_write_fields:
            for offset in self.config.double_write_fields[resolved_key]:
                extra_address = self.memory.get_address(self.config.base_offset, offset)
                if extra_address != address:
                    self.memory.write_int(extra_address, value)
        if resolved_key.endswith("_star"):
            star_chain = self._resolve_star_double_chain(resolved_key)
            if star_chain is not None:
                extra_address = self.memory.get_address_from_chain(
                    self.config.base_offset,
                    star_chain,
                )
                if extra_address != address:
                    self.memory.write_int(extra_address, value)
        elif resolved_key in self.config.double_write:
            extra_address = self.memory.get_address_from_chain(
                self.config.base_offset,
                self.config.double_write[resolved_key],
            )
            if extra_address != address:
                self.memory.write_int(extra_address, value)

    def _refresh_player_names(self) -> None:
        for key, edit in self._name_edits.items():
            cfg = self._resolve_name_config(key)
            if not cfg:
                edit.setText("")
                continue
            try:
                chain = list(cfg.get("chain", []))
                start = int(cfg.get("start", 0))
                end = int(cfg.get("end", 0))
                start_addr = self.memory.get_address_from_chain(
                    self.config.base_offset,
                    chain + [start],
                )
                end_addr = self.memory.get_address_from_chain(
                    self.config.base_offset,
                    chain + [end],
                )
                size = max(0, end_addr - start_addr + 1)
                if size <= 0:
                    edit.setText("")
                    continue
                raw = self.memory.read_bytes(start_addr, size)
                cleaned = raw.split(b"\x00", 1)[0]
                try:
                    name = cleaned.decode("utf-8")
                except UnicodeDecodeError:
                    name = cleaned.decode("shift_jis", errors="replace")
                edit.setText(name.strip())
            except Exception:
                edit.setText("")

    def _resolve_key(self, key: str) -> str:
        if key in self.config.pointer_chains or key in self.config.fields:
            return key
        if key == "player1_hp" and "player_hp" in self.config.pointer_chains:
            return "player_hp"
        if key == "player1_win" and "player_win" in self.config.pointer_chains:
            return "player_win"
        if key == "player1_star" and "player_star" in self.config.pointer_chains:
            return "player_star"
        return key

    def _is_key_configured(self, key: str) -> bool:
        resolved_key = self._resolve_key(key)
        return (
            resolved_key in self.config.module_fields
            or resolved_key in self.config.pointer_chains
            or resolved_key in self.config.fields
            or resolved_key in self.config.double_write
            or resolved_key in self.config.double_write_fields
            or self._resolve_hp_chain(resolved_key) is not None
            or self._resolve_win_chain(resolved_key) is not None
            or self._resolve_star_chain(resolved_key) is not None
        )

    def _resolve_hp_chain(self, key: str) -> list[int] | None:
        if key == "player1_hp":
            return self.config.pointer_chains.get("player_hp")
        if key in {"player2_hp", "player3_hp", "player4_hp"}:
            base_chain = self.config.pointer_chains.get("player_hp")
            if not base_chain or not self.config.hp_stride:
                return None
            index = int(key.replace("player", "").replace("_hp", ""))
            stride = self.config.hp_stride * (index - 1)
            derived = list(base_chain)
            derived[-1] = derived[-1] + stride
            return derived
        return None

    def _resolve_win_chain(self, key: str) -> list[int] | None:
        if key == "player1_win":
            return self.config.pointer_chains.get("player_win")
        if key in {"player2_win", "player3_win", "player4_win"}:
            base_chain = self.config.pointer_chains.get("player_win")
            if not base_chain or not self.config.win_stride:
                return None
            index = int(key.replace("player", "").replace("_win", ""))
            stride = self.config.win_stride * (index - 1)
            derived = list(base_chain)
            derived[-1] = derived[-1] + stride
            return derived
        return None

    def _resolve_star_chain(self, key: str) -> list[int] | None:
        if key == "player1_star":
            return self.config.pointer_chains.get("player_star")
        if key == "player2_star":
            return self.config.pointer_chains.get("player2_star")
        if key in {"player3_star", "player4_star"}:
            base_chain = self.config.pointer_chains.get("player2_star")
            if not base_chain or not self.config.star_stride:
                return None
            index = int(key.replace("player", "").replace("_star", ""))
            stride = self.config.star_stride * (index - 2)
            derived = list(base_chain)
            derived[-1] = derived[-1] + stride
            return derived
        return None

    def _resolve_star_double_chain(self, key: str) -> list[int] | None:
        if key == "player1_star":
            return self.config.double_write.get("player_star")
        if key == "player2_star":
            return self.config.double_write.get("player2_star")
        if key in {"player3_star", "player4_star"}:
            base_chain = self.config.double_write.get("player2_star")
            if not base_chain or not self.config.star_stride:
                return None
            index = int(key.replace("player", "").replace("_star", ""))
            stride = self.config.star_stride * (index - 2)
            derived = list(base_chain)
            derived[-1] = derived[-1] + stride
            return derived
        return None

    def _resolve_name_config(self, key: str) -> Dict[str, object] | None:
        if key in self.config.name_ranges:
            return self.config.name_ranges[key]
        if key == "player1_name" and "player_name" in self.config.name_ranges:
            return self.config.name_ranges["player_name"]
        return None

    def _is_name_configured(self, key: str) -> bool:
        return self._resolve_name_config(key) is not None

    def _save_settings(self) -> None:
        try:
            interval = int(self.poll_interval_edit.text())
            self.config.poll_interval_ms = interval
            self.timer.setInterval(interval)
            self.config.save()
            InfoBar.success("成功", "设置已保存", parent=self, position=InfoBarPosition.TOP)
        except Exception as exc:  # noqa: BLE001
            InfoBar.error("错误", f"保存失败：{exc}", parent=self, position=InfoBarPosition.TOP)

    def config_path(self) -> str:
        from .config import CONFIG_PATH

        return str(CONFIG_PATH)

    def _confirm_kill_process(self) -> None:
        if not self.memory.attached:
            InfoBar.warning("提示", "未检测到游戏进程", parent=self, position=InfoBarPosition.TOP)
            return
        reply = QMessageBox.question(
            self,
            "确认关闭",
            "确定要关闭游戏进程吗？",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if reply == QMessageBox.Yes:
            self._kill_process()

    def _kill_process(self) -> None:
        try:
            self.memory.terminate()
            self.status_label.setText("状态：等待游戏启动")
            self.status_label.setStyleSheet("color: #cf000f;")
            InfoBar.success("成功", "已关闭游戏进程", parent=self, position=InfoBarPosition.TOP)
        except Exception as exc:  # noqa: BLE001
            InfoBar.error("错误", f"关闭失败：{exc}", parent=self, position=InfoBarPosition.TOP)


class SmoothScrollArea(ScrollArea):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._smooth_scroll = SmoothScroll(self, Qt.Vertical, True)
        self._smooth_scroll.setSmoothMode(SmoothMode.COSINE)

    def wheelEvent(self, event):
        self._smooth_scroll.wheelEvent(event)
