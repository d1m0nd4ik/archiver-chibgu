"""
Модуль для анализа статистики постов и преподавателей.
ИСПРАВЛЕНО: pymorphy3 API (get_lexeme вместо get_lexemes).
"""
import re
from datetime import datetime
from typing import Dict, List, Set
import pymorphy3
from core.logging_config import logger
from core.database import Database
from core.period_calculator import PeriodCalculator

class StatisticsAnalyzer:
    def __init__(self):
        self.db = Database()
        self.period_calc = PeriodCalculator()
        self.morph = pymorphy3.MorphAnalyzer()

    def _get_forms(self, word: str) -> Set[str]:
        """Генерирует все формы слова через pymorphy3"""
        if not word: return set()
        # Базовые формы
        forms = {word.lower(), word.lower().replace('ё','е')}
        try:
            parsed = self.morph.parse(word)
            if parsed:
                # get_lexeme принимает объект Parse[0], а не строку
                for lex in self.morph.get_lexeme(parsed[0]):
                    forms.add(lex.lower())
                    forms.add(lex.lower().replace('ё','е'))
        except Exception:
            pass
        return forms

    def _prepare_employee(self, full_name: str) -> dict:
        """Подготавливает данные сотрудника для поиска"""
        parts = full_name.strip().split()
        if len(parts) < 2: return {}
        
        surname, first_name = parts[0], parts[1]
        patronymic = parts[2] if len(parts) > 2 else ""

        s_forms = self._get_forms(surname)
        n_forms = self._get_forms(first_name)
        p_forms = self._get_forms(patronymic) if patronymic else set()
        
        f_init = first_name[0].lower() if first_name else ''
        p_init = patronymic[0].lower() if patronymic else ''
        initials = [f"{f_init}.", f"{f_init}.{p_init}.", f"{f_init}", f"{f_init}.{p_init}"]

        return {
            'display': full_name,
            'surname': surname,
            's_forms': s_forms, 
            'n_forms': n_forms, 
            'p_forms': p_forms,
            'initials': initials
        }

    def _is_mentioned(self, text: str, emp: dict) -> bool:
        """Проверяет упоминание сотрудника через строгий контекст"""
        t = text.lower().replace('ё', 'е')
        
        # 1. Жесткое совпадение: Фамилия + Имя / Имя + Фамилия / Фамилия + И.О.
        pat = rf'\b({"|".join(map(re.escape, emp["s_forms"]))})\W+({"|".join(map(re.escape, emp["n_forms"]))}|{"|".join(map(re.escape, emp["initials"]))})\b'
        if re.search(pat, t): return True
        
        if re.search(rf'\b({"|".join(map(re.escape, emp["n_forms"]))})\W+({"|".join(map(re.escape, emp["s_forms"]))})\b', t): return True
        
        # Если есть отчество, проверяем связку Фамилия + Отчество
        if emp['p_forms'] and re.search(rf'\b({"|".join(map(re.escape, emp["s_forms"]))})\W+({"|".join(map(re.escape, emp["p_forms"]))})\b', t): return True

        # 2. Поиск только по фамилии + проверка контекста
        for sf in emp['s_forms']:
            for m in re.finditer(rf'\b{re.escape(sf)}\b', t):
                ctx = text[max(0, m.start()-50):min(len(text), m.end()+50)]
                ctx_c = ctx.lower().replace('ё', 'е').replace(sf, ' ')
                
                # Наше имя/инициалы в контексте? -> Это ОН
                if any(x in ctx_c for x in emp['n_forms']) or any(x in ctx_c for x in emp['initials']): return True
                if emp['p_forms'] and any(x in ctx_c for x in emp['p_forms']): return True
                
                # Ищем другие capitalized-слова в контексте (потенциальные чужие имена)
                others = re.findall(r'\b([А-ЯЁ][а-яё]+)\b', ctx)
                conflict = False
                for o in others:
                    o_n = o.lower().replace('ё', 'е')
                    # Если слово не принадлежит нашему сотруднику и длина > 2
                    if len(o_n) > 2 and o_n not in emp['n_forms'] and o_n not in emp['p_forms'] and o_n not in emp['s_forms']:
                        conflict = True
                        break
                if conflict:
                    continue  # Ложное срабатывание, пропускаем
                return True  # Контекст чист -> считаем совпадением
        return False

    def get_top_employees(self, period_type: str, start_date: datetime = None,
                          end_date: datetime = None, metric: str = 'post_count', 
                          limit: int = None) -> List[Dict]:
        """Считает упоминания преподавателей из БД в постах за период."""
        if start_date is None or end_date is None:
            start_date, end_date = self.period_calc.get_period_range(period_type)

        start_str = self.period_calc.format_date(start_date)
        end_str = self.period_calc.format_date(end_date)

        # 1. Загружаем эталонный список из БД
        db_emps = self.db.get_all_employees()
        if not db_emps: return []
        
        # 2. Готовим профили для поиска
        profiles = [self._prepare_employee(name) for name in db_emps if name and len(name.strip())>2]

        # 3. Загружаем посты
        posts = self.db.get_posts_by_date_range(start_str, end_str)
        if not posts: return []

        results = []
        # Кэш текстов постов для скорости
        post_texts = [(post[0], (post[2] or '') + " " + (post[3] or '')) for post in posts]

        # 4. Ищем совпадения
        for emp in profiles:
            if not emp: continue
            matched_post_ids = set()
            for pid, text in post_texts:
                if self._is_mentioned(text, emp):
                    matched_post_ids.add(pid)
            
            if matched_post_ids:
                # Считаем лайки/просмотры только для найденных постов
                total_likes = total_views = 0
                for pid in matched_post_ids:
                    stats = self.db.get_post_stats(pid)
                    if stats:
                        total_likes += stats.get('likes', 0)
                        total_views += stats.get('views', 0)

                results.append({
                    'employee': emp['display'],
                    'post_count': len(matched_post_ids),
                    'total_likes': total_likes,
                    'total_views': total_views
                })

        # 5. Сортируем по количеству постов (убывание)
        sort_key = metric if metric in ('total_likes', 'total_views') else 'post_count'
        results.sort(key=lambda x: x.get(sort_key, 0), reverse=True)
        
        return results[:limit] if limit is not None else results

    def get_top_posts(self, period_type, start_date=None, end_date=None, metric='likes', limit=10):
        return self.analyze_posts_by_period(period_type, start_date, end_date, metric)[:limit]

    def analyze_posts_by_period(self, period_type, start_date=None, end_date=None, metric='likes'):
        if start_date is None or end_date is None:
            start_date, end_date = self.period_calc.get_period_range(period_type)
        start_str, end_str = self.period_calc.format_date(start_date), self.period_calc.format_date(end_date)
        posts = self.db.get_posts_by_date_range(start_str, end_str)
        if not posts: return []
        
        results = []
        for post in posts:
            pid, date, text = post[0], post[1], post[2] or ""
            stats = self.db.get_post_stats(pid)
            if stats:
                results.append({
                    'post_id': pid, 'date': date, 'text': text[:100]+'...',
                    'likes': stats['likes'], 'comments': stats['comments'],
                    'shares': stats['shares'], 'views': stats['views']
                })
        mm = {'likes': lambda x: x['likes'], 'views': lambda x: x['views'], 'comments': lambda x: x['comments'], 'shares': lambda x: x['shares']}
        results.sort(key=mm.get(metric, mm['likes']), reverse=True)
        return results

    def get_statistics_summary(self, period_type, start_date=None, end_date=None):
        posts = self.analyze_posts_by_period(period_type, start_date, end_date, 'views')
        if not posts: return {'period': '...', 'total_posts': 0, 'total_likes': 0, 'total_views': 0}
        return {
            'period': self.period_calc.get_period_label(period_type, start_date, end_date),
            'total_posts': len(posts),
            'total_likes': sum(p['likes'] for p in posts),
            'total_views': sum(p['views'] for p in posts)
        }