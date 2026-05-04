"""
Модуль для расчета временных периодов и преобразования дат
"""

from datetime import datetime, timedelta, date
from typing import Tuple, List, Dict


class PeriodCalculator:
    """Класс для работы с временными периодами"""
    
    PERIOD_TYPES = {
        'hour': 'Час',
        'half_day': 'Пол дня',
        'day': 'День',
        'week': 'Неделя',
        'month': 'Месяц',
        'half_year': 'Пол года',
        'year': 'Год',
        'all_time': 'Все время'
    }
    
    @staticmethod
    def parse_date(date_str: str) -> datetime:
        """Парсит дату из различных форматов"""
        formats = ['%Y-%m-%d', '%d.%m.%Y', '%Y-%m-%d %H:%M:%S', '%d.%m.%Y %H:%M:%S']
        for fmt in formats:
            try:
                return datetime.strptime(date_str, fmt)
            except ValueError:
                continue
        raise ValueError(f"Не удалось распарсить дату: {date_str}")
    
    @staticmethod
    def format_date(dt: datetime, date_only: bool = True) -> str:
        """Форматирует дату в строку"""
        if date_only:
            return dt.strftime('%Y-%m-%d')
        return dt.strftime('%Y-%m-%d %H:%M:%S')
    
    @staticmethod
    def get_period_range(period_type: str, reference_date: datetime = None) -> Tuple[datetime, datetime]:
        """Получает начало и конец периода"""
        if reference_date is None:
            reference_date = datetime.now()
        
        if period_type == 'hour':
            start = reference_date.replace(minute=0, second=0, microsecond=0)
            end = start + timedelta(hours=1)
        
        elif period_type == 'half_day':
            # Первая половина: 00:00-11:59, вторая: 12:00-23:59
            hour = reference_date.hour
            start = reference_date.replace(second=0, microsecond=0)
            if hour < 12:
                start = start.replace(hour=0, minute=0)
                end = start.replace(hour=12)
            else:
                start = start.replace(hour=12, minute=0)
                end = (start + timedelta(days=1)).replace(hour=0, minute=0)
        
        elif period_type == 'day':
            start = reference_date.replace(hour=0, minute=0, second=0, microsecond=0)
            end = start + timedelta(days=1)
        
        elif period_type == 'week':
            # Неделя: понедельник-воскресенье
            start = reference_date.replace(hour=0, minute=0, second=0, microsecond=0)
            start = start - timedelta(days=start.weekday())  # К понедельнику
            end = start + timedelta(days=7)
        
        elif period_type == 'month':
            start = reference_date.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            if start.month == 12:
                end = start.replace(year=start.year + 1, month=1)
            else:
                end = start.replace(month=start.month + 1)
        
        elif period_type == 'half_year':
            # Первая половина: янв-июнь, вторая: июль-декабрь
            start = reference_date.replace(hour=0, minute=0, second=0, microsecond=0)
            if start.month <= 6:
                start = start.replace(month=1, day=1)
                end = start.replace(month=7)
            else:
                start = start.replace(month=7, day=1)
                end = start.replace(year=start.year + 1, month=1, day=1)
        
        elif period_type == 'year':
            start = reference_date.replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
            end = start.replace(year=start.year + 1)
        
        elif period_type == 'all_time':
            # За все время: с 2000 года до текущего момента
            start = datetime(2000, 1, 1)
            end = datetime.now() + timedelta(days=1)
        
        else:
            raise ValueError(f"Неизвестный тип периода: {period_type}")
        
        return start, end
    
    @staticmethod
    def get_period_label(period_type: str, start_date: datetime, end_date: datetime) -> str:
        """Возвращает человеческое описание периода"""
        start_str = start_date.strftime('%d.%m.%Y')
        end_str = (end_date - timedelta(days=1)).strftime('%d.%m.%Y')
        
        label = PeriodCalculator.PERIOD_TYPES.get(period_type, period_type)
        return f"{label}: {start_str} - {end_str}"
    
    @staticmethod
    def get_all_periods(start_year: int = 2020, end_year: int = None) -> Dict[str, List[Tuple[datetime, datetime]]]:
        """Генерирует список всех периодов для анализа"""
        if end_year is None:
            end_year = datetime.now().year
        
        periods = {}
        now = datetime.now()
        
        # Часы последних 7 дней
        periods['hour'] = []
        for i in range(168):  # 7 дней * 24 часа
            end = now - timedelta(hours=i)
            start = end - timedelta(hours=1)
            periods['hour'].append((start, end))
        
        # Половины дней последних 30 дней
        periods['half_day'] = []
        for i in range(60):
            current = now - timedelta(days=i // 2)
            start_half, end_half = PeriodCalculator.get_period_range('half_day', current)
            if (start_half, end_half) not in periods['half_day']:
                periods['half_day'].append((start_half, end_half))
        
        # Дни за последний год
        periods['day'] = []
        for i in range(365):
            current = now - timedelta(days=i)
            start, end = PeriodCalculator.get_period_range('day', current)
            periods['day'].append((start, end))
        
        # Недели за последние 2 года
        periods['week'] = []
        for i in range(104):
            current = now - timedelta(weeks=i)
            start, end = PeriodCalculator.get_period_range('week', current)
            if (start, end) not in periods['week']:
                periods['week'].append((start, end))
        
        # Месяцы за последние 5 лет
        periods['month'] = []
        for year in range(end_year, start_year - 1, -1):
            for month in range(12, 0, -1):
                dt = datetime(year, month, 1)
                start, end = PeriodCalculator.get_period_range('month', dt)
                periods['month'].append((start, end))
        
        # Половины лет за последние 10 лет
        periods['half_year'] = []
        for year in range(end_year, end_year - 10, -1):
            # Вторая половина
            dt = datetime(year, 9, 1)
            start, end = PeriodCalculator.get_period_range('half_year', dt)
            periods['half_year'].append((start, end))
            # Первая половина
            dt = datetime(year, 3, 1)
            start, end = PeriodCalculator.get_period_range('half_year', dt)
            periods['half_year'].append((start, end))
        
        # Годы
        periods['year'] = []
        for year in range(end_year, start_year - 1, -1):
            dt = datetime(year, 1, 1)
            start, end = PeriodCalculator.get_period_range('year', dt)
            periods['year'].append((start, end))
        
        # За все время
        periods['all_time'] = [(datetime(2000, 1, 1), now)]
        
        return periods
    
    @staticmethod
    def get_recent_periods(period_type: str, count: int = 5) -> List[Tuple[datetime, datetime]]:
        """Получает последние N периодов указанного типа"""
        now = datetime.now()
        periods = []
        
        if period_type == 'day':
            for i in range(count):
                current = now - timedelta(days=i)
                start, end = PeriodCalculator.get_period_range('day', current)
                periods.append((start, end))
        
        elif period_type == 'week':
            for i in range(count):
                current = now - timedelta(weeks=i)
                start, end = PeriodCalculator.get_period_range('week', current)
                if (start, end) not in periods:
                    periods.append((start, end))
        
        elif period_type == 'month':
            for i in range(count):
                current = now - timedelta(days=30 * i)
                start, end = PeriodCalculator.get_period_range('month', current)
                if (start, end) not in periods:
                    periods.append((start, end))
        
        elif period_type == 'year':
            for i in range(count):
                year = now.year - i
                dt = datetime(year, 1, 1)
                start, end = PeriodCalculator.get_period_range('year', dt)
                periods.append((start, end))
        
        return periods
