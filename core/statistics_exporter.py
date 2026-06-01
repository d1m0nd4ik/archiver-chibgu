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
    from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
    from openpyxl.chart import BarChart, LineChart, Reference
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
            
            # Headers: добавлена колонка "Популярность"
            headers = ['ID', 'Дата', 'Текст', 'Лайки', 'Комментарии', 'Поделиться', 'Популярность']
            ws.append(headers)
            
            # Форматирование заголовков
            header_fill = PatternFill(start_color='4472C4', end_color='4472C4', fill_type='solid')
            header_font = Font(bold=True, color='FFFFFF', size=11)
            header_border = Border(left=Side(style='thin'), right=Side(style='thin'),
                                  top=Side(style='thin'), bottom=Side(style='thin'))
            for cell in ws[1]:
                cell.fill = header_fill
                cell.font = header_font
                cell.alignment = Alignment(horizontal='center', vertical='center', wrap_text=True)
                cell.border = header_border
            
            zero_fill = PatternFill(start_color='FFC7CE', end_color='FFC7CE', fill_type='solid')
            positive_fill = PatternFill(start_color='C6EFCE', end_color='C6EFCE', fill_type='solid')
            zero_font = Font(color='9C0006')
            positive_font = Font(color='006100')

            # Добавление данных постов
            for row_idx, post in enumerate(posts, start=2):
                likes = post.get('likes', 0) or 0
                comments = post.get('comments', 0) or 0
                shares = post.get('shares', 0) or 0
                popularity = likes + comments + shares
                
                ws.append([
                    post.get('post_id', ''),
                    post.get('date', ''),
                    post.get('text', ''),
                    likes,
                    comments,
                    shares,
                    popularity
                ])

                # Цвет ячеек по значению: 0 = красный, >0 = зеленый
                for col, value in [('D', likes), ('E', comments), ('F', shares), ('G', popularity)]:
                    cell = ws[f'{col}{row_idx}']
                    if value == 0:
                        cell.fill = zero_fill
                        cell.font = zero_font
                    else:
                        cell.fill = positive_fill
                        cell.font = positive_font
            
            # Итоговая строка и среднее (если есть посты)
            if len(posts) > 0:
                # Пустая строка отступа перед ИТОГО
                total_row = len(posts) + 3  # +1 за пустую строку отступа
                ws[f'A{total_row}'] = 'ИТОГО'
                ws[f'A{total_row}'].font = Font(bold=True, size=11)
                ws[f'A{total_row}'].fill = PatternFill(start_color='E7E6E6', end_color='E7E6E6', fill_type='solid')
                
                # Формулы для итоговых значений (популярность как формула)
                ws[f'D{total_row}'] = f'=SUM(D2:D{total_row-1})'
                ws[f'E{total_row}'] = f'=SUM(E2:E{total_row-1})'
                ws[f'F{total_row}'] = f'=SUM(F2:F{total_row-1})'
                ws[f'G{total_row}'] = f'=SUM(G2:G{total_row-1})'
                
                # Форматирование итоговых строк
                for col in ['D', 'E', 'F', 'G']:
                    ws[f'{col}{total_row}'].fill = PatternFill(start_color='E7E6E6', end_color='E7E6E6', fill_type='solid')
                    ws[f'{col}{total_row}'].font = Font(bold=True)
                
                # Строка средних значений
                avg_row = total_row + 1
                ws[f'A{avg_row}'] = 'СРЕДНЕЕ'
                ws[f'A{avg_row}'].font = Font(bold=True, size=10, color='666666')
                ws[f'A{avg_row}'].fill = PatternFill(start_color='F2F2F2', end_color='F2F2F2', fill_type='solid')
                
                ws[f'D{avg_row}'] = f'=AVERAGE(D2:D{total_row-1})'
                ws[f'E{avg_row}'] = f'=AVERAGE(E2:E{total_row-1})'
                ws[f'F{avg_row}'] = f'=AVERAGE(F2:F{total_row-1})'
                ws[f'G{avg_row}'] = f'=AVERAGE(G2:G{total_row-1})'
                
                for col in ['D', 'E', 'F', 'G']:
                    ws[f'{col}{avg_row}'].fill = PatternFill(start_color='F2F2F2', end_color='F2F2F2', fill_type='solid')
                    ws[f'{col}{avg_row}'].font = Font(size=10)
            
            # Автоширина и перенос текста
            ws.column_dimensions['A'].width = 10
            ws.column_dimensions['B'].width = 15
            ws.column_dimensions['C'].width = 45
            ws.column_dimensions['D'].width = 12
            ws.column_dimensions['E'].width = 14
            ws.column_dimensions['F'].width = 12
            ws.column_dimensions['G'].width = 14
            
            # Перенос текста в текстовой колонке
            for row in ws.iter_rows(min_row=2, min_col=3, max_col=3, max_row=len(posts)+1):
                for cell in row:
                    cell.alignment = Alignment(horizontal='left', vertical='top', wrap_text=True)
            
            # Центрирование числовых значений
            for row in ws.iter_rows(min_row=2, min_col=4, max_col=7, max_row=len(posts)+1):
                for cell in row:
                    cell.alignment = Alignment(horizontal='center', vertical='center')
            
            # Freeze pane (заморозка заголовка)
            ws.freeze_panes = 'A2'
            
            # Автофильтр (только для данных, исключая ИТОГО и СРЕДНЕЕ)
            if len(posts) > 0:
                ws.auto_filter.ref = f'A1:G{len(posts)+1}'
            
            # Диаграммы: гистограмма и линии справа от таблицы
            if len(posts) > 0:
                top_n = min(10, len(posts))
                chart1 = BarChart()
                chart1.type = 'col'
                chart1.grouping = 'clustered'
                chart1.overlap = 0
                chart1.title = f'Топ {top_n} постов по популярности'
                chart1.y_axis.title = 'Популярность'
                chart1.x_axis.title = 'Дата'
                
                data1 = Reference(ws, min_col=7, min_row=1, max_row=top_n+1)
                cats1 = Reference(ws, min_col=2, min_row=2, max_row=top_n+1)
                chart1.add_data(data1, titles_from_data=True)
                chart1.set_categories(cats1)
                chart1.height = 10
                chart1.width = 20
                ws.add_chart(chart1, 'I2')
                
                trend_n = min(20, len(posts))
                
                # 2. LINE CHART: тренд лайков по дате
                chart2 = LineChart()
                chart2.title = 'Тренд лайков по времени (первые 20 постам)'
                chart2.y_axis.title = 'Лайки'
                chart2.x_axis.title = 'Дата'
                chart2.smooth = 0
                
                data2 = Reference(ws, min_col=4, min_row=1, max_row=trend_n+1)
                cats2 = Reference(ws, min_col=2, min_row=2, max_row=trend_n+1)
                chart2.add_data(data2, titles_from_data=True)
                chart2.set_categories(cats2)
                chart2.height = 10
                chart2.width = 20
                ws.add_chart(chart2, 'I7')
                
                # 3. LINE CHART: тренд комментариев по дате
                chart3 = LineChart()
                chart3.title = 'Тренд комментариев по времени (первые 20 постам)'
                chart3.y_axis.title = 'Комментарии'
                chart3.x_axis.title = 'Дата'
                chart3.smooth = 0
                
                data3 = Reference(ws, min_col=5, min_row=1, max_row=trend_n+1)
                cats3 = Reference(ws, min_col=2, min_row=2, max_row=trend_n+1)
                chart3.add_data(data3, titles_from_data=True)
                chart3.set_categories(cats3)
                chart3.height = 10
                chart3.width = 20
                ws.add_chart(chart3, 'I11')
                
                # 4. LINE CHART: тренд репостов по дате
                chart4 = LineChart()
                chart4.title = 'Тренд репостов по времени (первые 20 постам)'
                chart4.y_axis.title = 'Репосты'
                chart4.x_axis.title = 'Дата'
                chart4.smooth = 0
                
                data4 = Reference(ws, min_col=6, min_row=1, max_row=trend_n+1)
                cats4 = Reference(ws, min_col=2, min_row=2, max_row=trend_n+1)
                chart4.add_data(data4, titles_from_data=True)
                chart4.set_categories(cats4)
                chart4.height = 10
                chart4.width = 20
                ws.add_chart(chart4, 'I13')
            
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
            
            headers = ['ФИО', 'Упоминаний', 'Постов', 'Всего лайков', 'Средние лайки на пост']
            ws.append(headers)
            
            # Форматирование заголовков
            header_fill = PatternFill(start_color='70AD47', end_color='70AD47', fill_type='solid')
            header_font = Font(bold=True, color='FFFFFF', size=11)
            header_border = Border(left=Side(style='thin'), right=Side(style='thin'),
                                  top=Side(style='thin'), bottom=Side(style='thin'))
            for cell in ws[1]:
                cell.fill = header_fill
                cell.font = header_font
                cell.alignment = Alignment(horizontal='center', vertical='center', wrap_text=True)
                cell.border = header_border
            
            # Добавление данных преподавателей
            for emp in employees:
                mention_count = emp.get('mention_count', 0) or 0
                post_count = emp.get('post_count', 0) or 0
                total_likes = emp.get('total_likes', 0) or 0
                avg_likes = emp.get('avg_post_likes', 0) or 0
                
                ws.append([
                    emp.get('employee', ''),
                    mention_count,
                    post_count,
                    total_likes,
                    f"{avg_likes:.2f}"
                ])
            
            # Итоговая строка
            if len(employees) > 0:
                total_row = len(employees) + 2
                ws[f'A{total_row}'] = 'ИТОГО'
                ws[f'A{total_row}'].font = Font(bold=True, size=11)
                ws[f'A{total_row}'].fill = PatternFill(start_color='E7E6E6', end_color='E7E6E6', fill_type='solid')
                
                # Формулы
                ws[f'B{total_row}'] = f'=SUM(B2:B{total_row-1})'
                ws[f'C{total_row}'] = f'=SUM(C2:C{total_row-1})'
                ws[f'D{total_row}'] = f'=SUM(D2:D{total_row-1})'
                ws[f'E{total_row}'] = f'=AVERAGE(E2:E{total_row-1})'
                
                for col in ['B', 'C', 'D', 'E']:
                    ws[f'{col}{total_row}'].fill = PatternFill(start_color='E7E6E6', end_color='E7E6E6', fill_type='solid')
                    ws[f'{col}{total_row}'].font = Font(bold=True)
            
            # Ширина колонок
            ws.column_dimensions['A'].width = 30
            ws.column_dimensions['B'].width = 14
            ws.column_dimensions['C'].width = 12
            ws.column_dimensions['D'].width = 15
            ws.column_dimensions['E'].width = 18
            
            # Центрирование
            for row in ws.iter_rows(min_row=2, min_col=2, max_col=5, max_row=len(employees)+1):
                for cell in row:
                    cell.alignment = Alignment(horizontal='center')
            
            # Freeze pane
            ws.freeze_panes = 'A2'
            
            # Автофильтр
            if len(employees) > 0:
                ws.auto_filter.ref = f'A1:E{len(employees)+1}'
                
                # Диаграмма: топ преподавателей по упоминаниям
                top_n = min(10, len(employees))
                chart = BarChart()
                chart.type = 'col'
                chart.title = f'Топ {top_n} преподавателей по упоминаниям'
                chart.y_axis.title = 'Количество упоминаний'
                chart.x_axis.title = 'ФИО'
                
                data = Reference(ws, min_col=2, min_row=1, max_row=top_n+1)
                cats = Reference(ws, min_col=1, min_row=2, max_row=top_n+1)
                chart.add_data(data, titles_from_data=True)
                chart.set_categories(cats)
                chart.height = 10
                chart.width = 20
                ws.add_chart(chart, 'A' + str(len(employees) + 4))
            
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
    
    def export_media_to_excel(self, media: List[Dict], filename: str = None) -> str:
        if not OPENPYXL_AVAILABLE:
            return self.export_media_to_csv(media, filename.replace('.xlsx', '.csv') if filename else None)
        
        if filename is None:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f'media_export_{timestamp}.xlsx'
        
        self._ensure_export_dir()
        filepath = os.path.join(self.export_dir, filename)
        try:
            wb = openpyxl.Workbook()
            ws = wb.active
            ws.title = 'Медиа'
            
            headers = ['ID поста', 'Ключ медиа', 'Тип', 'Лайки', 'Комментарии', 'Репосты', 'Дата']
            ws.append(headers)
            
            # Форматирование заголовков
            header_fill = PatternFill(start_color='9C27B0', end_color='9C27B0', fill_type='solid')
            header_font = Font(bold=True, color='FFFFFF', size=11)
            header_border = Border(left=Side(style='thin'), right=Side(style='thin'),
                                  top=Side(style='thin'), bottom=Side(style='thin'))
            for cell in ws[1]:
                cell.fill = header_fill
                cell.font = header_font
                cell.alignment = Alignment(horizontal='center', vertical='center', wrap_text=True)
                cell.border = header_border
            
            # Добавление данных медиа
            for m in media:
                likes = m.get('likes', 0) or 0
                comments = m.get('comments', 0) or 0
                shares = m.get('shares', 0) or 0
                
                ws.append([
                    m.get('post_id', ''),
                    m.get('media_key', ''),
                    m.get('media_type', ''),
                    likes,
                    comments,
                    shares,
                    m.get('date', '')
                ])
            
            # Итоговая строка
            if len(media) > 0:
                total_row = len(media) + 2
                ws[f'A{total_row}'] = 'ИТОГО'
                ws[f'A{total_row}'].font = Font(bold=True, size=11)
                ws[f'A{total_row}'].fill = PatternFill(start_color='E7E6E6', end_color='E7E6E6', fill_type='solid')
                
                # Формулы
                ws[f'D{total_row}'] = f'=SUM(D2:D{total_row-1})'
                ws[f'E{total_row}'] = f'=SUM(E2:E{total_row-1})'
                ws[f'F{total_row}'] = f'=SUM(F2:F{total_row-1})'
                
                for col in ['D', 'E', 'F']:
                    ws[f'{col}{total_row}'].fill = PatternFill(start_color='E7E6E6', end_color='E7E6E6', fill_type='solid')
                    ws[f'{col}{total_row}'].font = Font(bold=True)
            
            # Ширина колонок
            ws.column_dimensions['A'].width = 12
            ws.column_dimensions['B'].width = 25
            ws.column_dimensions['C'].width = 12
            ws.column_dimensions['D'].width = 12
            ws.column_dimensions['E'].width = 14
            ws.column_dimensions['F'].width = 12
            ws.column_dimensions['G'].width = 14
            
            # Центрирование числовых значений
            for row in ws.iter_rows(min_row=2, min_col=4, max_col=6, max_row=len(media)+1):
                for cell in row:
                    cell.alignment = Alignment(horizontal='center')
            
            # Freeze pane
            ws.freeze_panes = 'A2'
            
            # Автофильтр
            if len(media) > 0:
                ws.auto_filter.ref = f'A1:G{len(media)+1}'
                
                # Диаграмма: топ медиа по лайкам
                top_n = min(15, len(media))
                chart = BarChart()
                chart.type = 'col'
                chart.title = f'Топ {top_n} медиа по лайкам'
                chart.y_axis.title = 'Лайки'
                chart.x_axis.title = 'Тип медиа'
                
                data = Reference(ws, min_col=4, min_row=1, max_row=top_n+1)
                cats = Reference(ws, min_col=3, min_row=2, max_row=top_n+1)
                chart.add_data(data, titles_from_data=True)
                chart.set_categories(cats)
                chart.height = 10
                chart.width = 18
                ws.add_chart(chart, 'A' + str(len(media) + 4))
            
            wb.save(filepath)
            logger.info("Медиа экспортировано в %s", filepath)
            return filepath
        except Exception as e:
            logger.error("Ошибка экспорта Excel: %s", e, exc_info=True)
            return None