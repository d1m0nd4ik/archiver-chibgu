"""Панель очереди задач и журнала операций."""

from PySide6.QtWidgets import (

    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,

    QTextEdit, QProgressBar, QFrame, QSizePolicy,

)

from PySide6.QtCore import Qt



from core.task_queue import AppTaskQueue

from ui.styles import STYLES, get_theme_colors, get_task_queue_styles

from ui.ui_scale import UiScale





class TaskQueuePanel(QFrame):

    def __init__(self, styles=None, parent=None, *, embedded: bool = False):

        super().__init__(parent)

        self.styles = styles or STYLES.get_styles()

        self._embedded = embedded

        self._queue = AppTaskQueue.instance()

        self._expanded = True

        self._task_styles = get_task_queue_styles()

        self.setObjectName("TaskQueuePanel")

        self._build_ui()

        self._queue.log_line.connect(self._append_log)

        self._queue.progress_percent.connect(self._on_percent)

        self._queue.progress_message.connect(self._on_message)

        self._queue.busy_changed.connect(self._on_busy)

        self._queue.task_started.connect(self._on_task_started)

        self._apply_theme()



    def _build_ui(self):

        layout = QVBoxLayout(self)

        pad = UiScale.px(14) if self._embedded else UiScale.px(10)

        layout.setContentsMargins(pad, pad, pad, pad)

        layout.setSpacing(UiScale.px(10))



        header = QHBoxLayout()

        header.setSpacing(UiScale.px(10))

        self.title_label = QLabel("Очередь задач")

        header.addWidget(self.title_label)

        header.addStretch()

        self.status_label = QLabel("Готов")

        self.status_label.setAlignment(Qt.AlignCenter)

        header.addWidget(self.status_label)

        self.clear_log_btn = QPushButton("Очистить журнал")

        self.clear_log_btn.clicked.connect(self._clear_log)

        header.addWidget(self.clear_log_btn)

        if not self._embedded:

            self.toggle_btn = QPushButton("Свернуть")

            self.toggle_btn.clicked.connect(self._toggle_body)

            header.addWidget(self.toggle_btn)

        self.cancel_btn = QPushButton("Отменить задачу")

        self.cancel_btn.setEnabled(False)

        self.cancel_btn.clicked.connect(self._queue.cancel_current)

        header.addWidget(self.cancel_btn)

        layout.addLayout(header)



        self.body = QWidget()

        body_layout = QVBoxLayout(self.body)

        body_layout.setContentsMargins(0, 0, 0, 0)

        body_layout.setSpacing(UiScale.px(8))



        self.progress = QProgressBar()

        self.progress.setRange(0, 100)

        self.progress.setValue(0)

        self.progress.setTextVisible(True)

        self.progress.setFormat("%p%")

        body_layout.addWidget(self.progress)



        self.log_view = QTextEdit()

        self.log_view.setReadOnly(True)

        if self._embedded:

            self.log_view.setMinimumHeight(UiScale.px(240))

        else:

            self.log_view.setMaximumHeight(UiScale.px(120))

        self.log_view.setPlaceholderText("Журнал загрузок, пересчёта тегов и синхронизации…")

        body_layout.addWidget(self.log_view, 1)



        layout.addWidget(self.body, 1)

        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)



    def _apply_theme(self):

        self._task_styles = get_task_queue_styles()

        c = get_theme_colors()

        if self._embedded:

            self.setStyleSheet(self._task_styles['panel'])

        else:

            self.setStyleSheet(f"""

                QFrame#TaskQueuePanel {{

                    background-color: {c.get('panel_bg', c['content_bg'])};

                    border-top: 1px solid {c.get('border', '#444')};

                }}

            """)

        fs = UiScale.px(14)

        self.title_label.setStyleSheet(

            f"color: {c['text']}; font-weight: 600; font-size: {fs}px; "
            f"background: transparent; padding: 0;"

        )

        self.status_label.setStyleSheet(self._task_styles['status_ready'])

        self.clear_log_btn.setStyleSheet(self._task_styles['clear'])

        self._style_cancel_btn(self.cancel_btn.isEnabled())

        self.progress.setStyleSheet(self._task_styles['progress'])

        self.log_view.setStyleSheet(self._task_styles['log'])

        if hasattr(self, 'toggle_btn'):

            from ui.styles import get_compact_button_stylesheet

            self.toggle_btn.setStyleSheet(get_compact_button_stylesheet(False))

            self.toggle_btn.setFixedHeight(UiScale.px(34))



        for btn in (self.clear_log_btn, self.cancel_btn):

            btn.setFixedHeight(UiScale.px(34))

        self.clear_log_btn.setCursor(Qt.PointingHandCursor)

        self.cancel_btn.setCursor(Qt.PointingHandCursor)



    def _style_cancel_btn(self, enabled: bool):

        key = 'cancel' if enabled else 'cancel_disabled'

        self.cancel_btn.setStyleSheet(self._task_styles[key])



    def _toggle_body(self):

        self._expanded = not self._expanded

        self.body.setVisible(self._expanded)

        self.toggle_btn.setText("Развернуть" if not self._expanded else "Свернуть")



    def _append_log(self, line: str):

        self.log_view.append(line)

        sb = self.log_view.verticalScrollBar()

        sb.setValue(sb.maximum())



    def _on_percent(self, value: int):

        self.progress.setValue(max(0, min(100, int(value))))



    def _on_message(self, message: str):

        if message:

            self.progress.setFormat(f"%p% — {message[:36]}")



    def _on_busy(self, busy: bool):

        self.cancel_btn.setEnabled(busy)

        self._style_cancel_btn(busy)

        if not busy:

            self.status_label.setText("Готов")

            self.status_label.setStyleSheet(self._task_styles['status_ready'])

            self.progress.setValue(0)

            self.progress.setFormat("%p%")

        else:

            pending = self._queue.pending_count()

            self.status_label.setText(f"Выполняется · в очереди {pending}")

            self.status_label.setStyleSheet(self._task_styles['status_busy'])



    def _on_task_started(self, title: str):

        self.status_label.setText(title[:28])

        self.status_label.setStyleSheet(self._task_styles['status_busy'])

        self._append_log(f"--- {title} ---")



    def _clear_log(self):

        self.log_view.clear()



    def update_styles(self, styles):

        self.styles = styles

        self._apply_theme()


