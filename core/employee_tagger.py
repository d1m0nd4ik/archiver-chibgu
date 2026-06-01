import os
import re
import time
import datetime
from urllib.parse import urljoin

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from bs4 import BeautifulSoup
import pymorphy3
from core.logging_config import logger
from core.database import Database
from core.name_normalizer import normalize_and_reorder

try:
    from natasha import Segmenter, NewsEmbedding, NewsMorphTagger, NewsNERTagger, Doc
    NATASHA_AVAILABLE = True
except ImportError:
    NATASHA_AVAILABLE = False


def normalize_name(value: str) -> str:
    if not value:
        return ''
    return value.replace('ё', 'е').replace('Ё', 'Е').strip()


def normalize_hashtag(value: str) -> str:
    if not value:
        return ''
    value = value.strip()
    if not value.startswith('#'):
        value = f"#{value}"
    value = value.replace('ё', 'е').replace('Ё', 'Е')
    return re.sub(r'[^#A-Za-zА-Яа-яЁё0-9_]', '', value)


def _slugify_word(value: str) -> str:
    return re.sub(r'[^A-Za-zА-Яа-яЁё0-9]', '', value)


def _ensure_unique_hashtag(base: str, existing_tags=None) -> str:
    if existing_tags is None:
        existing_tags = set()
    normalized = normalize_hashtag(base)
    if normalized.lower() not in {h.lower() for h in existing_tags}:
        return normalized
    counter = 1
    while True:
        candidate = normalize_hashtag(f"{base}_{counter}")
        if candidate.lower() not in {h.lower() for h in existing_tags}:
            return candidate
        counter += 1


def make_department_hashtag(department_name: str, existing_hashtags=None) -> str:
    if not department_name:
        return ''
    name = normalize_name(department_name)
    name = re.sub(r'[^A-Za-zА-Яа-яЁё0-9\s_]', ' ', name)
    parts = [p for p in re.split(r'[\s_]+', name) if p]
    if not parts:
        return ''
    parts = [p.capitalize() for p in parts]
    base = '#' + '_'.join(parts)
    return _ensure_unique_hashtag(base, existing_hashtags)


def make_teacher_hashtag(full_name: str, existing_hashtags=None) -> str:
    if not full_name:
        return ''
    full_name = normalize_name(full_name)
    parts = [p for p in full_name.split() if p]
    if not parts:
        return ''
    surname = _slugify_word(parts[0]).capitalize()
    firstname = _slugify_word(parts[1]) if len(parts) > 1 else ''
    patronymic = _slugify_word(parts[2]) if len(parts) > 2 else ''
    if firstname:
        if patronymic:
            base = f"#{surname}_{firstname[0].upper()}_{patronymic[0].upper()}"
        else:
            base = f"#{surname}_{firstname[0].upper()}"
    else:
        base = f"#{surname}"
    return _ensure_unique_hashtag(base, existing_hashtags)


def is_full_name_text(text: str) -> bool:
    if not text or len(text) < 5:
        return False
    parts = [p for p in re.split(r'[\s,;]+', text.strip()) if p]
    if len(parts) < 2 or len(parts) > 4:
        return False
    # Reject known non-name tokens that often appear on pages
    noise_tokens = {
        'международный','новость','студент','выпускник','информация','фотогалерея','учебный',
        'олимпиада','конкурс','расписание','лаборатория','публикация','фотогалерея','документ',
        'абитуриент','проект','галерея','бриф','трудоустройство','сотрудник','отдел','услуга'
    }
    for part in parts:
        low = part.lower().replace('ё', 'е')
        if low in noise_tokens:
            return False
        if not re.match(r'^[А-ЯЁ][а-яё]+$', part):
            return False
    return True


def normalize_person_name(full_name: str) -> str:
    if not full_name:
        return ''
    value = normalize_name(full_name)
    value = re.sub(r'\s+', ' ', value).strip()
    parts = []
    for part in value.split(' '):
        if not part:
            continue
        if len(part) == 1:
            parts.append(part.upper())
        else:
            parts.append(part[0].upper() + part[1:].lower())
    return ' '.join(parts)


