from __future__ import annotations

from dataclasses import dataclass
from typing import Dict

from PySide6.QtCore import Qt, QTimer, Slot
from PySide6.QtGui import QIntValidator
from PySide6.QtWidgets import (
    QWidget,
    QGridLayout,
    QVBoxLayout,
    QFrame,
    QMessageBox,
    QSizePolicy,
)
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
    ComboBox,
    Dialog,
)

from .config import AppConfig
from .i18n import I18n
from .memory import ProcessMemory


@dataclass
class FieldWidgets:
    label_key: str
    label: BodyLabel
    edit: LineEdit
    write_button: PushButton
    lock_button: PushButton
    configured: bool


class MainWindow(FluentWindow):
    def __init__(self, config: AppConfig, memory: ProcessMemory) -> None:
        super().__init__()
        self.config = config
        self.memory = memory
        self.i18n = I18n.load(self.config.language)
        self._applying_language = False
        self._status_state: str = "detached"  # detached | waiting | detected
        self._current_round: int = 0

        self._field_widgets: Dict[str, FieldWidgets] = {}
        self._name_edits: Dict[str, LineEdit] = {}
        self._player_title_labels: Dict[int, BodyLabel] = {}

        # 页面上需要动态翻译刷新的控件引用
        self.home_title_label: TitleLabel | None = None
        self.home_subtitle_label: SubtitleLabel | None = None
        self.common_section_label: BodyLabel | None = None
        self.match_section_label: BodyLabel | None = None
        self.players_section_label: BodyLabel | None = None
        self.tips_section_label: BodyLabel | None = None
        self.tips_body_label: BodyLabel | None = None

        self.settings_title_label: TitleLabel | None = None
        self.settings_subtitle_label: SubtitleLabel | None = None
        self.settings_poll_label: BodyLabel | None = None
        self.settings_language_label: BodyLabel | None = None
        self.settings_config_file_label: BodyLabel | None = None
        self.settings_author_label: BodyLabel | None = None

        # 语言选项与下拉框索引的稳定映射（避免依赖 ComboBox.currentData 的兼容性问题）
        self._language_codes: list[str] = ["zh-CN", "en-US"]

        # 设置自动保存（防抖）
        self._settings_autosave_timer = QTimer(self)
        self._settings_autosave_timer.setSingleShot(True)
        self._settings_autosave_timer.setInterval(450)
        self._settings_autosave_timer.timeout.connect(self._auto_save_settings)
        self._last_saved_poll_interval_ms: int = int(self.config.poll_interval_ms)

        # 导航项引用（不同版本 addSubInterface 返回值可能不同，用于实时更新侧边栏文字）
        self._nav_home_item = None
        self._nav_settings_item = None

        self.setWindowTitle(self._t("app.window_title"))
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

        self.home_title_label = TitleLabel(self._t("home.title"), page)
        self.home_subtitle_label = SubtitleLabel(self._t("home.subtitle"), page)
        layout.addWidget(self.home_title_label, 0, 0, 1, 4)
        layout.addWidget(self.home_subtitle_label, 1, 0, 1, 4)

        self.status_label = BodyLabel(self._t("status.detached"), page)
        self.status_label.setStyleSheet("color: #cf000f;")
        layout.addWidget(self.status_label, 2, 0, 1, 2)

        header_card = CardWidget(page)
        header_layout = QGridLayout(header_card)
        # 与下方各 CardWidget 保持一致的内边距，避免顶部“当前回合”区域显得太贴边
        header_layout.setContentsMargins(16, 16, 16, 16)
        header_layout.setHorizontalSpacing(8)
        header_layout.setColumnStretch(0, 1)
        header_layout.setColumnStretch(1, 1)
        header_layout.setColumnStretch(2, 0)
        header_layout.setColumnStretch(3, 0)

        self.round_label = BodyLabel(self._t("round.label", round=0), header_card)
        header_layout.addWidget(self.round_label, 0, 0, 1, 2)
        self.refresh_button = PushButton(self._t("button.refresh"), header_card)
        self.refresh_button.clicked.connect(self.refresh_values)
        header_layout.addWidget(self.refresh_button, 0, 2, alignment=Qt.AlignRight | Qt.AlignBottom)

        self.kill_button = PushButton(self._t("button.close"), header_card)
        self.kill_button.clicked.connect(self._confirm_kill_process)
        header_layout.addWidget(self.kill_button, 0, 3, alignment=Qt.AlignRight | Qt.AlignBottom)

        layout.addWidget(header_card, 3, 0, 1, 4)

        common_card = CardWidget(page)
        common_layout = QGridLayout(common_card)
        common_layout.setContentsMargins(16, 16, 16, 16)
        common_layout.setHorizontalSpacing(8)
        common_layout.setVerticalSpacing(8)

        self.common_section_label = BodyLabel(self._t("section.common"), common_card)
        common_layout.addWidget(self.common_section_label, 0, 0, 1, 4)
        self._add_field_row(common_layout, 1, "common_star", "field.common_star")
        self._add_field_row(common_layout, 2, "common_orange", "field.common_orange")
        self._add_field_row(common_layout, 3, "common_chocolate", "field.common_chocolate")

        layout.addWidget(common_card, 4, 0, 1, 4)

        match_card = CardWidget(page)
        match_layout = QGridLayout(match_card)
        match_layout.setContentsMargins(16, 16, 16, 16)
        match_layout.setHorizontalSpacing(8)
        match_layout.setVerticalSpacing(8)

        self.match_section_label = BodyLabel(self._t("section.match"), match_card)
        match_layout.addWidget(self.match_section_label, 0, 0, 1, 4)
        self._add_field_row(match_layout, 1, "dice", "field.dice")
        self._add_field_row(match_layout, 2, "round_count", "field.round_count")
        self._add_field_row(match_layout, 3, "attack_dice_left", "field.attack_dice_left")
        self._add_field_row(match_layout, 4, "attack_dice_right", "field.attack_dice_right")

        layout.addWidget(match_card, 5, 0, 1, 4)

        players_card = CardWidget(page)
        players_layout = QGridLayout(players_card)
        players_layout.setContentsMargins(16, 16, 16, 16)
        players_layout.setHorizontalSpacing(12)
        players_layout.setVerticalSpacing(12)

        self.players_section_label = BodyLabel(self._t("section.players"), players_card)
        players_layout.addWidget(self.players_section_label, 0, 0, 1, 2)

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

        self.tips_section_label = BodyLabel(self._t("section.tips"), tips_card)
        self.tips_body_label = BodyLabel(self._t("tips.only_support"), tips_card)
        tips_layout.addWidget(self.tips_section_label, 0, 0)
        tips_layout.addWidget(self.tips_body_label, 0, 1, 1, 3)

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
        self._nav_home_item = self.addSubInterface(scroll_area, FIF.GAME, self._t("nav.home"))

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
        self._nav_settings_item = self.addSubInterface(
            settings_scroll,
            FIF.SETTING,
            self._t("nav.settings"),
            position=NavigationItemPosition.BOTTOM,
        )

    def _t(self, key: str, **kwargs) -> str:
        return self.i18n.t(key, **kwargs)

    def apply_language(self, language: str) -> None:
        """运行时切换语言并刷新界面文案。"""
        if self._applying_language:
            return
        self._applying_language = True
        try:
            self.i18n = I18n.load(language)

            # window
            self.setWindowTitle(self._t("app.window_title"))

            # navigation（不同版本 QFluentWidgets API 可能不同，尽量兼容）
            if not self._set_nav_item_text(self._nav_home_item, self._t("nav.home")):
                self._try_set_navigation_text("home", self._t("nav.home"))
            if not self._set_nav_item_text(self._nav_settings_item, self._t("nav.settings")):
                self._try_set_navigation_text("settings", self._t("nav.settings"))

            # home titles
            if self.home_title_label is not None:
                self.home_title_label.setText(self._t("home.title"))
            if self.home_subtitle_label is not None:
                self.home_subtitle_label.setText(self._t("home.subtitle"))

            # status label
            self._refresh_status_text()

            # round
            self.round_label.setText(self._t("round.label", round=self._current_round))

            # header buttons
            self.refresh_button.setText(self._t("button.refresh"))
            self.kill_button.setText(self._t("button.close"))

            # section headers
            if self.common_section_label is not None:
                self.common_section_label.setText(self._t("section.common"))
            if self.match_section_label is not None:
                self.match_section_label.setText(self._t("section.match"))
            if self.players_section_label is not None:
                self.players_section_label.setText(self._t("section.players"))
            if self.tips_section_label is not None:
                self.tips_section_label.setText(self._t("section.tips"))
            if self.tips_body_label is not None:
                self.tips_body_label.setText(self._t("tips.only_support"))

            # field rows
            for _, widgets in self._field_widgets.items():
                widgets.label.setText(self._t(widgets.label_key))
                widgets.write_button.setText(self._t("button.write"))
                widgets.lock_button.setText(
                    self._t("button.locked") if widgets.lock_button.isChecked() else self._t("button.lock")
                )
                if not widgets.configured:
                    widgets.edit.setPlaceholderText(self._t("placeholder.unconfigured"))

            # player card titles + name placeholders
            for index, label in self._player_title_labels.items():
                label.setText(self._t("player.title", index=index))
            for key, edit in self._name_edits.items():
                if self._is_name_configured(key):
                    edit.setPlaceholderText(self._t("placeholder.loading"))
                else:
                    edit.setPlaceholderText(self._t("placeholder.unconfigured"))

            # settings page
            if self.settings_title_label is not None:
                self.settings_title_label.setText(self._t("settings.title"))
            if self.settings_subtitle_label is not None:
                self.settings_subtitle_label.setText(self._t("settings.subtitle"))
            if self.settings_poll_label is not None:
                self.settings_poll_label.setText(self._t("settings.poll_interval"))
            if self.settings_language_label is not None:
                self.settings_language_label.setText(self._t("settings.language"))
            if self.settings_config_file_label is not None:
                self.settings_config_file_label.setText(self._t("settings.config_file"))
            if self.settings_author_label is not None:
                self.settings_author_label.setText(self._t("settings.author"))

            # 更新语言下拉显示文本（保持索引不变）
            if hasattr(self, "language_combo") and self.language_combo is not None:
                self.language_combo.blockSignals(True)
                try:
                    for idx in range(self.language_combo.count()):
                        # 基于稳定的索引映射更新显示文本
                        code = self._language_codes[idx] if idx < len(self._language_codes) else ""
                        if code == "zh-CN":
                            self.language_combo.setItemText(idx, self._t("settings.language.zh_cn"))
                        elif code == "en-US":
                            self.language_combo.setItemText(idx, self._t("settings.language.en_us"))

                    # 同步选中项到目标语言
                    normalized = (language or "zh-CN").strip().replace("_", "-")
                    if normalized in self._language_codes:
                        self.language_combo.setCurrentIndex(self._language_codes.index(normalized))
                finally:
                    # 防止更新过程中抛异常导致信号被永久屏蔽，出现“第一次能切换，后面无反应”
                    self.language_combo.blockSignals(False)
        finally:
            self._applying_language = False

    def _try_set_navigation_text(self, route_key: str, text: str) -> None:
        nav = getattr(self, "navigationInterface", None)
        if nav is None:
            return

        # 常见方法签名：setItemText(routeKey: str, text: str)
        for method_name in (
            "setItemText",
            "setItemTextByKey",
            "setItemTitle",
            "setItemName",
            "setText",
        ):
            method = getattr(nav, method_name, None)
            if method is None:
                continue
            try:
                method(route_key, text)
                try:
                    nav.update()
                except Exception:
                    pass
                return
            except TypeError:
                pass
            except Exception:
                return

            # 某些实现参数顺序可能是 (text, routeKey)
            try:
                method(text, route_key)
                try:
                    nav.update()
                except Exception:
                    pass
                return
            except Exception:
                pass

        # 兜底：有些版本需要先拿到 item
        for getter_name in ("item", "getItem", "itemByKey", "getItemByKey"):
            get_item = getattr(nav, getter_name, None)
            if get_item is None:
                continue
            try:
                item = get_item(route_key)
                if item is not None and hasattr(item, "setText"):
                    item.setText(text)
                    try:
                        nav.update()
                    except Exception:
                        pass
                    return
            except Exception:
                pass

        # 兜底：尝试遍历 nav 上的子对象，匹配 routeKey/key
        try:
            for child in nav.findChildren(QWidget):
                if hasattr(child, "routeKey") and str(getattr(child, "routeKey")) == route_key and hasattr(child, "setText"):
                    child.setText(text)
                    nav.update()
                    return
        except Exception:
            return

    def _set_nav_item_text(self, item, text: str) -> bool:
        """优先使用 addSubInterface 返回的导航项直接改文案。"""
        if item is None:
            return False
        for attr in ("setText", "setTitle", "setName"):
            setter = getattr(item, attr, None)
            if setter is None:
                continue
            try:
                setter(text)
                return True
            except Exception:
                return False
        return False

    def _set_status_state(self, state: str) -> None:
        self._status_state = state
        self._refresh_status_text()

    def _refresh_status_text(self) -> None:
        if not hasattr(self, "status_label") or self.status_label is None:
            return
        if self._status_state == "detected":
            self.status_label.setText(self._t("status.detected"))
        elif self._status_state == "waiting":
            self.status_label.setText(self._t("status.waiting"))
        else:
            self.status_label.setText(self._t("status.detached"))

    def _build_settings_ui(self) -> QWidget:
        page = QWidget(self)
        page.setStyleSheet("background: transparent;")
        page.setObjectName("settings")
        layout = QVBoxLayout(page)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(12)

        self.settings_title_label = TitleLabel(self._t("settings.title"), page)
        self.settings_subtitle_label = SubtitleLabel(self._t("settings.subtitle"), page)
        layout.addWidget(self.settings_title_label)
        layout.addWidget(self.settings_subtitle_label)

        settings_card = CardWidget(page)
        settings_card.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Maximum)
        settings_layout = QGridLayout(settings_card)
        settings_layout.setContentsMargins(16, 16, 16, 16)
        settings_layout.setHorizontalSpacing(8)
        settings_layout.setVerticalSpacing(8)
        settings_layout.setColumnStretch(0, 0)
        settings_layout.setColumnStretch(1, 1)
        settings_layout.setColumnStretch(2, 0)

        self.settings_poll_label = BodyLabel(self._t("settings.poll_interval"), settings_card)
        settings_layout.addWidget(self.settings_poll_label, 0, 0)
        self.poll_interval_edit = LineEdit(settings_card)
        self.poll_interval_edit.setValidator(QIntValidator(50, 5000, self))
        self.poll_interval_edit.setText(str(self.config.poll_interval_ms))
        self.poll_interval_edit.setMaximumWidth(160)
        # 自动保存：输入变化后防抖保存，失焦也会触发一次
        self.poll_interval_edit.textChanged.connect(self._schedule_settings_autosave)
        self.poll_interval_edit.editingFinished.connect(self._auto_save_settings)
        settings_layout.addWidget(self.poll_interval_edit, 0, 1)

        self.settings_language_label = BodyLabel(self._t("settings.language"), settings_card)
        settings_layout.addWidget(self.settings_language_label, 1, 0)
        self.language_combo = ComboBox(settings_card)
        self.language_combo.setMaximumWidth(200)
        # 只用显示文本 + 稳定索引映射，避免不同 ComboBox 实现对 userData 支持不一致
        self.language_combo.addItem(self._t("settings.language.zh_cn"))
        self.language_combo.addItem(self._t("settings.language.en_us"))

        current_lang = (self.config.language or "zh-CN").strip().replace("_", "-")
        if current_lang in self._language_codes:
            self.language_combo.setCurrentIndex(self._language_codes.index(current_lang))

        # 双保险：不同版本可能只发其中一种信号
        self.language_combo.currentIndexChanged.connect(self._on_language_changed)
        if hasattr(self.language_combo, "currentTextChanged"):
            self.language_combo.currentTextChanged.connect(self._on_language_changed)
        settings_layout.addWidget(self.language_combo, 1, 1)

        self.settings_config_file_label = BodyLabel(self._t("settings.config_file"), settings_card)
        settings_layout.addWidget(self.settings_config_file_label, 2, 0)
        config_path_label = BodyLabel(str(self.config_path()), settings_card)
        config_path_label.setWordWrap(True)
        config_path_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        config_path_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        settings_layout.addWidget(config_path_label, 2, 1, 1, 2)

        self.settings_author_label = BodyLabel(self._t("settings.author"), settings_card)
        settings_layout.addWidget(self.settings_author_label, 3, 0)
        settings_layout.addWidget(BodyLabel("localhosts-A", settings_card), 3, 1, 1, 2)

        layout.addWidget(settings_card)
        layout.addStretch(1)

        return page

    def _on_language_changed(self, *_args) -> None:
        if self._applying_language:
            return

        idx = int(self.language_combo.currentIndex())
        selected_lang = self._language_codes[idx] if 0 <= idx < len(self._language_codes) else "zh-CN"
        self.config.language = selected_lang
        self.apply_language(selected_lang)
        # 语言切换通常期望下次启动仍然生效，这里直接持久化（不弹提示，避免打扰）
        try:
            self.config.save()
        except Exception:
            pass

    def _schedule_settings_autosave(self) -> None:
        """设置变更后触发防抖自动保存。"""
        if self._applying_language:
            # 语言应用过程中会批量改动文本，避免误触
            return
        self._settings_autosave_timer.start()

    def _auto_save_settings(self) -> None:
        self._save_settings(silent=True)

    def _attempt_attach(self, silent: bool) -> None:
        if self.memory.attached:
            return
        self.memory.process_name = self.config.process_name
        self.memory.module_name = self.config.module_name
        try:
            self.memory.attach()
            self._set_status_state("detected")
            self.status_label.setStyleSheet("color: #2d7d46;")
            if not silent:
                InfoBar.success(
                    self._t("infobar.success"),
                    self._t("msg.attach_success"),
                    parent=self,
                    position=InfoBarPosition.TOP,
                )
        except Exception:
            self._set_status_state("waiting")
            self.status_label.setStyleSheet("color: #cf000f;")

    def _add_field_row(self, layout: QGridLayout, row: int, key: str, label_key: str) -> None:
        label_widget = BodyLabel(self._t(label_key), self)
        edit = LineEdit(self)
        edit.setValidator(QIntValidator(0, 2 ** 31 - 1, self))
        edit.setText("0")
        write_button = PushButton(self._t("button.write"), self)
        write_button.clicked.connect(lambda: self.write_field_value(key))
        lock_button = PushButton(self._t("button.lock"), self)
        lock_button.setCheckable(True)
        lock_button.setChecked(False)
        lock_button.clicked.connect(lambda checked: self._toggle_lock_state(checked, lock_button))

        configured = True

        if not self._is_key_configured(key):
            configured = False
            edit.clear()
            edit.setPlaceholderText(self._t("placeholder.unconfigured"))
            edit.setReadOnly(True)
            write_button.setEnabled(False)
            lock_button.setEnabled(False)

        layout.addWidget(label_widget, row, 0)
        layout.addWidget(edit, row, 1)
        layout.addWidget(write_button, row, 2)
        layout.addWidget(lock_button, row, 3)

        self._field_widgets[key] = FieldWidgets(label_key, label_widget, edit, write_button, lock_button, configured)

    def _toggle_lock_state(self, checked: bool, button: PushButton) -> None:
        button.setText(self._t("button.locked") if checked else self._t("button.lock"))

    def _add_player_card(self, layout: QGridLayout, row: int, col: int, player_index: int) -> None:
        card = CardWidget(self)
        card_layout = QGridLayout(card)
        card_layout.setContentsMargins(12, 12, 12, 12)
        card_layout.setHorizontalSpacing(8)
        card_layout.setVerticalSpacing(6)

        name_key = f"player{player_index}_name"
        name_label = BodyLabel(self._t("player.title", index=player_index), card)
        self._player_title_labels[player_index] = name_label
        name_edit = LineEdit(card)
        name_edit.setReadOnly(True)
        name_edit.setPlaceholderText(
            self._t("placeholder.loading")
            if self._is_name_configured(name_key)
            else self._t("placeholder.unconfigured")
        )
        if not self._is_name_configured(name_key):
            name_edit.setReadOnly(True)
        self._name_edits[name_key] = name_edit

        card_layout.addWidget(name_label, 0, 0)
        card_layout.addWidget(name_edit, 0, 1, 1, 3)

        self._add_field_row(card_layout, 1, f"player{player_index}_hp", "field.hp")
        self._add_field_row(card_layout, 2, f"player{player_index}_win", "field.win")
        self._add_field_row(card_layout, 3, f"player{player_index}_star", "field.star")

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

        had_error = False
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
                    self._current_round = int(value)
                    self.round_label.setText(self._t("round.label", round=self._current_round))
            except Exception:
                had_error = True
                # 未进入对局时，部分指针/偏移可能不可读；此处不要直接断开附加。
                # 仅当进程确实退出时才 detach。
                self._set_input_placeholder(widgets.edit, "0")

        if had_error and self.memory.attached and not self.memory.is_alive():
            self.memory.detach()
            self._set_status_state("waiting")
            self.status_label.setStyleSheet("color: #cf000f;")
            return

        self._refresh_player_names()

    def write_field_value(self, key: str) -> None:
        if not self.memory.attached:
            InfoBar.warning(
                self._t("infobar.warning"),
                self._t("msg.please_attach"),
                parent=self,
                position=InfoBarPosition.TOP,
            )
            return
        widgets = self._field_widgets[key]
        try:
            text = widgets.edit.text().strip()
            if not text:
                InfoBar.warning(
                    self._t("infobar.warning"),
                    self._t("msg.enter_value"),
                    parent=self,
                    position=InfoBarPosition.TOP,
                )
                return
            value = int(text)
            address = self._resolve_address(key)
            self._write_value(key, address, value)
            InfoBar.success(
                self._t("infobar.success"),
                self._t("msg.write_done"),
                parent=self,
                position=InfoBarPosition.TOP,
            )
        except Exception as exc:  # noqa: BLE001
            InfoBar.error(
                self._t("infobar.error"),
                self._t("msg.write_failed", error=exc),
                parent=self,
                position=InfoBarPosition.TOP,
            )

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

    def _save_settings(self, silent: bool = False) -> None:
        """保存设置。

        - silent=True：自动保存，不弹出提示，避免频繁打扰。
        - silent=False：手动保存，提示保存结果。
        """
        try:
            text = self.poll_interval_edit.text().strip()
            if not text:
                return
            interval = int(text)
            # validator 已限制范围，这里再兜底一次
            interval = max(50, min(5000, interval))

            idx = int(self.language_combo.currentIndex())
            language = self._language_codes[idx] if 0 <= idx < len(self._language_codes) else "zh-CN"

            changed = False
            if interval != int(self.config.poll_interval_ms):
                self.config.poll_interval_ms = interval
                self.timer.setInterval(interval)
                changed = True

            if language != (self.config.language or "zh-CN"):
                self.config.language = language
                changed = True

            # 避免频繁写盘：无变化则直接返回
            if not changed and interval == self._last_saved_poll_interval_ms:
                return

            self.config.save()
            self._last_saved_poll_interval_ms = interval

            if not silent:
                InfoBar.success(
                    self._t("infobar.success"),
                    self._t("msg.settings_saved"),
                    parent=self,
                    position=InfoBarPosition.TOP,
                )
        except Exception as exc:  # noqa: BLE001
            if not silent:
                InfoBar.error(
                    self._t("infobar.error"),
                    self._t("msg.settings_save_failed", error=exc),
                    parent=self,
                    position=InfoBarPosition.TOP,
                )

    def config_path(self) -> str:
        from .config import CONFIG_PATH

        return str(CONFIG_PATH)

    def _confirm_kill_process(self) -> None:
        if not self.memory.attached:
            InfoBar.warning(
                self._t("infobar.warning"),
                self._t("msg.no_process"),
                parent=self,
                position=InfoBarPosition.TOP,
            )
            return

        dialog = Dialog(self._t("dialog.kill_title"), self._t("dialog.kill_text"), self)
        # 部分版本暴露 yesButton/cancelButton，可选设置文案
        try:
            if hasattr(dialog, "yesButton"):
                dialog.yesButton.setText(self._t("button.yes"))
            if hasattr(dialog, "cancelButton"):
                dialog.cancelButton.setText(self._t("button.no"))
        except Exception:
            pass

        try:
            accepted = bool(dialog.exec())
        except Exception:
            # 兜底：若 Dialog API 变化，退回系统消息框
            reply = QMessageBox.question(
                self,
                self._t("dialog.kill_title"),
                self._t("dialog.kill_text"),
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No,
            )
            accepted = reply == QMessageBox.Yes

        if accepted:
            self._kill_process()

    def _kill_process(self) -> None:
        try:
            self.memory.terminate()
            self._set_status_state("waiting")
            self.status_label.setStyleSheet("color: #cf000f;")
            InfoBar.success(
                self._t("infobar.success"),
                self._t("msg.kill_done"),
                parent=self,
                position=InfoBarPosition.TOP,
            )
        except Exception as exc:  # noqa: BLE001
            InfoBar.error(
                self._t("infobar.error"),
                self._t("msg.kill_failed", error=exc),
                parent=self,
                position=InfoBarPosition.TOP,
            )


class SmoothScrollArea(ScrollArea):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._smooth_scroll = SmoothScroll(self, Qt.Vertical, True)
        self._smooth_scroll.setSmoothMode(SmoothMode.COSINE)

    def wheelEvent(self, event):
        self._smooth_scroll.wheelEvent(event)
