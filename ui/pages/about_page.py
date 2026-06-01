from PySide6.QtWidgets import QWidget, QVBoxLayout, QFrame, QLabel
from PySide6.QtCore import Qt
from ui.styles import STYLES, apply_theme_to_page, get_theme_colors


class AboutPage(QWidget):
    """Страница о программе"""

    def __init__(self, styles=None):
        super().__init__()
        self.styles = styles or STYLES.get_styles()
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(30, 30, 30, 30)
        layout.setSpacing(20)

        header = QLabel("О программе")
        text_color = '#000000' if STYLES._theme == 'light' else '#ffffff'
        header.setStyleSheet(
            f"color: {text_color}; font-size: 22px; font-weight: bold; padding: 10px 0;"
        )
        self.header_label = header
        layout.addWidget(header)

        info_frame = QFrame()
        info_frame.setStyleSheet(self.styles['frame'])
        info_layout = QVBoxLayout(info_frame)
        info_layout.setSpacing(12)

        self.name_label = QLabel("VK Archiver CHIBGU")
        self.name_label.setStyleSheet(
            f"color: {text_color}; font-size: 24px; font-weight: bold;"
        )
        info_layout.addWidget(self.name_label)

        self.version_label = QLabel("Версия: 1.0.0")
        self.version_label.setStyleSheet("color: #888888; font-size: 14px;")
        info_layout.addWidget(self.version_label)

        self.desc_label = QLabel(self._about_text())
        self.desc_label.setWordWrap(True)
        self.desc_label.setTextFormat(Qt.TextFormat.PlainText)
        self.desc_label.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
        desc_color = '#666666' if STYLES._theme == 'light' else '#d4d4d4'
        self.desc_label.setStyleSheet(
            f"color: {desc_color}; font-size: 13px; line-height: 1.55; padding-top: 4px;"
        )
        info_layout.addWidget(self.desc_label)
        info_layout.addStretch()

        layout.addWidget(info_frame)
        layout.addStretch()

        self._theme_custom_labels = [self.name_label, self.version_label, self.desc_label]

    @staticmethod
    def _about_text() -> str:
        return """
Назначение
──────────
Десктопное приложение для сбора, хранения и анализа публикаций официального сообщества
ВКонтакте. Программа предназначена для ведения локального архива: тексты постов, вложения,
метрики вовлечённости и связь материалов с преподавателями и кафедрами университета.

Загрузка контента
─────────────────
• Подключение к группе ВК по токену API и ссылке на сообщество.
• Выбор периода выгрузки: час, день, неделя, месяц, год, весь доступный архив
  или произвольный диапазон дат.
• Скачивание фотографий в формате JPEG — файлы сохраняются как есть, без сжатия
  и без перекодирования в другие форматы.
• Скачивание видео и клипов: прямая загрузка или получение потока через yt-dlp
  в исходном качестве, без последующей оптимизации и без перекодирования в приложении.
• Для отдельных роликов сохраняются превью (JPEG) рядом с файлом видео.
• Медиа складываются в каталог Exports_data с разбивкой по дате публикации (год / месяц / день).

Архив и поиск
─────────────
• Все посты индексируются в базе SQLite (Archive.db): текст, теги, дата, ссылки,
  лайки, комментарии, репосты.
• Полнотекстовый поиск по архиву (механизм FTS5) — по тексту поста и по хештегам.
• Автоматическое формирование тегов из текста публикации (морфологический разбор
  через Natasha или pymorphy3).

Хранилище постов
────────────────
• Просмотр загруженных публикаций в виде карточек с текстом и вложениями.
• Поддержка нескольких фото и видео в одном посте, прокрутка внутри карточки.
• Воспроизведение видео во встроенном плеере.
• Подгрузка списка порциями и обновление статистики (лайки, комментарии, репосты)
  из ВКонтакте без повторной загрузки файлов.

Кафедры и преподаватели
───────────────────────
• Справочник кафедр и сотрудников с уникальными хештегами для разметки контента.
• Синхронизация с сайта университета: список кафедр, состав кафедр, отдельно —
  преподаватели колледжа; ход операции отображается в логе на экране.
• Ручное добавление, изменение хештега и удаление записей.
• В базе сохраняется привязка поста к автору (преподавателю) и кафедре, если она
  определена при обработке публикации.

Статистика и отчёты
───────────────────
• Раздел «Статистика постов»: топ публикаций за период по лайкам, комментариям,
  репостам или сводному показателю популярности; экспорт в CSV и Excel с таблицами
  и диаграммами.
• Раздел «Преподаватели в постах»: сводка активности авторов за выбранный период,
  экспорт списка публикаций с ФИО и хештегами в документ Word (.docx).

Настройки и интерфейс
─────────────────────
• Хранение токена, ссылки на группу и темы оформления в файле .env.
• Светлая, тёмная тема или автоматический выбор по настройкам операционной системы.
• Проверка доступа к API ВКонтакте из окна настроек.
• Создание ярлыка на рабочем столе (Windows).

Технологии: Python, PySide6 (Qt), SQLite, vk_api, yt-dlp, openpyxl, python-docx.
        """.strip()

    def update_styles(self, styles):
        self.styles = styles
        apply_theme_to_page(self, styles)
        c = get_theme_colors()
        self.name_label.setStyleSheet(
            f"color: {c['text']}; font-size: 24px; font-weight: bold;"
        )
        self.version_label.setStyleSheet(f"color: {c['text_muted']}; font-size: 14px;")
        self.desc_label.setStyleSheet(
            f"color: {c['text_muted']}; font-size: 13px; line-height: 1.55; padding-top: 4px;"
        )
