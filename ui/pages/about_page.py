from PySide6.QtWidgets import QWidget, QVBoxLayout, QFrame, QLabel, QScrollArea
from PySide6.QtCore import Qt
from ui.styles import (
    STYLES, apply_theme_to_page, get_theme_colors,
    get_page_header_style, get_page_hint_style, get_scroll_area_stylesheet,
)
from ui.ui_scale import UiScale


class AboutPage(QWidget):
    """Страница о программе — описание возможностей и разделов."""

    def __init__(self, styles=None):
        super().__init__()
        self.styles = styles or STYLES.get_styles()
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(*UiScale.page_margins())
        layout.setSpacing(UiScale.px(16))

        header = QLabel("О программе")
        header.setStyleSheet(get_page_header_style())
        self.header_label = header
        layout.addWidget(header)

        info_frame = QFrame()
        info_frame.setStyleSheet(self.styles['frame'])
        info_layout = QVBoxLayout(info_frame)
        info_layout.setSpacing(10)

        c = get_theme_colors()
        self.name_label = QLabel("VK Archiver CHIBGU")
        self.name_label.setStyleSheet(
            f"color: {c['text']}; font-size: 24px; font-weight: bold;"
        )
        info_layout.addWidget(self.name_label)

        self.version_label = QLabel("Версия: 1.0.0")
        self.version_label.setStyleSheet(
            f"color: {c['text_muted']}; font-size: 14px;"
        )
        info_layout.addWidget(self.version_label)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setStyleSheet(get_scroll_area_stylesheet())

        desc_host = QWidget()
        desc_layout = QVBoxLayout(desc_host)
        desc_layout.setContentsMargins(0, 0, 0, 0)

        self.desc_label = QLabel(self._about_text())
        self.desc_label.setWordWrap(True)
        self.desc_label.setTextFormat(Qt.TextFormat.PlainText)
        self.desc_label.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
        self.desc_label.setStyleSheet(
            f"color: {c['text']}; font-size: 13px; line-height: 1.55; padding-top: 4px;"
        )
        desc_layout.addWidget(self.desc_label)
        scroll.setWidget(desc_host)
        info_layout.addWidget(scroll, 1)

        journal_hint = QLabel(
            "Журнал ошибок, резервная копия, целостность и фоновые задачи — "
            "«Настройки приложения»."
        )
        journal_hint.setWordWrap(True)
        journal_hint.setProperty('uiRole', 'hint')
        journal_hint.setStyleSheet(get_page_hint_style())
        self.journal_hint = journal_hint
        info_layout.addWidget(journal_hint)

        layout.addWidget(info_frame, 1)

        self._theme_custom_labels = [
            self.name_label, self.version_label, self.desc_label, journal_hint,
        ]

    @staticmethod
    def _about_text() -> str:
        return """
Назначение
──────────
Десктопное приложение для сбора, хранения и анализа публикаций официального сообщества
ВКонтакте. Ведётся локальный архив: тексты постов, вложения (фото, видео, клипы),
метрики вовлечённости (лайки, комментарии, репосты), автоматические и ручные теги,
привязка материалов к преподавателям и кафедрам ЧИБГУ.

Данные: база SQLite (Archive.db) и папка Exports_data (медиа по дате публикации:
год / месяц / день). Поиск — полнотекстовый (FTS5) по тексту, тегам и подписи источника.

ОСНОВНОЕ (боковое меню)
───────────────────────
• Сводка — краткая статистика архива (всего постов, за месяц, ВК и ручные, файлы,
  топ-кафедра, посты без автора / тегов / вложений), быстрые переходы в другие разделы.

• Загрузка контента — выгрузка из ВК за выбранный период (час, день, неделя, месяц,
  год, весь архив или свой диапазон дат); ручное добавление материалов не из соцсетей
  (файлы, текст, теги, подпись источника). Перед добавлением проверяются похожие посты.

• Поиск в архиве — расширенный поиск с фильтрами (дата, тег, кафедра, автор, тип медиа,
  источник), сортировка, постраничный вывод (по 100 записей), превью фото и видео
  (миниатюры *_thumb.jpg), сохранённые пресеты фильтров, открытие поста в хранилище,
  редактирование из таблицы.

• Статистика постов — топ публикаций за период по лайкам, комментариям, репостам
  или сводной популярности; экспорт в CSV и Excel.

• Хранилище постов — просмотр карточек с текстом и вложениями, встроенный просмотр
  фото и видео, подгрузка списка порциями, кнопка «Статистика из ВК» для обновления
  лайков и комментариев без повторной загрузки файлов, редактирование поста,
  выгрузка вложений на рабочий стол во временную папку.

• Преподаватели в постах — сводка активности авторов за период, экспорт списка
  публикаций с ФИО и хэштегами в Word (.docx).

СПРАВОЧНИКИ
───────────
• Кафедры и преподаватели — справочник с хэштегами, синхронизация состава с сайта
  университета, ручное редактирование, отчёт Word по кафедре за выбранный период.

• Тэги — словарь тегирования (персональные, групповые, событийные): фраза в тексте
  поста → хэштег; иерархия «родительский тег» для подтипов событий. Кнопка
  «Пересчитать теги архива» — применить словарь ко всем постам (через очередь задач).

• Управление постами — таблица всех постов с фильтрами, цветовая «актуальность» по дате,
  редактирование, массовое удаление, смена подписи источника для ручных материалов.

НАСТРОЙКИ
─────────
• Основные — токен ВК и ссылка на сообщество (.env), светлая / тёмная тема,
  планировщик догрузки и метрик (пока приложение открыто: при старте и раз в час),
  ярлык на рабочем столе.

• Архив — резервная копия (Archive.db + Exports_data в ZIP), проверка целостности
  (файлы на диске ↔ записи в базе), исправление битых и лишних вложений.

• Загрузка (доп.) — размер пакета wall.get и параметры cookies для yt-dlp
  (если не скачиваются видео и клипы); обычно менять не требуется.

• Журнал — последние строки errors.log, очистка, открытие папки logs.

• Фоновые задачи — единая очередь: загрузка из ВК, пересчёт тегов, синхронизация
  кафедр, проверка целостности; журнал операций и отмена текущей задачи.

Планировщик (порядок шагов)
───────────────────────────
При включённом планировщике: синхронизация кафедр и преподавателей → проверка словаря
тегов → при необходимости пересчёт тегов → догрузка из ВК. Без справочников новые посты
не получат авторов и хэштеги из словаря. Обновление лайков вручную — в хранилище.

Технологии: Python, PySide6 (Qt), SQLite, vk_api, yt-dlp, Natasha / pymorphy3,
openpyxl, python-docx.
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
            f"color: {c['text']}; font-size: 13px; line-height: 1.55; padding-top: 4px;"
        )
