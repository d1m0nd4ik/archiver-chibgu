from PySide6.QtWidgets import QWidget, QVBoxLayout, QFrame, QLabel, QGridLayout, QLineEdit, QPushButton, QMessageBox
from PySide6.QtGui import QFont
from PySide6.QtCore import Qt
from core.config_manager import save_env_settings, get_effective_theme
from core.url_parser import VKUrlParser
from core.desktop_shortcut import create_desktop_shortcut
from core.logging_config import logger
from ui.styles import STYLES, apply_theme_to_page, get_theme_colors
import vk_api

class SettingsPage(QWidget):
    """Страница настроек"""

    def __init__(self, current_theme='system', saved_token='', saved_group_link='', styles=None):
        super().__init__()
        self.saved_token = saved_token or ''
        self.saved_group_link = saved_group_link or ''
        self.styles = styles or STYLES.get_styles()
        self.selected_theme = get_effective_theme(current_theme)
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(30, 30, 30, 30)
        layout.setSpacing(20)

        header = QLabel("Настройки приложения")
        header.setStyleSheet(self._get_header_style())
        self.header_label = header
        layout.addWidget(header)

        self.settings_frame = QFrame()
        self.settings_frame.setStyleSheet(self.styles['frame'])
        settings_layout = QVBoxLayout(self.settings_frame)
        settings_layout.setSpacing(20)

        # VK API
        vk_section = QFrame()
        vk_section.setStyleSheet("background-color: transparent;")
        vk_layout = QGridLayout(vk_section)
        vk_layout.setSpacing(15)

        self.vk_title = QLabel("🔑 Подключение к ВКонтакте")
        self.vk_title.setStyleSheet(self._get_label_style())
        vk_layout.addWidget(self.vk_title, 0, 0, 1, 2)

        vk_layout.addWidget(QLabel("Токен доступа:"), 1, 0)
        self.token_input = QLineEdit()
        self.token_input.setPlaceholderText("Вставьте токен с vkhost.github.io")
        self.token_input.setText(self.saved_token)
        self.token_input.setStyleSheet(self.styles['input'])
        self.token_input.setMinimumHeight(40)
        vk_layout.addWidget(self.token_input, 1, 1)

        vk_layout.addWidget(QLabel("Ссылка на сообщество:"), 2, 0)
        self.group_input = QLineEdit()
        self.group_input.setPlaceholderText("https://vk.ru/имя_группы, club123 или 236813059")
        self.group_input.setText(self.saved_group_link)
        self.group_input.setStyleSheet(self.styles['input'])
        self.group_input.setMinimumHeight(40)
        vk_layout.addWidget(self.group_input, 2, 1)

        vk_hint = QLabel(
            "Сообщество: полная ссылка (vk.com / vk.ru), короткое имя (apng_archiver) "
            "или числовой ID. При сохранении короткое имя можно проверить через VK API."
        )
        vk_hint.setWordWrap(True)
        vk_hint.setStyleSheet(self._get_info_style())
        vk_layout.addWidget(vk_hint, 3, 0, 1, 2)

        settings_layout.addWidget(vk_section)

        self.line_vk = QFrame()
        self.line_vk.setFrameShape(QFrame.HLine)
        self.line_vk.setFixedHeight(1)
        settings_layout.addWidget(self.line_vk)

        # ТЕМА ПРИЛОЖЕНИЯ
        theme_section = QFrame()
        theme_section.setStyleSheet("background-color: transparent;")
        theme_layout = QGridLayout(theme_section)
        theme_layout.setSpacing(15)

        self.theme_label = QLabel("🎨 Тема оформления:")
        self.theme_label.setStyleSheet(self._get_label_style())
        theme_layout.addWidget(self.theme_label, 0, 0)

        # Кнопка переключения темы (вместо ComboBox)
        self.theme_toggle_btn = QPushButton("Тёмная тема")
        self.theme_toggle_btn.setCheckable(True)
        self.theme_toggle_btn.setMinimumHeight(45)
        self.theme_toggle_btn.clicked.connect(self.on_theme_toggle)
        self._update_theme_button_style()
        theme_layout.addWidget(self.theme_toggle_btn, 0, 1)

        self.theme_info_label = QLabel()
        self._update_theme_info_label()
        self.theme_info_label.setStyleSheet(self._get_info_style())
        theme_layout.addWidget(self.theme_info_label, 1, 0, 1, 2)

        settings_layout.addWidget(theme_section)

        # Разделитель
        self.line_theme = QFrame()
        self.line_theme.setFrameShape(QFrame.HLine)
        self.line_theme.setFixedHeight(1)
        settings_layout.addWidget(self.line_theme)

        settings_layout.addStretch()

        self.shortcut_btn = QPushButton("Создать или обновить ярлык на рабочем столе")
        self.shortcut_btn.setStyleSheet(self.styles['button_secondary'])
        self.shortcut_btn.setMinimumHeight(44)
        self.shortcut_btn.clicked.connect(self.on_create_shortcut_clicked)
        settings_layout.addWidget(self.shortcut_btn)

        self.save_btn = QPushButton("Сохранить настройки")
        self.save_btn.setStyleSheet(self.styles['button'])
        self.save_btn.setMinimumHeight(50)
        self.save_btn.setFont(QFont("Arial", 12, QFont.Bold))
        self.save_btn.clicked.connect(self.on_save_clicked)
        settings_layout.addWidget(self.save_btn)

        self._secondary_buttons = [self.shortcut_btn]

        layout.addWidget(self.settings_frame)
        self.refresh_theme_sections()

    def _get_header_style(self):
        c = get_theme_colors()
        return f"color: {c['text']}; font-size: 22px; font-weight: bold; padding: 10px 0;"

    def _get_label_style(self):
        c = get_theme_colors()
        return f"color: {c['text']}; font-size: 14px; font-weight: 600;"

    def _get_info_style(self):
        c = get_theme_colors()
        return f"color: {c['text_muted']}; font-size: 13px; font-style: italic;"

    def refresh_theme_sections(self):
        c = get_theme_colors()
        sep = f"background-color: {c['separator']}; max-height: 1px; border: none;"
        self.line_vk.setStyleSheet(sep)
        self.line_theme.setStyleSheet(sep)
        self.settings_frame.setStyleSheet(self.styles['frame'])
        self.vk_title.setStyleSheet(self._get_label_style())
        self.theme_label.setStyleSheet(self._get_label_style())

    def _update_theme_info_label(self):
        applied = STYLES._theme
        selected_name = 'Светлая' if self.selected_theme == 'light' else 'Тёмная'
        if self.selected_theme == applied:
            self.theme_info_label.setText(f"→ Активна: {selected_name} тема")
        else:
            self.theme_info_label.setText(
                f"→ Выбрана: {selected_name} тема (применится после «Сохранить настройки»)"
            )

    def _update_theme_button_style(self):
        if self.selected_theme == 'light':
            self.theme_toggle_btn.setText("Светлая тема")
            self.theme_toggle_btn.setChecked(True)
            self.theme_toggle_btn.setStyleSheet("""
                QPushButton {
                    padding: 10px 20px;
                    border-radius: 8px;
                    background-color: #ffd700;
                    color: #000000;
                    border: 2px solid #ffa500;
                    font-weight: bold;
                    font-size: 14px;
                }
                QPushButton:hover {
                    background-color: #ffed4e;
                    border: 2px solid #ff8c00;
                }
            """)
        else:
            self.theme_toggle_btn.setText("Тёмная тема")
            self.theme_toggle_btn.setChecked(False)
            self.theme_toggle_btn.setStyleSheet("""
                QPushButton {
                    padding: 10px 20px;
                    border-radius: 8px;
                    background-color: #2b2b2b;
                    color: #ffffff;
                    border: 2px solid #555555;
                    font-weight: bold;
                    font-size: 14px;
                }
                QPushButton:hover {
                    background-color: #3a3a3a;
                    border: 2px solid #777777;
                }
            """)

    def on_create_shortcut_clicked(self):
        try:
            path = create_desktop_shortcut()
            QMessageBox.information(
                self,
                "Ярлык обновлён",
                f"Ярлык «VK Media Archiver Pro» на рабочем столе обновлён (иконка и путь запуска):\n\n{path}",
            )
        except OSError as e:
            QMessageBox.warning(self, "Недоступно", str(e))
        except Exception as e:
            logger.error("Create shortcut: %s", e, exc_info=True)
            QMessageBox.critical(self, "Ошибка", f"Не удалось создать ярлык:\n\n{e}")

    def on_theme_toggle(self):
        self.selected_theme = 'light' if self.selected_theme == 'dark' else 'dark'
        self._update_theme_button_style()
        self._update_theme_info_label()

    def on_save_clicked(self):
        """Сохранение настроек"""
        token = self.token_input.text().strip()
        group_link = self.group_input.text().strip()
        theme = self.selected_theme

        if not token or not group_link:
            QMessageBox.warning(
                self,
                "Не заполнены поля",
                "Укажите токен доступа и ссылку (или ID) сообщества ВКонтакте.",
            )
            return

        group_note = ""
        if not VKUrlParser._numeric_group_id(group_link):
            try:
                from core.vk_token import ensure_token_valid

                session = vk_api.VkApi(token=token)
                ensure_token_valid(session)
                resolved = VKUrlParser.resolve_group_id(group_link, session)
                if resolved is not None:
                    group_note = f"\nСообщество распознано, ID для API: {resolved}"
                else:
                    QMessageBox.warning(
                        self,
                        "Сообщество не найдено",
                        VKUrlParser.format_resolve_hint(group_link),
                    )
                    return
            except ValueError as e:
                QMessageBox.warning(self, "Сообщество не найдено", str(e))
                return
            except Exception as e:
                logger.warning("Проверка сообщества при сохранении: %s", e)
                QMessageBox.warning(
                    self,
                    "Не удалось проверить сообщество",
                    f"{e}\n\nНастройки не сохранены.",
                )
                return

        save_env_settings(token, group_link, '', theme)

        main_win = self.window()
        if hasattr(main_win, 'apply_theme'):
            main_win.apply_theme(theme)

        self._update_theme_info_label()

        QMessageBox.information(
            self,
            "Настройки сохранены",
            f"Токен и сообщество сохранены в .env{group_note}\n"
            f"Тема: {'Светлая' if theme == 'light' else 'Тёмная'} — применена ко всему приложению.",
        )

    def get_theme(self):
        return self.selected_theme

    def update_styles(self, styles):
        self.styles = styles
        apply_theme_to_page(self, styles)
        self.refresh_theme_sections()
        self.header_label.setStyleSheet(self._get_header_style())
        self.theme_info_label.setStyleSheet(self._get_info_style())
        self.shortcut_btn.setStyleSheet(self.styles['button_secondary'])
        self._update_theme_button_style()
        self._update_theme_info_label()


