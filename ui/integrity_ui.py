"""Диалоги проверки целостности архива (Настройки → Архив)."""
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QTextEdit, QPushButton, QMessageBox,
    QInputDialog,
)

from core.database import Database
from core.archive_integrity import check_archive_integrity
from core.integrity_actions import (
    delete_missing_attachment_records,
    open_post_folder,
    register_orphan_file,
)
from core.task_queue import AppTaskQueue


def run_integrity_check(parent):
    queue = AppTaskQueue.instance()
    if queue.is_busy():
        QMessageBox.information(
            parent,
            "Занято",
            "Дождитесь завершения текущей задачи или отмените её в Настройки → Фоновые задачи.",
        )
        return
    queue.enqueue_integrity_check(scan_orphans=True)
    QMessageBox.information(
        parent,
        "Проверка запущена",
        "Проверка целостности добавлена в очередь.\n"
        "Журнал и результат — в Настройки → Фоновые задачи.",
    )


def show_integrity_report(parent, report: dict | None = None, *, results_context: list | None = None):
    if report is None:
        db = Database()
        try:
            report = check_archive_integrity(db)
        finally:
            db.close()
    missing = report.get('missing_files', [])
    orphans = report.get('orphan_files', [])
    lines = [
        f"Отсутствующих файлов (в БД, нет на диске): {len(missing)}",
        f"Файлов на диске без записи в БД: {len(orphans)}",
        f"Пустых путей в БД: {len(report.get('empty_paths', []))}",
        f"Постов без вложений: {report.get('posts_without_attachments', 0)}",
    ]
    if missing:
        lines.append("\nПримеры отсутствующих:")
        for m in missing[:15]:
            lines.append(f"  пост {m['original_post_id']}: {m.get('media_path')}")
    if orphans:
        lines.append("\nПримеры лишних файлов:")
        for p in orphans[:15]:
            lines.append(f"  {p}")
    dlg = QDialog(parent)
    dlg.setWindowTitle("Целостность архива")
    lay = QVBoxLayout(dlg)
    te = QTextEdit()
    te.setReadOnly(True)
    te.setPlainText("\n".join(lines))
    lay.addWidget(te)
    btn_row = QHBoxLayout()
    del_btn = QPushButton("Удалить битые записи из БД")
    del_btn.clicked.connect(lambda: _integrity_delete_missing(dlg, missing))
    btn_row.addWidget(del_btn)
    folder_btn = QPushButton("Открыть папку поста…")
    folder_btn.clicked.connect(
        lambda: _integrity_open_folder(parent, results_context)
    )
    btn_row.addWidget(folder_btn)
    link_btn = QPushButton("Привязать лишний файл…")
    link_btn.clicked.connect(lambda: _integrity_link_orphan(dlg, orphans))
    btn_row.addWidget(link_btn)
    ok = QPushButton("Закрыть")
    ok.clicked.connect(dlg.accept)
    btn_row.addWidget(ok)
    lay.addLayout(btn_row)
    dlg.resize(620, 420)
    dlg.exec()


def _integrity_delete_missing(dlg, missing: list):
    if not missing:
        QMessageBox.information(dlg, "Нет записей", "Нет отсутствующих файлов в отчёте.")
        return
    db = Database()
    try:
        n = delete_missing_attachment_records(db, missing)
    finally:
        db.close()
    QMessageBox.information(dlg, "Готово", f"Удалено записей вложений: {n}")


def _integrity_open_folder(parent, results_context: list | None):
    pid = None
    if results_context:
        pid, ok = QInputDialog.getInt(
            parent, "ID поста", "original_post_id:", 0, -999999, 999999999
        )
        if not ok:
            return
    else:
        pid, ok = QInputDialog.getInt(
            parent, "ID поста", "original_post_id:", 0, -999999, 999999999
        )
        if not ok:
            return
    ok_open, msg = open_post_folder(int(pid))
    if not ok_open:
        QMessageBox.warning(parent, "Папка", msg)


def _integrity_link_orphan(dlg, orphans: list):
    if not orphans:
        QMessageBox.information(dlg, "Нет файлов", "Лишних файлов не найдено.")
        return
    path, ok = QInputDialog.getItem(
        dlg, "Лишний файл", "Выберите файл:", orphans[:50], 0, False
    )
    if not ok:
        return
    pid, ok2 = QInputDialog.getInt(dlg, "К посту", "original_post_id:", 0, -999999, 999999999)
    if not ok2:
        return
    db = Database()
    try:
        ok3 = register_orphan_file(db, path, int(pid))
    finally:
        db.close()
    QMessageBox.information(
        dlg, "Привязка", "Файл привязан." if ok3 else "Не удалось привязать файл."
    )
