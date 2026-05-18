import re
import requests
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

def normalize_name(name: str) -> str:
    return name.replace('ё', 'е').replace('Ё', 'Е').strip()

def extract_employees_from_html(html_content: str) -> list:
    soup = BeautifulSoup(html_content, 'html.parser')
    employees = []
    for tag in soup.find_all('td', itemprop='fio'):
        name = tag.get_text(strip=True)
        if name and len(name) > 3: employees.append(normalize_name(name))
    for table in soup.find_all('table'):
        headers = [h.get_text().lower() for h in table.find_all('th')]
        if any('ф.и.о.' in h for h in headers):
            for row in table.find_all('tr')[1:]:
                cells = row.find_all('td')
                if len(cells) >= 2:
                    name = re.sub(r'<[^>]+>', '', cells[1].get_text(strip=True))
                    name = normalize_name(name)
                    if name and len(name) > 3: employees.append(name)
    return employees

def remove_duplicates(employees: list) -> list:
    seen = set()
    return [e for e in employees if not (e in seen or seen.add(e))]

def fetch_employees_from_url(url: str = 'https://bgu-chita.ru/sveden/employees') -> list:
    try:
        resp = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=30)
        resp.encoding = 'utf-8'
        return remove_duplicates(extract_employees_from_html(resp.text))
    except Exception as e:
        logger.error(f"Fetch employees error: {e}")
        return []

def sync_employees_to_db(db: Database = None, url: str = 'https://bgu-chita.ru/sveden/employees') -> list:
    try:
        db = db or Database()
        employees = fetch_employees_from_url(url)
        if employees:
            if not db.update_employees(employees, source_url=url):
                logger.warning("Не удалось сохранить список сотрудников в БД")
        return employees
    except Exception as e:
        logger.error(f"Sync error: {e}")
        return []

def ensure_employees_loaded(db: Database = None, force_sync: bool = False) -> bool:
    """Загружает сотрудников из БД; при пустой таблице — с сайта вуза."""
    db = db or Database()
    if not force_sync and db.get_all_employees():
        return True
    employees = sync_employees_to_db(db)
    return bool(employees) or bool(db.get_all_employees())

