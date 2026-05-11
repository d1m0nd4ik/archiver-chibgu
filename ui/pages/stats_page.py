import datetime
from PySide6.QtWidgets import QWidget, QVBoxLayout, QFrame, QLabel, QGridLayout, QComboBox, QDateEdit, QPushButton, QHBoxLayout, QTextEdit, QMessageBox, QCheckBox
from PySide6.QtCore import Qt
from ui.styles import STYLES
from core.statistics_analyzer import StatisticsAnalyzer
from core.statistics_exporter import StatisticsExporter
from core.logging_config import logger

class StatsPage(QWidget):
    def __init__(self, styles=None):
        super().__init__()
        self.styles = styles or STYLES.get_styles()
        self.analyzer = StatisticsAnalyzer()
        self.exporter = StatisticsExporter()
        self.init_ui()
        self.refresh_statistics()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(30, 30, 30, 30)
        layout.setSpacing(20)

        header = QLabel("Статистика архива")
        tc = '#000000' if STYLES._theme == 'light' else '#ffffff'
        header.setStyleSheet(f"color: {tc}; font-size: 22px; font-weight: bold; padding: 10px 0;")
        self.header_label = header
        layout.addWidget(header)

        cf = QFrame(); cf.setStyleSheet(self.styles['frame']); cl = QGridLayout(cf); cl.setSpacing(16)
        cl.addWidget(QLabel("Период: "), 0, 0)
        self.period_combo = QComboBox(); self.period_combo.addItems(["Час", "День", "Неделя", "Месяц", "Год", "Все время", "Свой диапазон"]); self.period_combo.setCurrentText("День"); self.period_combo.currentTextChanged.connect(self.on_period_changed); self.period_combo.setStyleSheet(self.styles['input']); cl.addWidget(self.period_combo, 0, 1)
        cl.addWidget(QLabel("Метрика: "), 0, 2)
        self.metric_combo = QComboBox(); self.metric_combo.addItems(["Лайки", "Комментарии", "Репосты", "Просмотры"]); self.metric_combo.setCurrentText("Просмотры"); self.metric_combo.setStyleSheet(self.styles['input']); cl.addWidget(self.metric_combo, 0, 3)
        cl.addWidget(QLabel("Дата от: "), 1, 0)
        self.custom_start = QDateEdit(); self.custom_start.setCalendarPopup(True); self.custom_start.setDate(datetime.datetime.now() - datetime.timedelta(days=30)); self.custom_start.setEnabled(False); self.custom_start.setStyleSheet(self.styles['input']); cl.addWidget(self.custom_start, 1, 1)
        cl.addWidget(QLabel("Дата до: "), 1, 2)
        self.custom_end = QDateEdit(); self.custom_end.setCalendarPopup(True); self.custom_end.setDate(datetime.datetime.now()); self.custom_end.setEnabled(False); self.custom_end.setStyleSheet(self.styles['input']); cl.addWidget(self.custom_end, 1, 3)
        
        self.show_active_cb = QCheckBox("Показать только тех, у кого > 0 постов"); self.show_active_cb.setStyleSheet(f"color: {tc}; font-size: 13px;"); self.show_active_cb.setChecked(False); self.show_active_cb.stateChanged.connect(self.refresh_statistics); cl.addWidget(self.show_active_cb, 2, 0, 1, 2)
        self.refresh_btn = QPushButton("Обновить статистику"); self.refresh_btn.setStyleSheet(self.styles['button']); self.refresh_btn.clicked.connect(self.refresh_statistics); cl.addWidget(self.refresh_btn, 2, 2, 1, 2)
        self.exp_csv = QPushButton("Экспорт CSV"); self.exp_csv.setStyleSheet(self.styles['button_secondary']); self.exp_csv.clicked.connect(lambda: self._export('csv')); cl.addWidget(self.exp_csv, 2, 4, 1, 2)
        self.exp_xls = QPushButton("Экспорт Excel"); self.exp_xls.setStyleSheet(self.styles['button_secondary']); self.exp_xls.clicked.connect(lambda: self._export('xls')); cl.addWidget(self.exp_xls, 2, 6, 1, 2)
        layout.addWidget(cf)

        self.top_posts = QTextEdit(); self.top_posts.setReadOnly(True); self.top_posts.setStyleSheet(self.styles['textedit']); self.top_posts.setMinimumHeight(240)
        self.top_emps = QTextEdit(); self.top_emps.setReadOnly(True); self.top_emps.setStyleSheet(self.styles['textedit']); self.top_emps.setMinimumHeight(240)
        rl = QHBoxLayout()
        pf = QFrame(); pf.setStyleSheet(self.styles['frame']); pl = QVBoxLayout(pf); pl.addWidget(QLabel("Топ постов")); pl.addWidget(self.top_posts)
        ef = QFrame(); ef.setStyleSheet(self.styles['frame']); el = QVBoxLayout(ef); el.addWidget(QLabel("Топ преподавателей")); el.addWidget(self.top_emps)
        rl.addWidget(pf); rl.addWidget(ef); layout.addLayout(rl); layout.addStretch()

    def on_period_changed(self, v): self.custom_start.setEnabled(v=="Свой диапазон"); self.custom_end.setEnabled(v=="Свой диапазон")
    def get_period(self): return {"Час":"hour","День":"day","Неделя":"week","Месяц":"month","Год":"year","Все время":"all_time","Свой диапазон":"custom"}.get(self.period_combo.currentText(), "day")
    def get_range(self):
        p = self.get_period()
        if p=="custom": return self.custom_start.date().toPython(), self.custom_end.date().toPython()+datetime.timedelta(days=1)
        return self.analyzer.period_calc.get_period_range(p)
    def _mk(self, n): return {'Лайки':'likes','Комментарии':'comments','Репосты':'shares','Просмотры':'views'}.get(n,'views')

    def refresh_statistics(self):
        try:
            pk, sd, ed = self.get_period(), *self.get_range()
            mk = self._mk(self.metric_combo.currentText())
            sm = self.analyzer.get_statistics_summary(pk, sd, ed)
            self.status_message = f"Период: {sm.get('period')} | Постов: {sm.get('total_posts')} | Просмотров: {sm.get('total_views')} | Лайков: {sm.get('total_likes')}"
            
            tp = self.analyzer.get_top_posts(pk, sd, ed, mk, limit=10) or []
            te = self.analyzer.get_top_employees(pk, sd, ed, limit=None) or []
            if self.show_active_cb.isChecked(): te = [e for e in te if e.get('post_count',0)>0]
            
            self.top_posts.setPlainText(self._fmt_p(tp))
            self.top_emps.setPlainText(self._fmt_e(te))
        except Exception as e:
            logger.error(f"Stats error: {e}", exc_info=True)
            self.top_posts.setPlainText(f"Ошибка: {e}")
            self.top_emps.clear()

    def _fmt_p(self, p):
        if not p: return "Нет данных."
        l = []
        for i,x in enumerate(p,1): l.extend([f"{i}. ID {x.get('post_id')} | {x.get('date')}", f"   Лайки: {x.get('likes')} | Просмотры: {x.get('views')}", f"   Текст: {x.get('text')}", " "])
        return "\n".join(l)
    def _fmt_e(self, e):
        if not e: return "Нет данных по преподавателям."
        l = []
        for i,x in enumerate(e,1): l.extend([f"{i}. {x.get('employee','?')} | Постов: {x.get('post_count',0)}", " "])
        return "\n".join(l)

    def _export(self, fmt):
        try:
            pk, sd, ed = self.get_period(), *self.get_range()
            mk = self._mk(self.metric_combo.currentText())
            posts = self.analyzer.get_top_posts(pk, sd, ed, mk, limit=50)
            path = self.exporter.export_posts_to_csv(posts) if fmt=='csv' else self.exporter.export_posts_to_excel(posts)
            if path: QMessageBox.information(self, "Готово", f"Файл сохранён:\n{path}")
        except Exception as e: QMessageBox.critical(self, "Ошибка экспорта", str(e))

    def update_styles(self, styles):
        self.styles = styles
        tc = '#000000' if STYLES._theme == 'light' else '#ffffff'
        bg = '#f5f5f5' if STYLES._theme == 'light' else '#1e1e1e'
        self.header_label.setStyleSheet(f"color: {tc}; font-size: 22px; font-weight: bold; padding: 10px 0;")
        self.setStyleSheet(f"background-color: {bg};")
        self.top_posts.setStyleSheet(self.styles['textedit']); self.top_emps.setStyleSheet(self.styles['textedit'])
        self.show_active_cb.setStyleSheet(f"color: {tc}; font-size: 13px;")