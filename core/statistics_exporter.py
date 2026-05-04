"""
Модуль для экспорта статистики в CSV и Excel форматы
"""

import csv
import os
from datetime import datetime
from typing import List, Dict
from pathlib import Path

try:
    import openpyxl
    from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
    OPENPYXL_AVAILABLE = True
except ImportError:
    OPENPYXL_AVAILABLE = False


class StatisticsExporter:
    """Класс для экспорта статистики в различные форматы"""
    
    def __init__(self, export_dir: str = './exports'):
        self.export_dir = export_dir
        Path(export_dir).mkdir(parents=True, exist_ok=True)
    
    # ===== ЭКСПОРТ В CSV =====
    
    def export_posts_to_csv(self, posts: List[Dict], filename: str = None) -> str:
        """
        Экспортирует посты в CSV
        
        Args:
            posts: список словарей с данными постов
            filename: имя файла (если None, генерируется автоматически)
        
        Returns:
            Путь к созданному файлу
        """
        if filename is None:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f'posts_export_{timestamp}.csv'
        
        filepath = os.path.join(self.export_dir, filename)
        
        try:
            with open(filepath, 'w', newline='', encoding='utf-8-sig') as csvfile:
                fieldnames = ['ID', 'Дата', 'Текст', 'Лайки', 'Комментарии', 
                             'Поделиться', 'Просмотры', 'Всего взаимодействий']
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                
                writer.writeheader()
                for post in posts:
                    writer.writerow({
                        'ID': post.get('post_id', ''),
                        'Дата': post.get('date', ''),
                        'Текст': post.get('text', ''),
                        'Лайки': post.get('likes', 0),
                        'Комментарии': post.get('comments', 0),
                        'Поделиться': post.get('shares', 0),
                        'Просмотры': post.get('views', 0),
                        'Всего взаимодействий': post.get('total_engagement', 0)
                    })
            
            print(f"[Export] Посты экспортированы в {filepath}")
            return filepath
        except Exception as e:
            print(f"[Export] Ошибка экспорта CSV: {e}")
            return None
    
    def export_employees_to_csv(self, employees: List[Dict], filename: str = None) -> str:
        """Экспортирует статистику преподавателей в CSV"""
        if filename is None:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f'employees_export_{timestamp}.csv'
        
        filepath = os.path.join(self.export_dir, filename)
        
        try:
            with open(filepath, 'w', newline='', encoding='utf-8-sig') as csvfile:
                fieldnames = ['ФИО', 'Упоминаний', 'Постов', 'Всего лайков', 
                             'Всего просмотров', 'Средние лайки на пост']
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                
                writer.writeheader()
                for emp in employees:
                    writer.writerow({
                        'ФИО': emp.get('employee', ''),
                        'Упоминаний': emp.get('mention_count', 0),
                        'Постов': emp.get('post_count', 0),
                        'Всего лайков': emp.get('total_likes', 0),
                        'Всего просмотров': emp.get('total_views', 0),
                        'Средние лайки на пост': f"{emp.get('avg_post_likes', 0):.2f}"
                    })
            
            print(f"[Export] Преподаватели экспортированы в {filepath}")
            return filepath
        except Exception as e:
            print(f"[Export] Ошибка экспорта CSV: {e}")
            return None
    
    def export_media_to_csv(self, media: List[Dict], filename: str = None) -> str:
        """Экспортирует статистику медиа в CSV"""
        if filename is None:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f'media_export_{timestamp}.csv'
        
        filepath = os.path.join(self.export_dir, filename)
        
        try:
            with open(filepath, 'w', newline='', encoding='utf-8-sig') as csvfile:
                fieldnames = ['Ключ медиа', 'Тип', 'Просмотры', 'Дата']
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                
                writer.writeheader()
                for m in media:
                    writer.writerow({
                        'Ключ медиа': m.get('media_key', ''),
                        'Тип': m.get('type', ''),
                        'Просмотры': m.get('metric_value', 0),
                        'Дата': m.get('date', '')
                    })
            
            print(f"[Export] Медиа экспортировано в {filepath}")
            return filepath
        except Exception as e:
            print(f"[Export] Ошибка экспорта CSV: {e}")
            return None
    
    # ===== ЭКСПОРТ В EXCEL =====
    
    def export_posts_to_excel(self, posts: List[Dict], filename: str = None) -> str:
        """Экспортирует посты в Excel"""
        if not OPENPYXL_AVAILABLE:
            print("[Export] openpyxl не установлен. Используйте CSV вместо Excel.")
            return self.export_posts_to_csv(posts, filename and filename.replace('.xlsx', '.csv'))
        
        if filename is None:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f'posts_export_{timestamp}.xlsx'
        
        filepath = os.path.join(self.export_dir, filename)
        
        try:
            from openpyxl import Workbook
            wb = Workbook()
            ws = wb.active
            ws.title = 'Посты'
            
            # Заголовки
            headers = ['ID', 'Дата', 'Текст', 'Лайки', 'Комментарии', 
                      'Поделиться', 'Просмотры', 'Всего взаимодействий']
            ws.append(headers)
            
            # Форматирование заголовков
            header_fill = PatternFill(start_color='4472C4', end_color='4472C4', fill_type='solid')
            header_font = Font(bold=True, color='FFFFFF')
            
            for cell in ws[1]:
                cell.fill = header_fill
                cell.font = header_font
                cell.alignment = Alignment(horizontal='center', vertical='center')
            
            # Данные
            for post in posts:
                ws.append([
                    post.get('post_id', ''),
                    post.get('date', ''),
                    post.get('text', ''),
                    post.get('likes', 0),
                    post.get('comments', 0),
                    post.get('shares', 0),
                    post.get('views', 0),
                    post.get('total_engagement', 0)
                ])
            
            # Автоширина столбцов
            ws.column_dimensions['A'].width = 12
            ws.column_dimensions['B'].width = 12
            ws.column_dimensions['C'].width = 40
            ws.column_dimensions['D'].width = 12
            ws.column_dimensions['E'].width = 15
            ws.column_dimensions['F'].width = 12
            ws.column_dimensions['G'].width = 12
            ws.column_dimensions['H'].width = 20
            
            # Форматирование чисел
            for row in ws.iter_rows(min_row=2, min_col=4, max_col=8):
                for cell in row:
                    cell.alignment = Alignment(horizontal='center')
            
            wb.save(filepath)
            print(f"[Export] Посты экспортированы в {filepath}")
            return filepath
        except Exception as e:
            print(f"[Export] Ошибка экспорта Excel: {e}")
            return None
    
    def export_employees_to_excel(self, employees: List[Dict], filename: str = None) -> str:
        """Экспортирует преподавателей в Excel"""
        if not OPENPYXL_AVAILABLE:
            return self.export_employees_to_csv(employees, filename and filename.replace('.xlsx', '.csv'))
        
        if filename is None:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f'employees_export_{timestamp}.xlsx'
        
        filepath = os.path.join(self.export_dir, filename)
        
        try:
            from openpyxl import Workbook
            wb = Workbook()
            ws = wb.active
            ws.title = 'Преподаватели'
            
            headers = ['ФИО', 'Упоминаний', 'Постов', 'Всего лайков', 
                      'Всего просмотров', 'Средние лайки на пост']
            ws.append(headers)
            
            header_fill = PatternFill(start_color='70AD47', end_color='70AD47', fill_type='solid')
            header_font = Font(bold=True, color='FFFFFF')
            
            for cell in ws[1]:
                cell.fill = header_fill
                cell.font = header_font
                cell.alignment = Alignment(horizontal='center', vertical='center')
            
            for emp in employees:
                ws.append([
                    emp.get('employee', ''),
                    emp.get('mention_count', 0),
                    emp.get('post_count', 0),
                    emp.get('total_likes', 0),
                    emp.get('total_views', 0),
                    f"{emp.get('avg_post_likes', 0):.2f}"
                ])
            
            ws.column_dimensions['A'].width = 30
            ws.column_dimensions['B'].width = 12
            ws.column_dimensions['C'].width = 12
            ws.column_dimensions['D'].width = 15
            ws.column_dimensions['E'].width = 15
            ws.column_dimensions['F'].width = 18
            
            for row in ws.iter_rows(min_row=2, min_col=2, max_col=6):
                for cell in row:
                    cell.alignment = Alignment(horizontal='center')
            
            wb.save(filepath)
            print(f"[Export] Преподаватели экспортированы в {filepath}")
            return filepath
        except Exception as e:
            print(f"[Export] Ошибка экспорта Excel: {e}")
            return None
    
    def export_comprehensive_report(self, stats: Dict, filename: str = None) -> str:
        """Создает комплексный отчет со всей статистикой"""
        if not OPENPYXL_AVAILABLE:
            print("[Export] openpyxl не установлен. Установите его: pip install openpyxl")
            return None
        
        if filename is None:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f'comprehensive_report_{timestamp}.xlsx'
        
        filepath = os.path.join(self.export_dir, filename)
        
        try:
            from openpyxl import Workbook
            wb = Workbook()
            
            # Лист 1: Сводка
            ws_summary = wb.active
            ws_summary.title = 'Сводка'
            
            ws_summary['A1'] = 'СТАТИСТИКА АРХИВА'
            ws_summary['A1'].font = Font(size=16, bold=True)
            ws_summary.merge_cells('A1:B1')
            
            ws_summary['A3'] = 'Всего постов:'
            ws_summary['B3'] = stats.get('total_posts', 0)
            ws_summary['A4'] = 'Всего фото:'
            ws_summary['B4'] = stats.get('total_photos', 0)
            ws_summary['A5'] = 'Всего видео:'
            ws_summary['B5'] = stats.get('total_videos', 0)
            ws_summary['A6'] = 'Всего лайков:'
            ws_summary['B6'] = stats.get('total_likes', 0)
            ws_summary['A7'] = 'Всего просмотров:'
            ws_summary['B7'] = stats.get('total_views', 0)
            ws_summary['A8'] = 'Средние лайки на пост:'
            ws_summary['B8'] = f"{stats.get('avg_likes_per_post', 0):.2f}"
            ws_summary['A9'] = 'Средние просмотры на пост:'
            ws_summary['B9'] = f"{stats.get('avg_views_per_post', 0):.2f}"
            
            ws_summary.column_dimensions['A'].width = 25
            ws_summary.column_dimensions['B'].width = 20
            
            print(f"[Export] Комплексный отчет создан: {filepath}")
            wb.save(filepath)
            return filepath
        except Exception as e:
            print(f"[Export] Ошибка экспорта отчета: {e}")
            return None
    
    # ===== УТИЛИТЫ =====
    
    def get_export_files(self) -> List[str]:
        """Получает список всех экспортированных файлов"""
        if not os.path.exists(self.export_dir):
            return []
        
        return os.listdir(self.export_dir)
    
    def clean_old_exports(self, max_age_days: int = 30) -> int:
        """
        Удаляет старые экспорты (старше N дней)
        
        Returns:
            Количество удаленных файлов
        """
        import time
        removed_count = 0
        max_age_seconds = max_age_days * 86400
        
        try:
            for filename in os.listdir(self.export_dir):
                filepath = os.path.join(self.export_dir, filename)
                file_age = time.time() - os.path.getmtime(filepath)
                
                if file_age > max_age_seconds:
                    os.remove(filepath)
                    removed_count += 1
            
            print(f"[Export] Удалено старых файлов: {removed_count}")
        except Exception as e:
            print(f"[Export] Ошибка при удалении файлов: {e}")
        
        return removed_count
