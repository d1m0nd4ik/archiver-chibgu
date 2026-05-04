import re
import os
import pandas as pd
from bs4 import BeautifulSoup
import requests

def normalize_name(name):
    """Заменяет ё на е и очищает имя от лишних пробелов"""
    name = name.replace('ё', 'е').replace('Ё', 'Е')
    name = ' '.join(name.split())
    return name.strip()

def extract_employees_from_html(html_content):
    """Извлекает имена сотрудников из HTML-контента"""
    soup = BeautifulSoup(html_content, 'html.parser')
    employees = []
    
    for tag in soup.find_all('td', itemprop='fio'):
        name = tag.get_text(strip=True)
        if name and len(name) > 3:
            employees.append(normalize_name(name))

    tables = soup.find_all('table')
    for table in tables:
        headers = table.find_all('th')
        header_text = ' '.join([h.get_text().lower() for h in headers])
        
        if 'ф.и.о.' in header_text or 'ф.и.о преподавателя' in header_text:
            rows = table.find_all('tr')[1:]
            for row in rows:
                cells = row.find_all('td')
                if len(cells) >= 2:
                    name_cell = cells[1]
                    name = name_cell.get_text(strip=True)
                    name = re.sub(r'<[^>]+>', '', name)
                    name = normalize_name(name)
                    if name and len(name) > 3 and '<' not in name:
                        employees.append(name)

    return employees

def remove_duplicates(employees):
    """Удаляет дубликаты, сохраняя порядок"""
    seen = set()
    unique_employees = []
    for emp in employees:
        if emp not in seen:
            seen.add(emp)
            unique_employees.append(emp)
    return unique_employees

def create_excel_file(employees, filename='employees_unique.xlsx'):
    """Создает Excel-файл с сотрудниками"""
    df = pd.DataFrame({
        '№': range(1, len(employees) + 1),
        'ФИО сотрудника': employees
    })
    with pd.ExcelWriter(filename, engine='openpyxl') as writer:
        df.to_excel(writer, sheet_name='Сотрудники', index=False)
        worksheet = writer.sheets['Сотрудники']
        worksheet.column_dimensions['A'].width = 5
        worksheet.column_dimensions['B'].width = 50
    return filename

def update_employees_from_url(url='https://bgu-chita.ru/sveden/employees', filename='employees_unique.xlsx'):
    """Обновляет список сотрудников с сайта"""
    try:
        response = requests.get(url, headers={
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }, timeout=30)
        response.encoding = 'utf-8'
        html_content = response.text
        
        all_employees = extract_employees_from_html(html_content)
        unique_employees = remove_duplicates(all_employees)
        create_excel_file(unique_employees, filename)
        
        print(f"✓ Обновлено {len(unique_employees)} сотрудников")
        return unique_employees
    except Exception as e:
        print(f"⚠ Ошибка обновления: {e}")
        return []

def extract_keywords_from_text(text, max_tags=10):
    """Извлекает ключевые слова из текста (простая эвристика)"""
    if not text:
        return []
    
    # Стоп-слова (русские)
    stop_words = {
        'и', 'в', 'на', 'с', 'по', 'за', 'под', 'над', 'для', 'от', 'до', 'из',
        'а', 'но', 'или', 'же', 'бы', 'ли', 'то', 'если', 'как', 'что', 'кто',
        'этот', 'тот', 'такой', 'весь', 'сам', 'самый',
        'быть', 'был', 'была', 'было', 'были', 'есть', 'будет', 'будут',
        'я', 'ты', 'он', 'она', 'оно', 'мы', 'вы', 'они', 'меня', 'тебя', 'его', 'её',
        'мой', 'твой', 'свой', 'наш', 'ваш',
        'не', 'ни', 'да', 'нет', 'ну', 'же', 'ли', 'бы',
        'при', 'через', 'после', 'перед', 'между', 'без', 'кроме', 'кроме',
        'уже', 'только', 'очень', 'совсем', 'еще', 'ещё', 'более', 'менее',
        'так', 'также', 'потом', 'затем', 'после', 'перед',
        'год', 'года', 'лет', 'месяц', 'дня', 'час', 'раз', 'место', 'дело', 'время',
        'который', 'какой', 'чей', 'сколько', 'столько',
        'себя', 'себе', 'собой', 'собою',
        'здесь', 'там', 'туда', 'сюда', 'оттуда', 'отсюда',
        'когда', 'где', 'куда', 'откуда', 'почему', 'зачем',
        'хороший', 'новый', 'старый', 'большой', 'маленький', 'первый', 'последний'
    }
    
    # Очищаем текст
    text = text.lower()
    text = re.sub(r'[^\w\sа-яё]', ' ', text)
    words = text.split()
    
    # Фильтруем слова
    keywords = []
    for word in words:
        word = word.strip()
        if (len(word) >= 4 and 
            word not in stop_words and 
            not word.isdigit() and
            len(keywords) < max_tags):
            keywords.append(word)
    
    # Убираем дубликаты, сохраняя порядок
    seen = set()
    unique_keywords = []
    for kw in keywords:
        if kw not in seen:
            seen.add(kw)
            unique_keywords.append(kw)
    
    return unique_keywords[:max_tags]

