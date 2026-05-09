"""
Модуль для анализа статистики постов, видео, фото и преподавателей
"""

from datetime import datetime, timedelta
from typing import Dict, List, Tuple
from collections import defaultdict
from pathlib import Path
import json
import re

import pandas as pd

from core.database import Database
from core.period_calculator import PeriodCalculator
from core.employee_tagger import extract_employees_from_html, remove_duplicates, normalize_name


class StatisticsAnalyzer:
    """Класс для анализа статистики контента"""
    
    EMPLOYEE_LIST_PATH = Path('employees_unique.xlsx')

    def __init__(self):
        self.db = Database()
        self.period_calc = PeriodCalculator()
    
    def load_employee_list(self) -> List[str]:
        """Загружает список преподавателей из файла employees_unique.xlsx"""
        file_employees = []
        if self.EMPLOYEE_LIST_PATH.exists():
            try:
                df = pd.read_excel(self.EMPLOYEE_LIST_PATH)
                if 'ФИО сотрудника' in df.columns:
                    names = df['ФИО сотрудника'].dropna().astype(str).tolist()
                elif 'ФИО' in df.columns:
                    names = df['ФИО'].dropna().astype(str).tolist()
                else:
                    names = df.iloc[:, 0].dropna().astype(str).tolist()
                file_employees = [normalize_name(name.strip()) for name in names if name and len(name.strip()) > 3 and self.is_human_name(normalize_name(name.strip()))]
            except Exception:
                file_employees = []
        
        # Извлекаем преподавателей из постов
        post_employees = self.extract_employees_from_posts()
        
        # Объединяем и удаляем дубликаты
        all_employees = file_employees + post_employees
        return remove_duplicates(all_employees)
    
    def extract_employees_from_posts(self) -> List[str]:
        """Извлекает имена преподавателей из текста постов"""
        
        # Получаем все посты
        posts = self.db.get_all_posts()
        employees = []
        
        # Паттерны для поиска имен
        # Ф.И.О. формат
        fio_pattern = re.compile(r'\b[А-ЯЁ]\.\s*[А-ЯЁ]\.\s*[А-ЯЁ][а-яё]+\b')
        # Имя Отчество Фамилия
        full_name_pattern = re.compile(r'\b[А-ЯЁ][а-яё]+\s+[А-ЯЁ][а-яё]+\s+[А-ЯЁ][а-яё]+\b')
        # Фамилия И.О.
        surname_io_pattern = re.compile(r'\b[А-ЯЁ][а-яё]+\s+[А-ЯЁ]\.\s*[А-ЯЁ]\.\b')
        
        for post in posts:
            text = post[2] or ''
            tags = post[3] or ''
            full_text = text + ' ' + tags
            
            # Ищем по паттернам
            matches = []
            matches.extend(fio_pattern.findall(full_text))
            matches.extend(full_name_pattern.findall(full_text))
            matches.extend(surname_io_pattern.findall(full_text))
            
            for match in matches:
                normalized = normalize_name(match)
                if len(normalized) > 3 and self.is_human_name(normalized) and normalized not in employees:
                    employees.append(normalized)
        
        return employees
    
    def is_human_name(self, name: str) -> bool:
        """Проверяет, является ли строка именем человека"""
        # Разбиваем на слова
        words = name.split()
        
        # Должно быть 2-4 слова
        if not 2 <= len(words) <= 4:
            return False
        
        # Каждое слово должно начинаться с заглавной буквы
        for word in words:
            if not word[0].isupper():
                return False
        
        # Не должно содержать цифр
        if any(char.isdigit() for char in name):
            return False
        
        # Не должно содержать определенных слов, указывающих на не-человеческие сущности
        non_human_words = [
            'представители', 'регионального', 'центр', 'институт', 'факультет',
            'кафедра', 'отдел', 'служба', 'управление', 'комитет', 'совет',
            'ассоциация', 'организация', 'компания', 'фирма', 'завод', 'школа',
            'колледж', 'университет', 'академия'
        ]
        
        name_lower = name.lower()
        for word in non_human_words:
            if word in name_lower:
                return False
        
        # Для Ф.И.О. формата - проверяем отдельно
        if '.' in name:
            # Разбиваем по точкам и пробелам
            parts = re.split(r'[.\s]+', name)
            parts = [p for p in parts if p]  # Убираем пустые
            
            if len(parts) == 3:
                # Ф.И.О. - первые две части должны быть однобуквенными, третья - словом
                if (len(parts[0]) == 1 and len(parts[1]) == 1 and len(parts[2]) > 1 and
                    all(p[0].isupper() for p in parts)):
                    return True
            elif len(parts) == 2:
                # Фамилия И.О.
                if (len(parts[0]) > 1 and len(parts[1]) == 2 and 
                    parts[1][1] == '.' and all(p[0].isupper() for p in parts)):
                    return True
            else:
                return False
        
        return True
    
    def normalize_employee_name_for_display(self, name: str) -> str:
        """Нормализует имя преподавателя для отображения в формате 'Фамилия Имя Отчество'"""
        parts = name.split()
        
        # Если в формате "Ф.И.О." - ищем соответствующее полное имя
        if '.' in name:
            # Получаем все имена преподавателей
            all_employees = self.load_employee_list()
            
            # Ищем полное имя, которое соответствует этому сокращению
            for full_name in all_employees:
                if self._matches_abbreviation(name, full_name):
                    return full_name
            
            # Если не нашли, возвращаем как есть
            return name
        
        # Для полных имен - приводим к формату "Фамилия Имя Отчество"
        if len(parts) == 3:
            # Определяем порядок: если последнее слово выглядит как фамилия (с заглавной буквы,
            # и не является типичным именем), то переставляем
            last_word = parts[2]
            if (last_word[0].isupper() and 
                not last_word.endswith('вич') and not last_word.endswith('вна') and
                len(last_word) > 2):
                # Предполагаем "Имя Отчество Фамилия" -> "Фамилия Имя Отчество"
                return f"{last_word} {parts[0]} {parts[1]}"
            else:
                # Уже в правильном формате или не уверены
                return name
        
        return name
    
    def _matches_abbreviation(self, abbr: str, full_name: str) -> bool:
        """Проверяет, соответствует ли сокращение полному имени"""
        abbr = abbr.replace(' ', '').replace('.', '')
        full_parts = full_name.split()
        
        if len(full_parts) >= 3:
            # Берем первые буквы имени и отчества + фамилию
            expected_abbr = f"{full_parts[1][0]}{full_parts[2][0]}{full_parts[0]}"
            return abbr.lower() == expected_abbr.lower()
        
        return False
    
    def get_employee_name_variants(self, employee: str) -> List[str]:
        """Генерирует варианты имени для поиска"""
        variants = [employee.lower()]
        
        # Разбиваем на части
        parts = employee.split()
        if len(parts) >= 2:
            # Предполагаем, что фамилия - последняя часть
            surname = parts[-1]
            variants.append(surname.lower())
            
            if len(parts) >= 3:
                # Для формата "Имя Отчество Фамилия"
                name = parts[0]
                patronymic = parts[1]
                surname = parts[2]
                
                # Ф.И.О.
                if len(name) > 0 and len(patronymic) > 0 and len(surname) > 0:
                    fio = f"{name[0]}.{patronymic[0]}.{surname}"
                    variants.append(fio.lower())
                    variants.append(f"{name[0]}.{patronymic[0]} {surname}".lower())
                
                # И.О. Фамилия
                io_surname = f"{name[0]}.{patronymic[0]}. {surname}"
                variants.append(io_surname.lower())
                
                # Полное имя
                variants.append(f"{name} {patronymic} {surname}".lower())
                variants.append(f"{name} {surname}".lower())
                variants.append(f"{patronymic} {surname}".lower())
        
        return list(set(variants))  # Удаляем дубликаты

    # ===== АНАЛИЗ СТАТИСТИКИ ПОСТОВ =====
    
    def analyze_posts_by_period(self, period_type: str, start_date: datetime = None, 
                                end_date: datetime = None, metric: str = 'likes') -> List[Dict]:
        """
        Анализирует посты за период по метрике
        
        Args:
            period_type: тип периода (hour, day, week, month, year, all_time)
            start_date: дата начала (если None, используется текущий период)
            end_date: дата конца (если None, вычисляется автоматически)
            metric: метрика для сортировки (likes, comments, shares, views)
        
        Returns:
            Список топ-постов за период
        """
        if start_date is None or end_date is None:
            start_date, end_date = self.period_calc.get_period_range(period_type)
        
        start_str = self.period_calc.format_date(start_date)
        end_str = self.period_calc.format_date(end_date)
        
        # Получаем посты в диапазоне
        posts = self.db.get_posts_by_date_range(start_str, end_str)
        
        # Формируем результаты с метриками
        results = []
        for post in posts:
            original_post_id = post[0]
            post_stats = self.db.get_post_stats(original_post_id)
            if post_stats:
                results.append({
                    'post_id': original_post_id,
                    'date': post[1],
                    'text': post[2][:100] + '...' if len(post[2] or '') > 100 else post[2],
                    'likes': post_stats['likes'],
                    'comments': post_stats['comments'],
                    'shares': post_stats['shares'],
                    'views': post_stats['views'],
                    'total_engagement': post_stats['likes'] + post_stats['comments'] + post_stats['shares']
                })
        
        # Сортируем по метрике
        metric_map = {
            'likes': lambda x: x['likes'],
            'comments': lambda x: x['comments'],
            'shares': lambda x: x['shares'],
            'views': lambda x: x['views'],
            'engagement': lambda x: x['total_engagement']
        }
        
        results.sort(key=metric_map.get(metric, metric_map['likes']), reverse=True)
        return results
    
    def get_top_posts(self, period_type: str, start_date: datetime = None, 
                      end_date: datetime = None, metric: str = 'likes', limit: int = 10) -> List[Dict]:
        """Получает топ постов за период"""
        posts = self.analyze_posts_by_period(period_type, start_date, end_date, metric)
        return posts[:limit]
    
    def analyze_posts_by_period_range(self, custom_start: datetime, custom_end: datetime, 
                                      metric: str = 'likes') -> List[Dict]:
        """Анализирует посты в кастомном диапазоне дат"""
        start_str = self.period_calc.format_date(custom_start)
        end_str = self.period_calc.format_date(custom_end)
        
        posts = self.db.get_posts_by_date_range(start_str, end_str)
        
        results = []
        for post in posts:
            original_post_id = post[0]
            post_stats = self.db.get_post_stats(original_post_id)
            if post_stats:
                results.append({
                    'post_id': original_post_id,
                    'date': post[1],
                    'text': post[2][:100] + '...' if len(post[2] or '') > 100 else post[2],
                    'likes': post_stats['likes'],
                    'comments': post_stats['comments'],
                    'shares': post_stats['shares'],
                    'views': post_stats['views'],
                })
        
        metric_map = {
            'likes': lambda x: x['likes'],
            'comments': lambda x: x['comments'],
            'shares': lambda x: x['shares'],
            'views': lambda x: x['views']
        }
        
        results.sort(key=metric_map.get(metric, metric_map['likes']), reverse=True)
        return results
    
    # ===== АНАЛИЗ СТАТИСТИКИ ВИДЕО И ФОТО =====
    
    def analyze_media_by_period(self, media_type: str, period_type: str, 
                               start_date: datetime = None, end_date: datetime = None,
                               metric: str = 'views') -> List[Dict]:
        """
        Анализирует видео или фото за период
        
        Args:
            media_type: 'photo' или 'video'
            period_type: тип периода
            start_date: дата начала
            end_date: дата конца
            metric: метрика (views, likes, comments, shares)
        
        Returns:
            Список топ-медиафайлов
        """
        if start_date is None or end_date is None:
            start_date, end_date = self.period_calc.get_period_range(period_type)
        
        start_str = self.period_calc.format_date(start_date)
        end_str = self.period_calc.format_date(end_date)
        
        results = self.db.get_top_media_by_period(media_type, period_type, start_str, end_str, metric)
        
        formatted_results = []
        for result in results:
            formatted_results.append({
                'media_key': result[0],
                'type': result[1],
                'metric_value': result[2],
                'date': result[3]
            })
        
        return formatted_results
    
    def get_top_media(self, media_type: str, period_type: str, start_date: datetime = None,
                      end_date: datetime = None, metric: str = 'views', limit: int = 10) -> List[Dict]:
        """Получает топ видео/фото за период"""
        media = self.analyze_media_by_period(media_type, period_type, start_date, end_date, metric)
        return media[:limit]
    
    # ===== АНАЛИЗ СТАТИСТИКИ ПРЕПОДАВАТЕЛЕЙ =====
    
    def analyze_employees_by_period(self, period_type: str, start_date: datetime = None,
                                   end_date: datetime = None, metric: str = 'mention_count',
                                   employees_list: List[str] = None) -> List[Dict]:
        """
        Анализирует упоминания преподавателей за период
        
        Args:
            period_type: тип периода
            start_date: дата начала
            end_date: дата конца
            metric: метрика (mention_count, post_count, etc)
            employees_list: список преподавателей для анализа
        
        Returns:
            Список преподавателей с статистикой
        """
        if start_date is None or end_date is None:
            start_date, end_date = self.period_calc.get_period_range(period_type)
        
        start_str = self.period_calc.format_date(start_date)
        end_str = self.period_calc.format_date(end_date)
        
        if employees_list is None:
            employees_list = []
        
        results = []
        
        for employee in employees_list:
            # Получаем варианты имени для поиска
            name_variants = self.get_employee_name_variants(employee)
            
            # Подсчитываем упоминания
            mention_count = 0
            for variant in name_variants:
                mention_count += self.db.count_employee_mentions(variant, start_str, end_str)
            
            # Подсчитываем посты с преподавателем
            posts = self.db.get_posts_by_date_range(start_str, end_str)
            post_count = 0
            total_likes = 0
            total_views = 0
            
            for post in posts:
                post_text = (post[2] or '') + ' ' + (post[3] or '')
                post_text_lower = post_text.lower()
                
                # Проверяем, содержит ли пост хотя бы один вариант имени
                if any(variant in post_text_lower for variant in name_variants):
                    post_count += 1
                    post_stats = self.db.get_post_stats(post[0])
                    if post_stats:
                        total_likes += post_stats['likes']
                        total_views += post_stats['views']
            
            if mention_count > 0 or post_count > 0:
                results.append({
                    'employee': employee,
                    'mention_count': mention_count,
                    'post_count': post_count,
                    'total_likes': total_likes,
                    'total_views': total_views,
                    'avg_post_likes': total_likes / post_count if post_count > 0 else 0
                })
        
        # Сортируем по метрике
        metric_map = {
            'mention_count': lambda x: x['mention_count'],
            'post_count': lambda x: x['post_count'],
            'total_likes': lambda x: x['total_likes'],
            'total_views': lambda x: x['total_views'],
            'avg_post_likes': lambda x: x['avg_post_likes']
        }
        
        results.sort(key=metric_map.get(metric, metric_map['mention_count']), reverse=True)
        return results
    
    def get_top_employees(self, period_type: str, start_date: datetime = None,
                         end_date: datetime = None, metric: str = 'mention_count',
                         employees_list: List[str] = None, limit: int = 10) -> List[Dict]:
        """Получает топ преподавателей за период"""
        employees = self.analyze_employees_by_period(period_type, start_date, end_date, metric, employees_list)
        return employees[:limit]
    
    # ===== СРАВНЕНИЕ ПЕРИОДОВ =====
    
    def compare_periods(self, period_type: str, count: int = 2, metric: str = 'likes') -> Dict:
        """
        Сравнивает топ-посты между периодами
        
        Args:
            period_type: тип периода
            count: количество последних периодов для сравнения
            metric: метрика для сравнения
        
        Returns:
            Словарь с сравнением
        """
        periods = self.period_calc.get_recent_periods(period_type, count)
        
        comparison = {}
        for i, (start, end) in enumerate(periods):
            period_label = self.period_calc.get_period_label(period_type, start, end)
            top_posts = self.get_top_posts(period_type, start, end, metric, limit=5)
            comparison[period_label] = top_posts
        
        return comparison
    
    # ===== ОБЩАЯ СТАТИСТИКА =====
    
    def get_overall_statistics(self) -> Dict:
        """Получает общую статистику по всему архиву"""
        stats = self.db.get_stats()
        
        # Получаем статистику за все время
        all_posts = self.db.get_posts_by_date_range('2000-01-01', 
                                                    (datetime.now() + timedelta(days=1)).strftime('%Y-%m-%d'))
        
        total_likes = 0
        total_comments = 0
        total_shares = 0
        total_views = 0
        
        for post in all_posts:
            post_stats = self.db.get_post_stats(post[0])
            if post_stats:
                total_likes += post_stats['likes']
                total_comments += post_stats['comments']
                total_shares += post_stats['shares']
                total_views += post_stats['views']
        
        return {
            'total_posts': stats['total'],
            'total_photos': stats['photos'],
            'total_videos': stats['videos'],
            'total_likes': total_likes,
            'total_comments': total_comments,
            'total_shares': total_shares,
            'total_views': total_views,
            'avg_likes_per_post': total_likes / stats['total'] if stats['total'] > 0 else 0,
            'avg_views_per_post': total_views / stats['total'] if stats['total'] > 0 else 0
        }
    
    # ===== СИНХРОНИЗАЦИЯ И ПРОВЕРКА КОНСИСТЕНТНОСТИ =====
    
    def verify_post_consistency(self, original_post_id: int) -> bool:
        """Проверяет наличие поста в БД"""
        return self.db.verify_post_consistency(original_post_id)
    
    def get_statistics_summary(self, period_type: str, start_date: datetime = None,
                              end_date: datetime = None) -> Dict:
        """Получает сводку статистики за период"""
        posts = self.analyze_posts_by_period(period_type, start_date, end_date, 'views')
        
        if not posts:
            return {
                'period': self.period_calc.get_period_label(period_type, start_date or datetime.now(), end_date),
                'total_posts': 0,
                'total_likes': 0,
                'total_views': 0,
                'avg_views': 0
            }
        
        total_likes = sum(p['likes'] for p in posts)
        total_views = sum(p['views'] for p in posts)
        
        return {
            'period': self.period_calc.get_period_label(period_type, start_date or datetime.now(), end_date),
            'total_posts': len(posts),
            'total_likes': total_likes,
            'total_views': total_views,
            'avg_views': total_views / len(posts) if posts else 0,
            'avg_likes': total_likes / len(posts) if posts else 0
        }