def extract_department_employee_names(soup: BeautifulSoup) -> list:
    names = []
    seen = set()
    selectors = [
        '.view-pps-list .views-field-title a',
        '.view-dept-list .views-field-title a',
        '.views-field-field-dept-list-vname a',
        '.views-field-title a',
        '.view-content .item-list ol li a',
        '.views-row a'
    ]
    for selector in selectors:
        for a in soup.select(selector):
            text = normalize_person_name(a.get_text(strip=True))
            if not text or text in seen:
                continue
            if is_full_name_text(text):
                seen.add(text)
                names.append(text)
    return names


DEPARTMENTS_INDEX_URL = 'https://bgu-chita.ru/institute/departments'
DEPARTMENTS_INDEX_FALLBACK_URLS = (
    'http://bgu-chita.ru/institute/departments',
)
COLLEGE_DEPARTMENT_NAME = 'Колледж'
COLLEGE_TEACHERS_URL = 'http://college.bgu-chita.ru/college/teachers/'

_HTTP_SESSION = None
_BROWSER_HEADERS = {
    'User-Agent': (
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
        'AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    ),
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    'Accept-Language': 'ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7',
}


def _get_http_session() -> requests.Session:
    global _HTTP_SESSION
    if _HTTP_SESSION is None:
        session = requests.Session()
        session.headers.update(_BROWSER_HEADERS)
        retry = Retry(
            total=3,
            connect=3,
            read=3,
            backoff_factor=1.5,
            status_forcelist=(429, 500, 502, 503, 504),
            allowed_methods=frozenset(['GET', 'HEAD']),
        )
        adapter = HTTPAdapter(max_retries=retry)
        session.mount('https://', adapter)
        session.mount('http://', adapter)
        _HTTP_SESSION = session
    return _HTTP_SESSION


def extract_departments_from_index(html_content: str, base_url: str) -> list:
    """Извлекает кафедры со страницы списка: название и URL каждой кафедры отдельно."""
    soup = BeautifulSoup(html_content, 'lxml')
    departments = []
    seen_urls = set()

    def add_department(name: str, href: str):
        if not name or not href:
            return
        if not re.search(r'/node/\d+', href):
            return
        url = urljoin(base_url, href).rstrip('/')
        if url in seen_urls:
            return
        seen_urls.add(url)
        departments.append({'name': normalize_name(name.strip()), 'url': url})

    for row in soup.select('.view-all-kaf table.views-table tbody tr'):
        dept_cell = row.select_one('td.views-field-field-dept-list-vname')
        faculty_cell = row.select_one('td.views-field.views-field-title')

        nested_depts = []
        if dept_cell:
            for anchor in dept_cell.select('.view-dept-list .views-field-title a[href*="/node/"]'):
                text = anchor.get_text(strip=True)
                href = anchor.get('href', '').strip()
                if text and href:
                    nested_depts.append((text, href))

        if nested_depts:
            for text, href in nested_depts:
                add_department(text, href)
        elif faculty_cell:
            for anchor in faculty_cell.select('a[href*="/node/"]'):
                text = anchor.get_text(strip=True)
                href = anchor.get('href', '').strip()
                if text and href and re.search(r'кафедр', text, re.IGNORECASE):
                    add_department(text, href)

    if not departments:
        for anchor in soup.select('.view-dept-list .views-field-title a[href*="/node/"]'):
            text = anchor.get_text(strip=True)
            href = anchor.get('href', '').strip()
            if text and href:
                add_department(text, href)

    return departments


def extract_department_links(html_content: str, base_url: str) -> list:
    """Совместимость: только URL кафедр."""
    return [item['url'] for item in extract_departments_from_index(html_content, base_url)]


def extract_college_teachers(html_content: str) -> list:
    """Преподаватели колледжа со страницы /college/teachers/."""
    soup = BeautifulSoup(html_content, 'lxml')
    names = []
    seen = set()
    for anchor in soup.select('ul.lcp_catlist li a'):
        name = anchor.get('title') or anchor.get_text(strip=True)
        name = normalize_person_name(normalize_name(name))
        if not name or name in seen:
            continue
        if is_full_name_text(name):
            seen.add(name)
            names.append(name)
    return sorted(names)


def extract_department_page(html_content: str, page_url: str) -> tuple:
    soup = BeautifulSoup(html_content, 'lxml')
    department_name = ''
    for selector in ('h1.title', 'h1.page-title', 'h1', '.page-header h1'):
        title_tag = soup.select_one(selector)
        if title_tag:
            candidate = normalize_name(title_tag.get_text(strip=True))
            if candidate and len(candidate) > 3:
                department_name = candidate
                break
    if not department_name:
        department_name = page_url

    content_root = soup.select_one('.view-pps-list') or soup.select_one('#content') or soup.select_one('main') or soup
    employees = extract_department_employee_names(content_root if hasattr(content_root, 'select') else soup)

    if not employees:
        for element in soup.find_all(attrs={'itemprop': 'fio'}):
            name = normalize_name(element.get_text(strip=True))
            if is_full_name_text(name):
                employees.append(name)

    if not employees:
        for row in soup.find_all('tr'):
            cells = [c.get_text(strip=True) for c in row.find_all(['td', 'th'])]
            for candidate in cells:
                candidate = normalize_name(candidate)
                if is_full_name_text(candidate):
                    employees.append(candidate)

    if not employees:
        for li in soup.find_all('li'):
            candidate = normalize_name(li.get_text(strip=True))
            if is_full_name_text(candidate):
                employees.append(candidate)

    if not employees:
        text = soup.get_text(separator=' ', strip=True)
        for match in re.findall(r'([А-ЯЁ][а-яё]+\s+[А-ЯЁ][а-яё]+(?:\s+[А-ЯЁ][а-яё]+)?)', text):
            candidate = normalize_name(match)
            if is_full_name_text(candidate):
                employees.append(candidate)

    return department_name, sorted(set(employees))


def fetch_page(url: str, retries: int = 3) -> str:
    """Загружает HTML-страницу с повторами при сетевых сбоях."""
    session = _get_http_session()
    last_error = None
    for attempt in range(1, retries + 1):
        try:
            response = session.get(url, timeout=(20, 120), allow_redirects=True)
            response.raise_for_status()
            if not response.encoding or response.encoding.lower() in ('iso-8859-1', 'ascii'):
                response.encoding = response.apparent_encoding or 'utf-8'
            return response.text
        except requests.RequestException as error:
            last_error = error
            if attempt < retries:
                time.sleep(2 * attempt)
    raise last_error


def fetch_departments_index(progress_callback=None) -> tuple:
    """Шаг 1: загрузить страницу со списком кафедр и распарсить её."""
    candidates = [DEPARTMENTS_INDEX_URL, *DEPARTMENTS_INDEX_FALLBACK_URLS]
    last_error = None
    for index_url in candidates:
        try:
            if progress_callback:
                progress_callback(f'Шаг 1/3: загрузка списка кафедр — {index_url}')
            html = fetch_page(index_url)
            departments = extract_departments_from_index(html, index_url)
            if departments:
                if progress_callback:
                    progress_callback(f'Найдено кафедр: {len(departments)}')
                return departments, index_url
            last_error = RuntimeError('На странице не найдены кафедры.')
        except Exception as error:
            last_error = error
            if progress_callback:
                progress_callback(f'Не удалось загрузить {index_url}: {error}')
    raise RuntimeError(f'Не удалось получить список кафедр: {last_error}')


def _upsert_department_employees(db, department, employees, source_url, used_employee_hashtags, fetched_names, lines, progress_callback):
    for full_name in employees:
        clean_full_name = normalize_person_name(full_name)
        if not clean_full_name:
            continue
        normalized_full_name = clean_full_name.lower().replace('ё', 'е')
        fetched_names.add(normalized_full_name)

        parts = clean_full_name.split()
        surname = parts[0] if len(parts) > 0 else ''
        firstname = parts[1] if len(parts) > 1 else ''
        patronymic = parts[2] if len(parts) > 2 else ''
        teacher_hashtag = make_teacher_hashtag(clean_full_name, used_employee_hashtags)
        used_employee_hashtags.add(teacher_hashtag)

        db.upsert_employee(
            full_name=clean_full_name,
            normalized_name=normalized_full_name,
            surname=surname,
            firstname=firstname,
            patronymic=patronymic,
            hashtag=teacher_hashtag,
            department_id=department['id'],
            source_url=source_url
        )
        msg = f"    Преподаватель: {clean_full_name} ({teacher_hashtag})"
        lines.append(msg)
        if progress_callback:
            try:
                progress_callback(msg)
            except Exception:
                pass


def sync_departments_to_db(db: Database = None, main_url: str = None, extra_urls: list = None, progress_callback=None) -> dict:
    """Синхронизирует кафедры и преподавателей в БД.

    Порядок:
    1) страница со списком кафедр → парсинг всех кафедр;
    2) для каждой кафедры — страница кафедры → преподаватели;
    3) страница колледжа → преподаватели колледжа.
    """
    db = db or Database()
    index_url = main_url or DEPARTMENTS_INDEX_URL
    log_path = os.path.join(os.getcwd(), 'sync_log.txt')
    lines = []
    synced_departments = 0
    dept_errors = 0
    college_synced = False

    def emit(message: str):
        lines.append(message)
        if progress_callback:
            try:
                progress_callback(message)
            except Exception:
                pass

    try:
        if extra_urls:
            emit('Шаг 1/3: используется заданный список URL кафедр')
            departments = [{'name': None, 'url': url.strip()} for url in dict.fromkeys(extra_urls) if url.strip()]
            if not departments:
                raise RuntimeError('Список URL кафедр пуст.')
            emit(f'Кафедр в списке: {len(departments)}')
        else:
            departments, index_url = fetch_departments_index(progress_callback=emit)

        used_department_hashtags = {d['hashtag'] for d in db.get_departments() if d.get('hashtag')}
        used_employee_hashtags = {e['hashtag'] for e in db.get_all_employee_details() if e.get('hashtag')}
        fetched_names = set()
        total = len(departments)

        emit(f'Шаг 2/3: загрузка преподавателей по {total} кафедрам')
        for index, dept_info in enumerate(departments, start=1):
            url = dept_info['url']
            dept_title = dept_info.get('name') or url
            try:
                emit(f'  [{index}/{total}] {dept_title}')
                department_html = fetch_page(url)
                page_name, employees = extract_department_page(department_html, url)
                department_name = dept_info.get('name') or page_name
                department_name = normalize_name(department_name)
                department_hashtag = make_department_hashtag(department_name, used_department_hashtags)
                used_department_hashtags.add(department_hashtag)
                department = db.upsert_department(department_name, hashtag=department_hashtag, url=url)
                if not department:
                    continue
                synced_departments += 1
                emit(f"    Кафедра сохранена: {department_name} ({department_hashtag}), преподавателей: {len(employees)}")
                _upsert_department_employees(
                    db, department, employees, url,
                    used_employee_hashtags, fetched_names, lines, progress_callback
                )
            except Exception as error:
                dept_errors += 1
                emit(f'    Ошибка: {error}')

        emit(f'Шаг 3/3: загрузка колледжа — {COLLEGE_TEACHERS_URL}')
        try:
            college_html = fetch_page(COLLEGE_TEACHERS_URL)
            college_employees = extract_college_teachers(college_html)
            college_hashtag = make_department_hashtag(COLLEGE_DEPARTMENT_NAME, used_department_hashtags)
            used_department_hashtags.add(college_hashtag)
            college_dept = db.upsert_department(
                COLLEGE_DEPARTMENT_NAME, hashtag=college_hashtag, url=COLLEGE_TEACHERS_URL
            )
            if college_dept and college_employees:
                college_synced = True
                synced_departments += 1
                emit(f'    Колледж: {len(college_employees)} преподавателей')
                _upsert_department_employees(
                    db, college_dept, college_employees, COLLEGE_TEACHERS_URL,
                    used_employee_hashtags, fetched_names, lines, progress_callback
                )
            else:
                emit('    Колледж: преподаватели не найдены на странице')
        except Exception as error:
            emit(f'    Ошибка колледжа: {error}')

        if fetched_names:
            db.delete_employees_not_in_list(list(fetched_names))
            emit(f'Удалены устаревшие записи. Всего преподавателей на сайте: {len(fetched_names)}')

        summary = (
            f'Готово: кафедр {synced_departments}, преподавателей {len(fetched_names)}, '
            f'ошибок кафедр {dept_errors}, колледж {"да" if college_synced else "нет"}'
        )
        emit(summary)

        with open(log_path, 'a', encoding='utf-8') as log_file:
            log_file.write('\n'.join(lines) + '\n')

        if synced_departments == 0 and not fetched_names:
            return {
                'success': False,
                'error': 'Не удалось загрузить ни одной кафедры и ни одного преподавателя.',
                'details': lines,
            }

        return {
            'success': True,
            'details': lines,
            'departments': synced_departments,
            'employees': len(fetched_names),
            'dept_errors': dept_errors,
            'college_synced': college_synced,
        }

    except Exception as error:
        error_message = f"Sync error: {error}"
        logger.error(error_message, exc_info=True)
        emit(f'Критическая ошибка: {error}')
        with open(log_path, 'a', encoding='utf-8') as log_file:
            log_file.write('\n'.join(lines) + '\n')
        return {'success': False, 'error': str(error), 'details': lines}


def ensure_employees_loaded(db: Database = None, force_sync: bool = False) -> bool:
    """Проверяет наличие справочника в БД. Синхронизация только при force_sync=True."""
    db = db or Database()
    if force_sync:
        result = sync_departments_to_db(db)
        return result.get('success', False)
    return bool(db.get_all_employee_details())


def sync_departments_from_list(urls: list, db: Database = None) -> dict:
    """Синхронизирует кафедры, используя явный список URL (node-страницы)."""
    db = db or Database()
    return sync_departments_to_db(db, extra_urls=urls)


class EmployeeTagger:
    def __init__(self, db: Database = None, refresh_on_init: bool = False):
        self.db = db or Database()
        self.morph = pymorphy3.MorphAnalyzer()
        self.natasha_ready = False
        self.profiles = []
        self.name_index = {}
        self.hashtag_index = {}
        self.employee_by_normalized_name = {}

        if NATASHA_AVAILABLE:
            try:
                emb = NewsEmbedding()
                self.segmenter = Segmenter()
                self.morph_tagger = NewsMorphTagger(emb)
                self.ner_tagger = NewsNERTagger(emb)
                self.natasha_ready = True
            except Exception as error:
                logger.warning("Natasha initialization failed: %s", error)

        self._load_db()
        if refresh_on_init:
            ensure_employees_loaded(self.db, force_sync=True)
            self._load_db()

        if not self.profiles:
            logger.warning(
                "Список преподавателей пуст. Проверьте синхронизацию кафедр и интернет-соединение."
            )

    def _load_db(self):
        self.profiles = []
        self.name_index.clear()
        self.hashtag_index.clear()

        for raw in self.db.get_all_employee_details():
            full_name = raw.get('full_name')
            if not full_name:
                continue
            clean_name = normalize_and_reorder(full_name)
            clean_name = clean_name.strip()
            if not clean_name:
                continue

            profile = self._prepare_name_profile(clean_name)
            if profile:
                self.profiles.append(profile)
                key = clean_name.lower().replace('ё', 'е')
                self.name_index[key] = full_name
                self.employee_by_normalized_name[key] = raw

                surname_firstname = ' '.join(clean_name.split()[:2]).lower().replace('ё', 'е')
                if surname_firstname:
                    self.name_index[surname_firstname] = full_name
                    if surname_firstname not in self.employee_by_normalized_name:
                        self.employee_by_normalized_name[surname_firstname] = raw

            hashtag = raw.get('hashtag')
            if hashtag:
                normalized_hashtag = normalize_hashtag(hashtag).lower()
                self.hashtag_index[normalized_hashtag] = raw

    def _prepare_name_profile(self, full_name: str) -> dict:
        parts = [p for p in full_name.split() if p]
        if len(parts) < 2:
            return {}
        surname, firstname = parts[0], parts[1]
        patronymic = parts[2] if len(parts) > 2 else ''

        def get_forms(word: str) -> set:
            forms = {word.lower(), word.lower().replace('ё', 'е')}
            try:
                parsed = self.morph.parse(word)
                if parsed:
                    for lex in self.morph.get_lexeme(parsed[0]):
                        forms.add(str(lex).lower())
                        forms.add(str(lex).lower().replace('ё', 'е'))
            except Exception:
                pass
            return forms

        return {
            'full_name': full_name,
            'surname': surname,
            'firstname': firstname,
            'patronymic': patronymic,
            'surname_forms': get_forms(surname),
            'firstname_forms': get_forms(firstname),
            'patronymic_forms': get_forms(patronymic) if patronymic else set(),
            'initials': {firstname[:1].lower(), f"{firstname[:1].lower()}.{patronymic[:1].lower()}" if patronymic else firstname[:1].lower()}
        }

    def _check_name_context(self, text: str, profile: dict) -> bool:
        text_lower = text.lower().replace('ё', 'е')
        for surname_form in profile['surname_forms']:
            if re.search(rf'\b{re.escape(surname_form)}\b', text_lower):
                if any(re.search(rf'\b{re.escape(name_form)}\b', text_lower) for name_form in profile['firstname_forms']):
                    return True
                if profile['patronymic_forms'] and any(re.search(rf'\b{re.escape(p_form)}\b', text_lower) for p_form in profile['patronymic_forms']):
                    return True
                if any(init in text_lower for init in profile['initials']):
                    return True
        return False

    def extract_teacher_hashtags(self, text: str) -> list:
        if not text:
            return []
        raw_tags = re.findall(r'#([A-Za-zА-Яа-яЁё0-9_]+)', text)
        return [normalize_hashtag(tag) for tag in sorted(set(raw_tags))]

    def find_employee_by_hashtag(self, hashtag: str):
        if not hashtag:
            return None
        return self.hashtag_index.get(normalize_hashtag(hashtag).lower())

    def find_employee_by_name(self, full_name: str):
        if not full_name:
            return None
        normalized = normalize_and_reorder(full_name).lower().replace('ё', 'е').strip()
        return self.employee_by_normalized_name.get(normalized)

    def find_employees_in_text(self, text: str) -> set:
        if not text:
            return set()
        found = set()
        teacher_tags = self.extract_teacher_hashtags(text)
        for tag in teacher_tags:
            employee = self.find_employee_by_hashtag(tag)
            if employee:
                found.add(employee['full_name'])

        if found:
            return found

        if self.natasha_ready:
            try:
                doc = Doc(text)
                doc.segment(self.segmenter)
                doc.tag_morph(self.morph_tagger)
                doc.tag_ner(self.ner_tagger)
                for span in doc.spans:
                    if span.type == 'PER':
                        name = span.text.lower().replace('ё', 'е')
                        if name in self.name_index:
                            found.add(self.name_index[name])
            except Exception:
                pass

        for profile in self.profiles:
            if self._check_name_context(text, profile):
                found.add(profile['full_name'])

        return found

    def get_teacher_hashtags(self, text: str) -> list:
        return self.extract_teacher_hashtags(text)

    def get_all_tags(self, text: str, include_keywords: bool = True, include_teacher_tags: bool = False) -> list:
        tags = set()
        if include_teacher_tags:
            tags.update(self.get_teacher_hashtags(text))

        if include_keywords and text:
            clean = re.sub(r'[^А-Яа-яЁё0-9_\s]', ' ', text.lower())
            words = [w for w in clean.split() if len(w) >= 4]
            stop_words = {
                'и','в','на','с','по','не','что','он','я','так','его','но','да','ты','к','у','же','вы','за','бы','только','ее','мне',
                'было','от','меня','еще','нет','из','ему','когда','даже','ну','ли','если','уже','или','ни','быть','был','до','вас',
                'уж','вам','ведь','там','потом','себя','ничего','ей','может','они','тут','где','есть','надо','ней','для','мы','тебя',
                'их','чем','была','сам','чтоб','без','будто','человек','чего','раз','тоже','себе','под','жизнь','будет','тогда','кто',
                'этот','того','потому','этого','какой','совсем','ним','здесь','этом','один','почти','мой','тем','чтобы','нее','сейчас',
                'были','куда','зачем','всех','никогда','можно','при','наконец','два','об','другой','хоть','после','над','больше','тот',
                'через','эти','нас','про','всего','них','какая','много','разве','три','эту','моя','впрочем','хорошо','свою','этой','перед',
                'иногда','лучше','чуть','том','нельзя','такой','им','более','всегда','конечно','всю','между','это','зато'
            }
            for word in words:
                if word not in stop_words and not word.isdigit():
                    tags.add(f"#{word}")

        return sorted(tags)
