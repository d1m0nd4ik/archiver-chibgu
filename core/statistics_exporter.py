"""
Модуль для экспорта статистики в CSV и Excel форматы
"""
import csv
import os
import time
from datetime import datetime
from typing import List, Dict
from pathlib import Path

from requests import post
from core.logging_config import logger

try:
    import openpyxl
    from openpyxl.styles import Font, PatternFill, Alignment
    OPENPYXL_AVAILABLE = True
except ImportError:
    OPENPYXL_AVAILABLE = False

class StatisticsExporter:
    """Класс для экспорта статистики в различные форматы"""
    def __init__(self, export_dir: str = './exports'):
        self.export_dir = export_dir

    def _ensure_export_dir(self):
        if not os.path.exists(self.export_dir):
            Path(self.export_dir).mkdir(parents=True, exist_ok=True)

    # ===== ЭКСПОРТ В CSV =====
    def export_posts_to_csv(self, posts: List[Dict], filename: str = None) -> str:
        if filename is None:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f'posts_export_{timestamp}.csv'
        
        self._ensure_export_dir()
        filepath = os.path.join(self.export_dir, filename)
        try:
            with open(filepath, 'w', newline='', encoding='utf-8-sig') as csvfile:
                fieldnames = ['ID', 'Дата', 'Текст', 'Лайки', 'Комментарии', 'Поделиться']
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                writer.writeheader()
                for post in posts:
                    writer.writerow({
                        'ID': post.get('post_id', ''),
                        'Дата': post.get('date', ''),
                        'Текст': post.get('text', ''),
                        'Лайки': post.get('likes', 0),
                        'Комментарии': post.get('comments', 0),
                        'Поделиться': post.get('shares', 0)
                    })
            logger.info("Посты экспортированы в %s", filepath)
            return filepath
        except Exception as e:
            logger.error("Ошибка экспорта CSV: %s", e, exc_info=True)
            return None

    def export_employees_to_csv(self, employees: List[Dict], filename: str = None) -> str:
        if filename is None:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f'employees_export_{timestamp}.csv'
        
        self._ensure_export_dir()
        filepath = os.path.join(self.export_dir, filename)
        try:
            with open(filepath, 'w', newline='', encoding='utf-8-sig') as csvfile:
                fieldnames = ['ФИО', 'Упоминаний', 'Постов', 'Всего лайков',
                              'Средние лайки на пост']
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                writer.writeheader()
                for emp in employees:
                    writer.writerow({
                        'ФИО': emp.get('employee', ''),
                        'Упоминаний': emp.get('mention_count', 0),
                        'Постов': emp.get('post_count', 0),
                        'Всего лайков': emp.get('total_likes', 0),
                        'Средние лайки на пост': f"{emp.get('avg_post_likes', 0):.2f}"
                    })
            logger.info("Преподаватели экспортированы в %s", filepath)
            return filepath
        except Exception as e:
            logger.error("Ошибка экспорта CSV: %s", e, exc_info=True)
            return None

    def export_media_to_csv(self, media: List[Dict], filename: str = None) -> str:
        if filename is None:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f'media_export_{timestamp}.csv'
        
        self._ensure_export_dir()
        filepath = os.path.join(self.export_dir, filename)
        try:
            with open(filepath, 'w', newline='', encoding='utf-8-sig') as csvfile:
                fieldnames = ['Ключ медиа', 'Тип', 'Лайки', 'Комментарии', 'Дата']
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                writer.writeheader()
                for m in media:
                    writer.writerow({
                        'Ключ медиа': m.get('media_key', ''),
                        'Тип': m.get('type', ''),
                        'Лайки': m.get('likes', m.get('metric_value', 0)),
                        'Комментарии': m.get('comments', 0),
                        'Дата': m.get('date', '')
                    })
            logger.info("Медиа экспортировано в %s", filepath)
            return filepath
        except Exception as e:
            logger.error("Ошибка экспорта CSV: %s", e, exc_info=True)
            return None

    # ===== ЭКСПОРТ В EXCEL =====
    def export_posts_to_excel(self, posts: List[Dict], filename: str = None) -> str:
        if not OPENPYXL_AVAILABLE:
            logger.info("openpyxl не установлен. Использую CSV-фоллбек.")
            return self.export_posts_to_csv(posts, filename.replace('.xlsx', '.csv') if filename else None)
        
        if filename is None:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f'posts_export_{timestamp}.xlsx'
        
        self._ensure_export_dir()
        filepath = os.path.join(self.export_dir, filename)
        try:
            wb = openpyxl.Workbook()
            ws = wb.active
            ws.title = 'Посты'
            
            headers = ['ID', 'Дата', 'Текст', 'Лайки', 'Комментарии', 'Поделиться']
            ws.append(headers)
            
            header_fill = PatternFill(start_color='4472C4', end_color='4472C4', fill_type='solid')
            header_font = Font(bold=True, color='FFFFFF')
            for cell in ws[1]:
                cell.fill = header_fill
                cell.font = header_font
                cell.alignment = Alignment(horizontal='center', vertical='center')
            
            for post in posts:
                ws.append([
                    post.get('post_id', ''), post.get('date', ''), post.get('text', ''),
                    post.get('likes', 0), post.get('comments', 0), post.get('shares', 0)
                ])
            
            for col, width in [('A', 12), ('B', 12), ('C', 40), ('D', 12), 
                               ('E', 15), ('F', 12), ('G', 12), ('H', 20)]:
                ws.column_dimensions[col].width = width
                
            for row in ws.iter_rows(min_row=2, min_col=4, max_col=8):
                for cell in row:
                    cell.alignment = Alignment(horizontal='center')
            
            wb.save(filepath)
            logger.info("Посты экспортированы в %s", filepath)
            return filepath
        except Exception as e:
            logger.error("Ошибка экспорта Excel: %s", e, exc_info=True)
            return None

    def export_employees_to_excel(self, employees: List[Dict], filename: str = None) -> str:
        if not OPENPYXL_AVAILABLE:
            return self.export_employees_to_csv(employees, filename.replace('.xlsx', '.csv') if filename else None)
        
        if filename is None:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f'employees_export_{timestamp}.xlsx'
        
        self._ensure_export_dir()
        filepath = os.path.join(self.export_dir, filename)
        try:
            wb = openpyxl.Workbook()
            ws = wb.active
            ws.title = 'Преподаватели'
            
            headers = ['ФИО', 'Упоминаний', 'Постов', 'Всего лайков',
                       'Средние лайки на пост']
            ws.append(headers)
            
            header_fill = PatternFill(start_color='70AD47', end_color='70AD47', fill_type='solid')
            header_font = Font(bold=True, color='FFFFFF')
            for cell in ws[1]:
                cell.fill = header_fill
                cell.font = header_font
                cell.alignment = Alignment(horizontal='center', vertical='center')
            
            for emp in employees:
                ws.append([
                    emp.get('employee', ''), emp.get('mention_count', 0), emp.get('post_count', 0),
                    emp.get('total_likes', 0),
                    f"{emp.get('avg_post_likes', 0):.2f}"
                ])
            
            for col, width in [('A', 30), ('B', 12), ('C', 12), ('D', 15), ('E', 18)]:
                ws.column_dimensions[col].width = width
                
            for row in ws.iter_rows(min_row=2, min_col=2, max_col=5):
                for cell in row:
                    cell.alignment = Alignment(horizontal='center')
            
            wb.save(filepath)
            logger.info("Преподаватели экспортированы в %s", filepath)
            return filepath
        except Exception as e:
            logger.error("Ошибка экспорта Excel: %s", e, exc_info=True)
            return None

    def export_comprehensive_report(self, stats: Dict, filename: str = None) -> str:
        if not OPENPYXL_AVAILABLE:
            logger.info("openpyxl не установлен. Экспорт отчета недоступен.")
            return None
        
        if filename is None:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f'comprehensive_report_{timestamp}.xlsx'
        
        self._ensure_export_dir()
        filepath = os.path.join(self.export_dir, filename)
        try:
            wb = openpyxl.Workbook()
            ws = wb.active
            ws.title = 'Сводка'
            
            ws['A1'] = 'СТАТИСТИКА АРХИВА'
            ws['A1'].font = Font(size=16, bold=True)
            ws.merge_cells('A1:B1')
            
            ws['A3'] = 'Всего постов:'; ws['B3'] = stats.get('total_posts', 0)
            ws['A4'] = 'Всего фото:'; ws['B4'] = stats.get('total_photos', 0)
            ws['A5'] = 'Всего видео:'; ws['B5'] = stats.get('total_videos', 0)
            ws['A6'] = 'Всего лайков:'; ws['B6'] = stats.get('total_likes', 0)
            ws['A7'] = 'Средние лайки на пост:'; ws['B7'] = f"{stats.get('avg_likes_per_post', 0):.2f}"
            
            ws.column_dimensions['A'].width = 25
            ws.column_dimensions['B'].width = 20
            
            logger.info("Комплексный отчет создан: %s", filepath)
            wb.save(filepath)
            return filepath
        except Exception as e:
            logger.error("Ошибка экспорта отчета: %s", e, exc_info=True)
            return None

    # ===== УТИЛИТЫ =====
    def get_export_files(self) -> List[str]:
        if not os.path.exists(self.export_dir):
            return []
        return os.listdir(self.export_dir)

    def clean_old_exports(self, max_age_days: int = 30) -> int:
        removed_count = 0
        max_age_seconds = max_age_days * 86400
        try:
            for filename in os.listdir(self.export_dir):
                filepath = os.path.join(self.export_dir, filename)
                file_age = time.time() - os.path.getmtime(filepath)
                if file_age > max_age_seconds:
                    os.remove(filepath)
                    removed_count += 1
            logger.info("Удалено старых экспортов: %d", removed_count)
        except Exception as e:
            logger.error("Ошибка при удалении старых файлов: %s", e, exc_info=True)
        return removed_count