class EmployeeTagger:
    def __init__(self, db: Database = None, refresh_on_init: bool = True):
        self.db = db or Database()
        self.morph = pymorphy3.MorphAnalyzer()
        self.natasha_ready = False
        if NATASHA_AVAILABLE:
            try:
                emb = NewsEmbedding()
                self.segmenter = Segmenter()
                self.morph_tagger = NewsMorphTagger(emb)
                self.ner_tagger = NewsNERTagger(emb)
                self.natasha_ready = True
            except Exception as e:
                logger.warning("Natasha NER недоступна, используется поиск по ФИО: %s", e)

        self.profiles = []
        self.name_index = {}
        self._load_db()
        if refresh_on_init or not self.profiles:
            try:
                ensure_employees_loaded(self.db, force_sync=refresh_on_init)
            except Exception as e:
                logger.error("Ошибка загрузки сотрудников: %s", e)
            self._load_db()
        if not self.profiles:
            logger.warning(
                "Список преподавателей пуст — теги ФИО в постах не будут добавляться. "
                "Проверьте интернет и страницу https://bgu-chita.ru/sveden/employees"
            )

    def _load_db(self):
        self.profiles = []
        self.name_index.clear()
        for raw in self.db.get_all_employees():
            if not raw or len(raw.strip()) < 3: continue
            clean = normalize_and_reorder(raw)
            self.profiles.append(self._prep(clean))
            key = clean.lower().replace('ё', 'е')
            self.name_index[key] = clean
            parts = key.split()
            if len(parts) >= 3:
                self.name_index[parts[0]] = clean
                self.name_index[f"{parts[0]} {parts[1]}"] = clean

    def _prep(self, name: str) -> dict:
        parts = name.strip().split()
        if len(parts) < 2: return {}
        s, n = parts[0], parts[1]
        p = parts[2] if len(parts) > 2 else ""
        
        # Исправленный вызов pymorphy3
        def get_forms(w):
            forms = {w.lower(), w.lower().replace('ё','е')}
            try:
                parsed = self.morph.parse(w)
                if parsed:
                    for lex in self.morph.get_lexeme(parsed[0]):
                        forms.add(lex.lower())
                        forms.add(lex.lower().replace('ё','е'))
            except: pass
            return forms

        s_forms = get_forms(s)
        n_forms = get_forms(n)
        p_forms = get_forms(p) if p else set()
        
        fi, pi = (n[0].lower(), p[0].lower()) if p else (n[0].lower(), '')
        return {'full': name, 'surname': s, 'name': n, 'patronymic': p,
                's_forms': s_forms, 'n_forms': n_forms, 'p_forms': p_forms,
                'initials': [f"{fi}.", f"{fi}.{pi}.", fi, f"{fi}.{pi}"]}

    def _check_context(self, text: str, emp: dict) -> bool:
        t = text.lower().replace('ё', 'е')
        for sf in emp['s_forms']:
            for m in re.finditer(rf'\b{re.escape(sf)}\b', t):
                ctx = text[max(0, m.start()-50):min(len(text), m.end()+50)]
                ctx_c = ctx.lower().replace('ё', 'е').replace(sf, ' ')
                if any(x in ctx_c for x in emp['n_forms']) or any(x in ctx_c for x in emp['initials']): return True
                if emp['p_forms'] and any(x in ctx_c for x in emp['p_forms']): return True
                others = re.findall(r'\b([А-ЯЁ][а-яё]+)\b', ctx)
                for o in others:
                    o_n = o.lower().replace('ё', 'е')
                    if len(o_n) > 2 and o_n not in emp['n_forms'] and o_n not in emp['p_forms'] and o_n not in emp['s_forms']:
                        return False
                return True
        return False

    def find_employees_in_text(self, text: str) -> set:
        if not text: return set()
        found = set()
        if self.natasha_ready:
            try:
                doc = Doc(text)
                doc.segment(self.segmenter)
                doc.tag_morph(self.morph_tagger)
                doc.tag_ner(self.ner_tagger)
                for sp in doc.spans:
                    if sp.type == 'PER':
                        e = sp.text.lower().replace('ё', 'е')
                        if e in self.name_index: found.add(self.name_index[e])
            except Exception: pass
        if not found:
            for emp in self.profiles:
                if self._check_context(text, emp): found.add(emp['full'])
        return found

    def get_hashtags(self, text: str) -> list:
        return sorted([f"#{n.lower().replace('ё','е').replace(' ','_')}" for n in self.find_employees_in_text(text)])

    def get_all_tags(self, text: str, include_keywords: bool = True) -> list:
        if not text: return []
        tags = set(self.get_hashtags(text))
        if include_keywords:
            words = re.sub(r'[^\w\sа-яё]', ' ', text.lower()).split()
            stop = {'и','в','на','с','по','не','что','он','я','так','его','но','да','ты','к','у','же','вы','за','бы','только','ее','мне','было','от','меня','еще','нет','из','ему','когда','даже','ну','ли','если','уже','или','ни','быть','был','до','вас','уж','вам','ведь','там','потом','себя','ничего','ей','может','они','тут','где','есть','надо','ней','для','мы','тебя','их','чем','была','сам','чтоб','без','будто','человек','чего','раз','тоже','себе','под','жизнь','будет','тогда','кто','этот','того','потому','этого','какой','совсем','ним','здесь','этом','один','почти','мой','тем','чтобы','нее','сейчас','были','куда','зачем','всех','никогда','можно','при','наконец','два','об','другой','хоть','после','над','больше','тот','через','эти','нас','про','всего','них','какая','много','разве','три','эту','моя','впрочем','хорошо','свою','этой','перед','иногда','лучше','чуть','том','нельзя','такой','им','более','всегда','конечно','всю','между','это','зато'}
            tags.update(f"#{w}" for w in words if len(w)>=4 and w not in stop and not w.isdigit())
        return sorted(list(tags))