import datetime
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QFrame, QLabel, QGridLayout, QPushButton, QProgressBar,
    QDateEdit, QComboBox, QDateTimeEdit, QTextEdit,
    QHBoxLayout, QListWidget, QFileDialog, QScrollArea,
)
from PySide6.QtGui import QFont
from PySide6.QtCore import Qt

from core.database import Database
from core.employee_tagger import normalize_hashtag
from core.manual_sources import load_manual_source_labels
from core.nlp_processor import dedupe_hashtags
from core.post_tags import parse_manual_tags
from ui.styles import (
    STYLES, apply_theme_to_page, get_combo_stylesheet,
    get_page_header_style, get_page_subtitle_style, get_page_hint_style,
    get_section_title_style, get_scroll_area_stylesheet,
)
from ui.form_layout import FormGrid


class DownloadPage(QWidget):
    """Загрузка из ВК и ручное добавление материалов в архив."""

    def __init__(self, styles=None):
        super().__init__()
        self.styles = styles or STYLES.get_styles()
        self._selected_files: list[str] = []
        self._form_labels: list[QLabel] = []
        self.init_ui()

    def init_ui(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setStyleSheet(get_scroll_area_stylesheet())
        outer.addWidget(scroll)

        content = QWidget()
        scroll.setWidget(content)
        layout = QVBoxLayout(content)
        layout.setContentsMargins(30, 30, 30, 30)
        layout.setSpacing(20)

        header = QLabel("Загрузка контента")
        header.setStyleSheet(get_page_header_style())
        self.header_label = header
        layout.addWidget(header)

        subtitle = QLabel(
            "Архив вуза: посты из ВКонтакте и материалы, добавленные вручную "
            "(фото с мероприятий, статьи, файлы не из соцсетей)."
        )
        subtitle.setWordWrap(True)
        subtitle.setProperty('uiRole', 'subtitle')
        subtitle.setStyleSheet(get_page_subtitle_style())
        self.subtitle_label = subtitle
        layout.addWidget(subtitle)

        vk_title = QLabel("Из ВКонтакте")
        vk_title.setProperty('uiRole', 'section')
        vk_title.setStyleSheet(get_section_title_style())
        self.vk_title = vk_title
        layout.addWidget(vk_title)

        self.form_frame = QFrame()
        self.form_frame.setStyleSheet(self.styles['frame'])
        self._vk_form_layout = QGridLayout(self.form_frame)
        form_layout = self._vk_form_layout
        FormGrid.setup_two_column(form_layout, wide_labels=True)

        period_lbl = FormGrid.make_label("Период загрузки:", wide=True)
        self._form_labels.append(period_lbl)
        form_layout.addWidget(period_lbl, 0, 0)
        self.period_combo = QComboBox()
        self.period_combo.addItems([
            "Час", "День", "Неделя", "Месяц", "Год", "Все время", "Свой диапазон"
        ])
        self.period_combo.setCurrentText("Все время")
        self.period_combo.currentTextChanged.connect(self.on_period_changed)
        self.period_combo.setStyleSheet(self.styles.get('combo', self.styles['input']))
        form_layout.addWidget(self.period_combo, 0, 1)

        start_lbl = FormGrid.make_label("Дата начала:", wide=True)
        self._form_labels.append(start_lbl)
        form_layout.addWidget(start_lbl, 1, 0)
        self.date_start = QDateEdit()
        self.date_start.setCalendarPopup(True)
        self.date_start.setDate(datetime.datetime.now() - datetime.timedelta(days=7))
        self.date_start.setStyleSheet(self.styles.get('date', self.styles['input']))
        self.date_start.setEnabled(False)
        form_layout.addWidget(self.date_start, 1, 1)

        end_lbl = FormGrid.make_label("Дата окончания:", wide=True)
        self._form_labels.append(end_lbl)
        form_layout.addWidget(end_lbl, 2, 0)
        self.date_end = QDateEdit()
        self.date_end.setCalendarPopup(True)
        self.date_end.setDate(datetime.datetime.now())
        self.date_end.setStyleSheet(self.styles.get('date', self.styles['input']))
        self.date_end.setEnabled(False)
        form_layout.addWidget(self.date_end, 2, 1)

        for w in (self.period_combo, self.date_start, self.date_end):
            FormGrid.fix_field(w, compact=False)
        FormGrid.sync_grid(form_layout, compact=False, labels=self._form_labels)

        layout.addWidget(self.form_frame)

        self.download_btn = QPushButton("Начать загрузку из ВК")
        self.download_btn.setStyleSheet(self.styles['button'])
        self.download_btn.setMinimumHeight(50)
        self.download_btn.setFont(QFont("Arial", 12, QFont.Bold))
        layout.addWidget(self.download_btn)

        self.progress_frame = QFrame()
        self.progress_frame.setStyleSheet(self.styles['frame'])
        progress_layout = QVBoxLayout(self.progress_frame)

        self.progress_label = QLabel("Прогресс:")
        self.progress_label.setStyleSheet(self.styles['label'])
        progress_layout.addWidget(self.progress_label)

        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setFormat("%p%")
        self.progress_bar.setStyleSheet(self.styles['progressbar'])
        progress_layout.addWidget(self.progress_bar)

        layout.addWidget(self.progress_frame)

        # --- Ручная загрузка ---
        manual_title = QLabel("Ручное добавление в архив")
        manual_title.setProperty('uiRole', 'section')
        manual_title.setStyleSheet(get_section_title_style())
        self.manual_title = manual_title
        layout.addWidget(manual_title)

        manual_hint = QLabel(
            "Фото юбилеев, праздников, материалы не из соцсетей. "
            "Подпись источника видна в хранилище. Управление постами — в «Справочники» → «Управление постами»."
        )
        manual_hint.setWordWrap(True)
        manual_hint.setProperty('uiRole', 'hint')
        manual_hint.setStyleSheet(get_page_hint_style())
        self.manual_hint = manual_hint
        layout.addWidget(manual_hint)

        self.manual_frame = QFrame()
        self.manual_frame.setStyleSheet(self.styles['frame'])
        self._manual_grid = QGridLayout(self.manual_frame)
        manual_grid = self._manual_grid
        FormGrid.setup_two_column(manual_grid, wide_labels=True)

        row = 0
        dt_lbl = FormGrid.make_label("Дата и время:", wide=True)
        self._form_labels.append(dt_lbl)
        manual_grid.addWidget(dt_lbl, row, 0)
        self.manual_datetime = QDateTimeEdit()
        self.manual_datetime.setCalendarPopup(True)
        self.manual_datetime.setDateTime(datetime.datetime.now())
        self.manual_datetime.setDisplayFormat("dd.MM.yyyy HH:mm")
        self.manual_datetime.setStyleSheet(
            self.styles.get('datetime', self.styles.get('date', self.styles['input']))
        )
        manual_grid.addWidget(self.manual_datetime, row, 1)

        row += 1
        src_lbl = FormGrid.make_label("Источник:", wide=True)
        self._form_labels.append(src_lbl)
        manual_grid.addWidget(src_lbl, row, 0)
        self.manual_source = QComboBox()
        self.manual_source.setProperty("comboAllowTyping", True)
        self.manual_source.setEditable(True)
        self.manual_source.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)
        self.manual_source.lineEdit().setPlaceholderText(
            "Выберите из списка или введите свой вариант…"
        )
        manual_grid.addWidget(self.manual_source, row, 1)
        self.reload_manual_sources()

        row += 1
        text_lbl = FormGrid.make_label("Текст поста:", wide=True, top=True)
        self._form_labels.append(text_lbl)
        manual_grid.addWidget(text_lbl, row, 0)
        self.manual_text = QTextEdit()
        self.manual_text.setPlaceholderText(
            "Описание, заголовок статьи, подписи к фото…"
        )
        self.manual_text.setStyleSheet(self.styles.get('textedit', self.styles['input']))
        self.manual_text.setMinimumHeight(100)
        self.manual_text.setMaximumHeight(160)
        manual_grid.addWidget(self.manual_text, row, 1)

        row += 1
        tags_lbl = FormGrid.make_label("Теги:", wide=True, top=True)
        self._form_labels.append(tags_lbl)
        manual_grid.addWidget(tags_lbl, row, 0)
        tags_col = QVBoxLayout()
        tags_col.setSpacing(6)
        picker_row = QHBoxLayout()
        self.manual_tag_picker = QComboBox()
        self.manual_tag_picker.setEditable(False)
        self.manual_tag_picker.setMinimumHeight(36)
        picker_row.addWidget(self.manual_tag_picker, 1)
        self.manual_add_tag_btn = QPushButton("Добавить из словаря")
        self.manual_add_tag_btn.setStyleSheet(self.styles['button_secondary'])
        self.manual_add_tag_btn.clicked.connect(self._add_manual_tag_from_picker)
        picker_row.addWidget(self.manual_add_tag_btn)
        tags_col.addLayout(picker_row)
        self.manual_tags_edit = QTextEdit()
        self.manual_tags_edit.setMaximumHeight(72)
        self.manual_tags_edit.setPlaceholderText(
            "#тег1 #тег2 — вручную или кнопкой; плюс автоподбор по тексту из словаря"
        )
        self.manual_tags_edit.setStyleSheet(self.styles.get('textedit', self.styles['input']))
        tags_col.addWidget(self.manual_tags_edit)
        manual_grid.addLayout(tags_col, row, 1)
        self.reload_manual_tag_picker()

        row += 1
        files_lbl = FormGrid.make_label("Файлы:", wide=True, top=True)
        self._form_labels.append(files_lbl)
        manual_grid.addWidget(files_lbl, row, 0)
        files_col = QVBoxLayout()
        files_btns = QHBoxLayout()
        self.manual_pick_btn = QPushButton("Выбрать файлы…")
        self.manual_pick_btn.setStyleSheet(self.styles['button_secondary'])
        self.manual_clear_files_btn = QPushButton("Очистить список")
        self.manual_clear_files_btn.setStyleSheet(self.styles['button_secondary'])
        files_btns.addWidget(self.manual_pick_btn)
        files_btns.addWidget(self.manual_clear_files_btn)
        files_btns.addStretch()
        files_col.addLayout(files_btns)
        self.manual_files_list = QListWidget()
        self.manual_files_list.setMinimumHeight(72)
        self.manual_files_list.setMaximumHeight(120)
        self.manual_files_list.setStyleSheet(self.styles.get('textedit', self.styles['input']))
        files_col.addWidget(self.manual_files_list)
        manual_grid.addLayout(files_col, row, 1)

        for w in (self.manual_datetime, self.manual_source):
            FormGrid.fix_field(w, compact=False)
        FormGrid.sync_grid(manual_grid, compact=False, labels=self._form_labels)

        layout.addWidget(self.manual_frame)

        self.manual_add_btn = QPushButton("Добавить в архив")
        self.manual_add_btn.setStyleSheet(self.styles['button'])
        self.manual_add_btn.setMinimumHeight(48)
        self.manual_add_btn.setFont(QFont("Arial", 11, QFont.Bold))
        layout.addWidget(self.manual_add_btn)

        self.manual_pick_btn.clicked.connect(self._pick_manual_files)
        self.manual_clear_files_btn.clicked.connect(self._clear_manual_files)

        layout.addStretch()

        self._primary_buttons = [self.download_btn, self.manual_add_btn]
        self._secondary_buttons = [
            self.manual_add_tag_btn, self.manual_pick_btn, self.manual_clear_files_btn,
        ]

    def on_period_changed(self, value):
        custom = value == "Свой диапазон"
        self.date_start.setEnabled(custom)
        self.date_end.setEnabled(custom)

    def get_date_range(self):
        period = self.period_combo.currentText()
        now = datetime.datetime.now()

        if period == "Свой диапазон":
            start = self.date_start.date().toPython()
            end = self.date_end.date().toPython() + datetime.timedelta(days=1)
            return start, end
        if period == "Час":
            return now - datetime.timedelta(hours=1), now
        if period == "День":
            return now - datetime.timedelta(days=1), now
        if period == "Неделя":
            return now - datetime.timedelta(days=7), now
        if period == "Месяц":
            return now - datetime.timedelta(days=30), now
        if period == "Год":
            return now - datetime.timedelta(days=365), now
        return datetime.datetime(2000, 1, 1), now

    def _pick_manual_files(self):
        paths, _ = QFileDialog.getOpenFileNames(
            self,
            "Выберите фото или видео",
            "",
            "Медиа (*.jpg *.jpeg *.png *.gif *.webp *.bmp *.mp4 *.mov *.avi *.mkv *.webm);;Все файлы (*.*)",
        )
        if not paths:
            return
        for p in paths:
            if p not in self._selected_files:
                self._selected_files.append(p)
                self.manual_files_list.addItem(p)

    def _clear_manual_files(self):
        self._selected_files.clear()
        self.manual_files_list.clear()

    def reload_manual_sources(self):
        current = self.manual_source.currentText().strip() if hasattr(self, 'manual_source') else ""
        self.manual_source.blockSignals(True)
        self.manual_source.clear()
        for label in load_manual_source_labels():
            self.manual_source.addItem(label)
        if current:
            if self.manual_source.findText(current) < 0:
                self.manual_source.addItem(current)
            self.manual_source.setCurrentText(current)
        self.manual_source.blockSignals(False)
        self.manual_source.setStyleSheet(
            self.styles.get('combo', get_combo_stylesheet())
        )

    def reload_manual_tag_picker(self):
        db = Database()
        try:
            tags = db.get_dictionary_hashtags(only_active=True)
        finally:
            db.close()
        self.manual_tag_picker.clear()
        for t in tags:
            self.manual_tag_picker.addItem(t, t)
        self.manual_tag_picker.setStyleSheet(
            self.styles.get('combo', get_combo_stylesheet())
        )

    def _add_manual_tag_from_picker(self):
        raw = self.manual_tag_picker.currentData() or self.manual_tag_picker.currentText().strip()
        if not raw:
            return
        tag = normalize_hashtag(str(raw))
        current = parse_manual_tags(self.manual_tags_edit.toPlainText())
        if tag not in current:
            current.append(tag)
        self.manual_tags_edit.setPlainText(' '.join(dedupe_hashtags(current)))

    def get_manual_import_data(self) -> dict:
        qdt = self.manual_datetime.dateTime()
        py_dt = datetime.datetime(
            qdt.date().year(), qdt.date().month(), qdt.date().day(),
            qdt.time().hour(), qdt.time().minute(),
        )
        return {
            'posted_at': py_dt,
            'text': self.manual_text.toPlainText(),
            'file_paths': list(self._selected_files),
            'source_label': self.manual_source.currentText().strip(),
            'manual_tags': self.manual_tags_edit.toPlainText(),
        }

    def clear_manual_form(self):
        self.manual_text.clear()
        self.manual_source.setCurrentText("")
        self.manual_tags_edit.clear()
        self.manual_datetime.setDateTime(datetime.datetime.now())
        self._clear_manual_files()

    def update_styles(self, styles):
        self.styles = styles
        apply_theme_to_page(self, styles)
        self.progress_label.setStyleSheet(self.styles.get('label', ''))
        self.manual_text.setStyleSheet(self.styles.get('textedit', self.styles['input']))
        self.manual_tags_edit.setStyleSheet(self.styles.get('textedit', self.styles['input']))
        self.manual_files_list.setStyleSheet(self.styles.get('textedit', self.styles['input']))
        self.reload_manual_sources()

    def reset_progress(self):
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setFormat("%p%")

    def set_progress(self, percent: int):
        self.progress_bar.setValue(max(0, min(100, percent)))
