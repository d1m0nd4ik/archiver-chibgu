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
from core.employee_tagger import normalize_hashtag, normalize_person_name

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
        """Считает посты преподавателей по авторству, основанному на хэштегах."""
        if start_date is None or end_date is None:
            start_date, end_date = self.period_calc.get_period_range(period_type)

        start_str = self.period_calc.format_date(start_date)
        end_str = self.period_calc.format_date(end_date)

        results = self.db.get_top_employees_by_period(start_str, end_str, limit=limit or 50)
        if not results:
            return []

        # Поддерживаем разные метрики: пост_count или total_likes
        if metric == 'total_likes':
            results.sort(key=lambda x: x.get('total_likes', 0), reverse=True)
        else:
            results.sort(key=lambda x: x.get('post_count', 0), reverse=True)

        return results[:limit] if limit is not None else results

    def get_top_posts(self, period_type, start_date=None, end_date=None, metric='likes', limit=10):
        return self.analyze_posts_by_period(period_type, start_date, end_date, metric)[:limit]

    @staticmethod
    def _strip_hashtags(text: str) -> str:
        if not text:
            return ''
        cleaned = re.sub(r'#[\wА-Яа-яЁё]+', '', text)
        return re.sub(r'\s+', ' ', cleaned).strip()

    @staticmethod
    def _format_fio_display(name: str) -> str:
        if not name:
            return ''
        return normalize_person_name(name.strip())

    def _lookup_employee_by_hashtag(self, hashtag: str):
        if not hashtag:
            return None
        for candidate in (hashtag, normalize_hashtag(hashtag)):
            emp = self.db.get_employee_by_hashtag(candidate)
            if emp:
                return emp
        return None

    def _resolve_author_fio(self, author_name: str, author_hashtag: str, teacher_hashtag: str) -> str:
        name = (author_name or '').strip()
        if name and not name.startswith('#'):
            return self._format_fio_display(name)
        for tag in (author_hashtag, teacher_hashtag):
            emp = self._lookup_employee_by_hashtag(tag)
            if emp and emp.get('full_name'):
                return self._format_fio_display(emp['full_name'])
        return ''

    def analyze_posts_by_period(self, period_type, start_date=None, end_date=None, metric='likes'):
        if start_date is None or end_date is None:
            start_date, end_date = self.period_calc.get_period_range(period_type)
        start_str, end_str = self.period_calc.format_date(start_date), self.period_calc.format_date(end_date)
        posts = self.db.get_posts_with_author_by_date_range(start_str, end_str)
        if not posts: return []
        
        results = []
        for post in posts:
            pid, date, text = post[0], post[1], post[2] or ""
            post_url = post[4] or ''
            teacher_hashtag = post[5] or ''
            department_hashtag = post[6] or ''
            author_name_raw = post[9] or ''
            author_hashtag = post[10] or ''
            stats = self.db.get_post_stats(pid)
            if stats:
                # Get media paths (for thumbnails) if any
                media_items = self.db.get_attachments_for_post(pid)
                media_paths = [m['media_path'] for m in media_items]
                clean_text = self._strip_hashtags(text)
                preview = clean_text if len(clean_text) <= 300 else clean_text[:300] + '...'
                popularity = (stats.get('likes', 0) + stats.get('comments', 0) + stats.get('shares', 0))
                author_fio = self._resolve_author_fio(author_name_raw, author_hashtag, teacher_hashtag)
                dept_hashtag = post[12] if len(post) > 12 else ''
                display_teacher_tag = teacher_hashtag or author_hashtag or ''
                display_dept_tag = department_hashtag or dept_hashtag or ''
                results.append({
                    'post_id': pid,
                    'date': date,
                    'text': preview,
                    'post_url': post_url,
                    'author_name': author_fio,
                    'teacher_hashtag': display_teacher_tag,
                    'department_hashtag': display_dept_tag,
                    'likes': stats['likes'],
                    'comments': stats['comments'],
                    'shares': stats['shares'],
                    'popularity': popularity,
                    'media_paths': media_paths,
                })
        mm = {
            'likes': lambda x: x['likes'],
            'comments': lambda x: x['comments'],
            'shares': lambda x: x['shares'],
            'popularity': lambda x: x.get('popularity', x.get('likes', 0) + x.get('comments', 0) + x.get('shares', 0))
        }
        results.sort(key=mm.get(metric, mm['likes']), reverse=True)
        return results

    def get_statistics_summary(self, period_type, start_date=None, end_date=None):
        posts = self.analyze_posts_by_period(period_type, start_date, end_date)
        if not posts: return {'period': '...', 'total_posts': 0, 'total_likes': 0, 'total_comments': 0, 'total_shares': 0}
        return {
            'period': self.period_calc.get_period_label(period_type, start_date, end_date),
            'total_posts': len(posts),
            'total_likes': sum(p['likes'] for p in posts),
            'total_comments': sum(p['comments'] for p in posts),
            'total_shares': sum(p['shares'] for p in posts)
        }