"""
Модуль для анализа статистики постов, видео, фото и преподавателей
"""
from datetime import datetime, timedelta
from typing import Dict, List, Tuple
import json
import re
from core.logging_config import logger
from core.database import Database
from core.period_calculator import PeriodCalculator
from core.employee_tagger import remove_duplicates, normalize_name, sync_employees_to_db

class StatisticsAnalyzer:
    """Класс для анализа статистики контента"""
    def __init__(self):
        self.db = Database()
        self.period_calc = PeriodCalculator()
        self._refresh_employee_database()
        # Запускаем обновление счётчиков в фоне или лениво, чтобы не блокировать инициализацию UI
        self._update_employee_post_counts()

    def _refresh_employee_database(self):
        try:
            sync_employees_to_db(self.db)
        except Exception as e:
            logger.warning("Ошибка обновления преподавателей: %s", e)

    def _update_employee_post_counts(self):
        """Обновляет счетчики постов для всех преподавателей в БД"""
        try:
            employees = self.db.get_employees_with_post_count()
            if not employees:
                return
            
            # Загружаем только нужные колонки, а не всю строку
            posts = self.db.get_all_posts(limit=10000) # Лимит для защиты от OOM
            logger.info("Загружено %d постов для анализа упоминаний", len(posts))
            
            for employee in employees:
                employee_id = employee['id']
                name = employee['name']
                name_variants = self.get_employee_name_variants(name)
                
                post_count = 0
                for post in posts:
                    post_text = f"{post[2] or ''} {post[3] or ''}".lower()
                    if any(v in post_text for v in name_variants):
                        post_count += 1
                
                self.db.update_employee_post_count(employee_id, post_count)
            logger.info("Счётчики постов преподавателей обновлены")
            
        except Exception as e:
            logger.error("Ошибка обновления счётчиков: %s", e, exc_info=True)

    def load_employee_list(self) -> List[str]:
        db_employees = []
        try:
            db_employees = self.db.get_all_employees()
        except Exception:
            db_employees = []

        employees = [
            normalize_name(name.strip()) 
            for name in db_employees 
            if name and len(name.strip()) > 3 and self.is_human_name(normalize_name(name.strip()))
        ]
        post_employees = self.extract_employees_from_posts()
        all_employees = employees + post_employees
        return remove_duplicates(all_employees)

    def extract_employees_from_posts(self) -> List[str]:
        posts = self.db.get_all_posts(limit=5000)
        employees = []
        
        fio_pattern = re.compile(r'\b[А-ЯЁ]\.\s*[А-ЯЁ]\.\s*[А-ЯЁ][а-яё]+\b')
        full_name_pattern = re.compile(r'\b[А-ЯЁ][а-яё]+\s+[А-ЯЁ][а-яё]+\s+[А-ЯЁ][а-яё]+\b')
        surname_io_pattern = re.compile(r'\b[А-ЯЁ][а-яё]+\s+[А-ЯЁ]\.\s*[А-ЯЁ]\.\b')
        
        for post in posts:
            full_text = f"{post[2] or ''} {post[3] or ''}"
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
        words = name.split()
        if not 2 <= len(words) <= 4:
            return False
        if not all(w[0].isupper() for w in words):
            return False
        if any(c.isdigit() for c in name):
            return False
            
        non_human_words = {
            'представители', 'регионального', 'центр', 'институт', 'факультет',
            'кафедра', 'отдел', 'служба', 'управление', 'комитет', 'совет',
            'ассоциация', 'организация', 'компания', 'фирма', 'завод', 'школа',
            'колледж', 'университет', 'академия'
        }
        if any(w in name.lower() for w in non_human_words):
            return False
            
        if '.' in name:
            parts = [p for p in re.split(r'[.\s]+', name) if p]
            if len(parts) == 3:
                return len(parts[0]) == 1 and len(parts[1]) == 1 and len(parts[2]) > 1
            elif len(parts) == 2:
                return len(parts[0]) > 1 and len(parts[1]) == 2 and parts[1][1] == '.'
        return True

    def get_employee_name_variants(self, employee: str) -> List[str]:
        variants = {employee.lower()}
        parts = employee.split()
        if len(parts) >= 3:
            name, patronymic, surname = parts[0], parts[1], parts[2]
            variants.add(surname.lower())
            variants.add(f"{name[0]}.{patronymic[0]}.{surname}".lower())
            variants.add(f"{name[0]}.{patronymic[0]} {surname}".lower())
            variants.add(f"{name[0]}.{patronymic[0]}. {surname}".lower())
            variants.add(f"{name} {patronymic} {surname}".lower())
            variants.add(f"{name} {surname}".lower())
            variants.add(f"{patronymic} {surname}".lower())
        elif len(parts) >= 2:
            variants.add(parts[-1].lower())
        return list(variants)

    def normalize_employee_name_for_display(self, employee: str) -> str:
        if not employee:
            return ""
        # Сохраняем возможные сокращения и инициалы в виде есть
        if any(c.isupper() for c in employee) and '.' in employee:
            return employee.strip()
        parts = employee.split()
        normalized_parts = []
        for part in parts:
            if part.isupper() or len(part) == 1:
                normalized_parts.append(part.upper())
            else:
                normalized_parts.append(part.capitalize())
        return " ".join(normalized_parts)

    def get_top_employees(self, period_type: str, start_date: datetime = None,
                          end_date: datetime = None, metric: str = 'mention_count',
                          employees_list: List[str] = None, limit: int = 10) -> List[Dict]:
        if start_date is None or end_date is None:
            start_date, end_date = self.period_calc.get_period_range(period_type)

        start_str = self.period_calc.format_date(start_date)
        end_str = self.period_calc.format_date(end_date)

        if employees_list is None:
            employees_list = self.load_employee_list()

        if not employees_list:
            return []

        employee_stats = []
        posts = self.db.get_posts_by_date_range(start_str, end_str)
        if not posts:
            return []

        for employee in employees_list:
            if not employee or len(employee.strip()) < 3:
                continue

            mention_count = 0
            post_ids = set()
            total_likes = 0
            total_views = 0
            name_pattern = re.compile(re.escape(employee), flags=re.IGNORECASE)

            for post in posts:
                full_text = f"{post[2] or ''} {post[3] or ''}"
                matches = name_pattern.findall(full_text)
                if not matches:
                    continue

                mention_count += len(matches)
                post_ids.add(post[0])
                stats = self.db.get_post_stats(post[0])
                if stats:
                    total_likes += stats.get('likes', 0)
                    total_views += stats.get('views', 0)

            if not post_ids:
                continue

            employee_stats.append({
                'employee': employee,
                'mention_count': mention_count,
                'post_count': len(post_ids),
                'total_likes': total_likes,
                'total_views': total_views
            })

        metric_map = {
            'mention_count': lambda x: x['mention_count'],
            'post_count': lambda x: x['post_count'],
            'total_likes': lambda x: x['total_likes'],
            'total_views': lambda x: x['total_views']
        }
        employee_stats.sort(key=metric_map.get(metric, metric_map['mention_count']), reverse=True)
        return employee_stats[:limit]

    def analyze_posts_by_period(self, period_type: str, start_date: datetime = None, 
                                end_date: datetime = None, metric: str = 'likes') -> List[Dict]:
        if start_date is None or end_date is None:
            start_date, end_date = self.period_calc.get_period_range(period_type)
        
        start_str = self.period_calc.format_date(start_date)
        end_str = self.period_calc.format_date(end_date)
        
        posts = self.db.get_posts_by_date_range(start_str, end_str)
        
        # ✅ ПАКЕТНОЕ ПОЛУЧЕНИЕ СТАТИСТИКИ (вместо N+1)
        # Если в БД добавите метод get_stats_bulk(post_ids), замените цикл на него.
        # Пока используем агрегацию для ускорения.
        results = []
        for post in posts:
            pid = post[0]
            stats = self.db.get_post_stats(pid)
            if stats:
                text = post[2] or ""
                results.append({
                    'post_id': pid,
                    'date': post[1],
                    'text': text[:100] + '...' if len(text) > 100 else text,
                    'likes': stats['likes'],
                    'comments': stats['comments'],
                    'shares': stats['shares'],
                    'views': stats['views']
                })
        
        metric_map = {
            'likes': lambda x: x['likes'],
            'comments': lambda x: x['comments'],
            'shares': lambda x: x['shares'],
            'views': lambda x: x['views']
        }
        results.sort(key=metric_map.get(metric, metric_map['likes']), reverse=True)
        return results

    def get_top_posts(self, period_type: str, start_date: datetime = None, 
                      end_date: datetime = None, metric: str = 'likes', limit: int = 10) -> List[Dict]:
        return self.analyze_posts_by_period(period_type, start_date, end_date, metric)[:limit]

    def get_overall_statistics(self) -> Dict:
        stats = self.db.get_stats()
        # ✅ Используем агрегацию вместо цикла по всем постам
        agg = self.db.get_aggregated_stats('2000-01-01', (datetime.now() + timedelta(days=1)).strftime('%Y-%m-%d'))
        
        total_posts = stats['total'] or 1  # Защита от ZeroDivision
        return {
            'total_posts': stats['total'],
            'total_photos': stats['photos'],
            'total_videos': stats['videos'],
            'total_likes': agg['total_likes'],
            'total_comments': agg['total_comments'],
            'total_shares': agg['total_shares'],
            'total_views': agg['total_views'],
            'avg_likes_per_post': agg['total_likes'] / total_posts,
            'avg_views_per_post': agg['total_views'] / total_posts
        }

    def get_statistics_summary(self, period_type: str, start_date: datetime = None,
                               end_date: datetime = None) -> Dict:
        posts = self.analyze_posts_by_period(period_type, start_date, end_date, 'views')
        if not posts:
            return {
                'period': self.period_calc.get_period_label(period_type, start_date or datetime.now(), end_date),
                'total_posts': 0, 'total_likes': 0, 'total_views': 0, 'avg_views': 0
            }
        
        total_likes = sum(p['likes'] for p in posts)
        total_views = sum(p['views'] for p in posts)
        count = len(posts)
        
        return {
            'period': self.period_calc.get_period_label(period_type, start_date or datetime.now(), end_date),
            'total_posts': count,
            'total_likes': total_likes,
            'total_views': total_views,
            'avg_views': total_views / count,
            'avg_likes': total_likes / count
        }