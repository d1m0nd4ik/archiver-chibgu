"""Диалог редактирования поста в архиве."""

from __future__ import annotations



import datetime



from PySide6.QtWidgets import (

    QDialog, QVBoxLayout, QGridLayout, QLabel, QLineEdit, QTextEdit,

    QDateTimeEdit, QCheckBox, QPushButton, QHBoxLayout, QMessageBox,

    QComboBox,

)

from PySide6.QtCore import Qt



from core.database import Database

from core.employee_tagger import EmployeeTagger, normalize_hashtag

from core.post_tags import build_post_tags, parse_manual_tags, resolve_author_and_department

from core.smart_tagger import SmartTagger

from core.nlp_processor import dedupe_hashtags

from ui.styles import STYLES, get_theme_colors, get_combo_stylesheet
from ui.form_layout import FormGrid





class PostEditDialog(QDialog):

    def __init__(self, post: dict, parent=None, styles=None):

        super().__init__(parent)

        self.styles = styles or STYLES.get_styles()

        self.post = post

        self._saved = False

        self.setWindowTitle(f"Редактирование поста #{post.get('original_post_id')}")

        self.setMinimumWidth(560)

        self._build_ui()

        self._load_data()



    def _build_ui(self):

        layout = QVBoxLayout(self)

        layout.setSpacing(12)

        self._form_grid = QGridLayout()
        grid = self._form_grid
        FormGrid.setup_two_column(grid, wide_labels=True)
        self._form_labels: list[QLabel] = []

        is_manual = (self.post.get('post_source') or 'vk') == 'manual'

        row = 0

        dt_lbl = FormGrid.make_label("Дата и время:", wide=True)
        self._form_labels.append(dt_lbl)
        grid.addWidget(dt_lbl, row, 0)

        self.datetime_edit = QDateTimeEdit()

        self.datetime_edit.setCalendarPopup(True)

        self.datetime_edit.setDisplayFormat("dd.MM.yyyy HH:mm")

        self.datetime_edit.setStyleSheet(
            self.styles.get('datetime', self.styles.get('date', self.styles['input']))
        )

        grid.addWidget(self.datetime_edit, row, 1)



        row += 1

        src_lbl = FormGrid.make_label("Источник:", wide=True)
        self._form_labels.append(src_lbl)
        grid.addWidget(src_lbl, row, 0)

        if is_manual:

            self.source_combo = QComboBox()

            self.source_combo.setEditable(False)

            self.source_combo.setStyleSheet(
                self.styles.get('combo', get_combo_stylesheet())
            )

            grid.addWidget(self.source_combo, row, 1)

        else:

            self.source_readonly = QLabel()

            self.source_readonly.setWordWrap(True)

            grid.addWidget(self.source_readonly, row, 1)



        row += 1

        txt_lbl = FormGrid.make_label("Текст:", wide=True, top=True)
        self._form_labels.append(txt_lbl)
        grid.addWidget(txt_lbl, row, 0)

        self.text_edit = QTextEdit()

        self.text_edit.setMinimumHeight(140)

        self.text_edit.setStyleSheet(self.styles.get('textedit', self.styles['input']))

        grid.addWidget(self.text_edit, row, 1)



        row += 1

        tags_lbl = FormGrid.make_label("Теги:", wide=True, top=True)
        self._form_labels.append(tags_lbl)
        grid.addWidget(tags_lbl, row, 0)

        tags_col = QVBoxLayout()



        self.retag_cb = QCheckBox("Пересчитать теги автоматически по словарю из текста")

        self.retag_cb.setChecked(False)

        tags_col.addWidget(self.retag_cb)



        picker_row = QHBoxLayout()

        self.tag_picker = QComboBox()

        self.tag_picker.setEditable(False)

        self.tag_picker.setMinimumWidth(200)

        self.tag_picker.setStyleSheet(self.styles.get('combo', get_combo_stylesheet()))

        picker_row.addWidget(self.tag_picker, 1)

        add_tag_btn = QPushButton("Добавить из словаря")

        add_tag_btn.setStyleSheet(self.styles['button_secondary'])

        add_tag_btn.clicked.connect(self._add_tag_from_picker)

        picker_row.addWidget(add_tag_btn)

        tags_col.addLayout(picker_row)



        self.tags_edit = QTextEdit()

        self.tags_edit.setMaximumHeight(80)

        self.tags_edit.setPlaceholderText("#тег1 #тег2 — ввод вручную или кнопкой выше")

        self.tags_edit.setStyleSheet(self.styles.get('textedit', self.styles['input']))

        tags_col.addWidget(self.tags_edit)



        self.retag_cb.toggled.connect(self._on_retag_toggle)

        grid.addLayout(tags_col, row, 1)

        from ui.combo_effects import setup_all_combos

        setup_all_combos(self)
        for w in (self.datetime_edit,):
            FormGrid.fix_field(w, compact=False)
        if hasattr(self, 'source_combo'):
            FormGrid.fix_field(self.source_combo, compact=False)
        FormGrid.fix_field(self.tag_picker, compact=False)
        FormGrid.sync_grid(grid, compact=False, labels=self._form_labels)

        layout.addLayout(grid)



        btns = QHBoxLayout()

        btns.addStretch()

        cancel_btn = QPushButton("Отмена")

        cancel_btn.setStyleSheet(self.styles['button_secondary'])

        cancel_btn.clicked.connect(self.reject)

        save_btn = QPushButton("Сохранить")

        save_btn.setStyleSheet(self.styles['button'])

        save_btn.clicked.connect(self._save)

        btns.addWidget(cancel_btn)

        btns.addWidget(save_btn)

        layout.addLayout(btns)



        c = get_theme_colors()

        self.setStyleSheet(f"background-color: {c['page_bg']}; color: {c['text']};")



    def _load_tag_picker(self):

        db = Database()

        try:

            tags = db.get_dictionary_hashtags(only_active=True)

        finally:

            db.close()

        self.tag_picker.clear()

        for t in tags:

            self.tag_picker.addItem(t, t)



    def _on_retag_toggle(self, checked: bool):

        self.tags_edit.setEnabled(not checked)

        self.tag_picker.setEnabled(not checked)



    def _add_tag_from_picker(self):

        raw = self.tag_picker.currentData() or self.tag_picker.currentText().strip()

        if not raw:

            return

        tag = normalize_hashtag(str(raw))

        current = parse_manual_tags(self.tags_edit.toPlainText())

        if tag not in current:

            current.append(tag)

        self.tags_edit.setPlainText(' '.join(dedupe_hashtags(current)))



    def _load_data(self):

        self._load_tag_picker()

        date_str = self.post.get('date') or ''

        try:

            dt = datetime.datetime.strptime(date_str, "%Y-%m-%d %H:%M")

            self.datetime_edit.setDateTime(dt)

        except ValueError:

            self.datetime_edit.setDateTime(datetime.datetime.now())



        if hasattr(self, 'source_combo'):

            current = (self.post.get('source_label') or 'Ручная загрузка').strip()

            from core.manual_sources import load_manual_source_labels

            labels = load_manual_source_labels(Database())

            if current and current not in labels:

                labels.insert(0, current)

            self.source_combo.clear()

            for lbl in labels:

                self.source_combo.addItem(lbl)

            idx = self.source_combo.findText(current)

            self.source_combo.setCurrentIndex(idx if idx >= 0 else 0)

        elif hasattr(self, 'source_readonly'):

            src = "ВКонтакте"

            if self.post.get('post_url'):

                src += f" — {self.post['post_url']}"

            self.source_readonly.setText(src)



        self.text_edit.setPlainText(self.post.get('text') or '')

        self.tags_edit.setPlainText(self.post.get('tags') or '')

        self._on_retag_toggle(self.retag_cb.isChecked())



    def _save(self):

        text = self.text_edit.toPlainText().strip()

        qdt = self.datetime_edit.dateTime()

        date_str = datetime.datetime(

            qdt.date().year(), qdt.date().month(), qdt.date().day(),

            qdt.time().hour(), qdt.time().minute(),

        ).strftime("%Y-%m-%d %H:%M")

        source_label = None

        if hasattr(self, 'source_combo'):

            source_label = self.source_combo.currentText().strip() or "Ручная загрузка"



        update_kwargs = dict(

            date=date_str,

            text=text,

            source_label=source_label,

        )



        db = Database()

        tagger = EmployeeTagger(db, refresh_on_init=False)



        if self.retag_cb.isChecked():

            smart = SmartTagger(db)

            smart.ensure_dictionary()

            tags, teacher_ht, dept_ht, emp_id, dept_id = build_post_tags(text, tagger, smart)

            update_kwargs['tags'] = tags

            update_kwargs.update(

                teacher_hashtag=teacher_ht,

                department_hashtag=dept_ht,

                author_employee_id=emp_id,

                author_department_id=dept_id,

            )

        else:

            manual_tags = parse_manual_tags(self.tags_edit.toPlainText())

            update_kwargs['tags'] = ' '.join(manual_tags)

            teacher_ht, dept_ht, emp_id, dept_id = resolve_author_and_department(

                tagger, text

            )

            for tag in manual_tags:

                emp = tagger.find_employee_by_hashtag(tag)

                if emp:

                    teacher_ht = emp.get('hashtag') or tag

                    emp_id = emp.get('id')

                    dept_id = emp.get('department_id')

                    dept_ht = emp.get('department_hashtag')

                    break

            update_kwargs.update(

                teacher_hashtag=teacher_ht,

                department_hashtag=dept_ht,

                author_employee_id=emp_id,

                author_department_id=dept_id,

            )



        ok = db.update_post(self.post['original_post_id'], **update_kwargs)

        db.close()



        if not ok:

            QMessageBox.warning(self, "Ошибка", "Не удалось сохранить изменения.")

            return

        self._saved = True

        self.accept()



    def was_saved(self) -> bool:

        return self._saved