class EmployeeTagger:
    """Умный поиск преподавателей по ФИО в тексте + NLP теги"""
    
    def __init__(self, excel_path='employees_unique.xlsx'):
        self.employees = []
        
        if not os.path.exists(excel_path):
            print("⚠️ Файл employees_unique.xlsx не найден. Создаем...")
            try:
                update_employees_from_url(filename=excel_path)
            except Exception as e:
                print(f"❌ Не удалось создать файл: {e}")
                print("Запустите pars.py вручную для создания файла")
        
        self.load_data(excel_path)
    
    def load_data(self, excel_path):
        """Загрузка и парсинг списка преподавателей"""
        try:
            if not os.path.exists(excel_path):
                print(f"⚠️ Файл {excel_path} не найден")
                return

            df = pd.read_excel(excel_path)
            full_names = df['ФИО сотрудника'].tolist()
            
            for full_name in full_names:
                if pd.isna(full_name) or len(full_name) < 5:
                    continue
                
                parts = full_name.strip().split()
                if len(parts) >= 1:
                    surname = parts[0]
                    name = parts[1] if len(parts) > 1 else ""
                    patronymic = parts[2] if len(parts) > 2 else ""
                    
                    self.employees.append({
                        'original': full_name,
                        'surname': surname,
                        'name': name,
                        'patronymic': patronymic
                    })
        except Exception as e:
            print(f"Ошибка загрузки преподавателей: {e}")

    def get_all_tags(self, text, include_keywords=True):
        """Получает все теги: преподаватели + ключевые слова"""
        if not text:
            return []
        
        tags = set()
        
        # 1. Теги преподавателей
        employee_tags = self.get_hashtags(text)
        tags.update(employee_tags)
        
        # 2. Ключевые слова из текста
        if include_keywords:
            keywords = extract_keywords_from_text(text, max_tags=15)
            for kw in keywords:
                tags.add(f"#{kw}")
        
        return sorted(list(tags))

    def get_hashtags(self, text):
        """Ищет совпадения в тексте и возвращает хэштеги преподавателей"""
        if not text:
            return []

        search_text = text.lower().replace('ё', 'е')
        tags = set()
        
        for emp in self.employees:
            surname = emp['surname'].lower()
            name = emp['name'].lower()
            patronymic = emp['patronymic'].lower()
            
            # 1. Полное ФИО
            if patronymic:
                full_variant = f"{surname} {name} {patronymic}"
                if self._check_word_boundary(search_text, full_variant):
                    tags.add(f"#{surname}_{name}_{patronymic}")
            
            # 2. Имя Фамилия
            if name:
                variant_2 = f"{surname} {name}"
                if self._check_word_boundary(search_text, variant_2):
                    tags.add(f"#{surname}_{name}")
                
                variant_3 = f"{name} {surname}"
                if self._check_word_boundary(search_text, variant_3):
                    tags.add(f"#{surname}_{name}")

            # 3. Просто Фамилия
            if self._check_word_boundary(search_text, surname):
                tags.add(f"#{surname}")

        return list(tags)

    def _check_word_boundary(self, text, phrase):
        """Проверяет наличие фразы в тексте"""
        words = phrase.split()
        if len(words) > 1:
            return phrase in text
        
        if len(phrase) > 4:
            return phrase in text
            
        return False