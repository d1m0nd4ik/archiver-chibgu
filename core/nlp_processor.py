"""
Утилиты для хэштегов и шаблон словаря тегов (DEFAULT_TAG_DICTIONARY).
Подбор тегов по тексту — в core.smart_tagger.SmartTagger.
"""
import re
from collections import defaultdict

from config.settings import MAX_TAGS, MIN_WORD_LENGTH
from core.database import Database
from core.logging_config import logger

try:
    import pymorphy3
    PYMORPHY_AVAILABLE = True
except ImportError:
    PYMORPHY_AVAILABLE = False

try:
    from natasha import Segmenter, NewsEmbedding, NewsMorphTagger, Doc
    NATASHA_AVAILABLE = True
except ImportError:
    NATASHA_AVAILABLE = False
    logger.warning("Natasha не найдена. Будет использован fallback на pymorphy3.")

STOP_WORDS = {
    'год', 'года', 'лет', 'месяц', 'день', 'дня', 'час', 'время', 'человек', 'люди',
    'дело', 'жизнь', 'вопрос', 'часть', 'раз', 'это', 'этот', 'тот', 'такой', 'также',
    'быть', 'был', 'была', 'были', 'есть', 'нет', 'который', 'которая', 'которые',
    'где', 'когда', 'почему', 'потому', 'сегодня', 'вчера', 'завтра', 'наш', 'наша',
    'наше', 'наши', 'нашей', 'нашем', 'наших', 'свой', 'своя', 'свои', 'свое', 'своей',
    'весь', 'вся', 'все', 'всего', 'всем', 'всех', 'этом', 'этой', 'этих', 'том', 'той',
    'тех', 'тут', 'там', 'здесь', 'уже', 'еще', 'ещё', 'или', 'либо', 'при', 'для',
    'под', 'над', 'между', 'после', 'перед', 'через', 'без', 'про', 'об', 'от', 'до',
    'из', 'на', 'по', 'со', 'во', 'не', 'ни', 'да', 'но', 'же', 'ли', 'бы', 'как',
    'что', 'чтобы', 'если', 'когда', 'очень', 'более', 'менее', 'сам', 'сама', 'само',
    'сами', 'является', 'являются', 'включает', 'включают', 'которых', 'которому',
}

VALID_POS = {'NOUN', 'ADJ', 'PROPN'}
VALID_TOKEN_RE = re.compile(r"^[а-яёa-z0-9-]+$", re.IGNORECASE)

# Фразы с фиксированным правильным написанием
KNOWN_PHRASES = {
    'великий отечественный война': 'великая_отечественная_война',
    'великая отечественная война': 'великая_отечественная_война',
    'великой отечественной войны': 'великая_отечественная_война',
    'день победы': 'день_победы',
    'день победы великой отечественной войны': 'день_победы',
    'новый год': 'новый_год',
    'день знаний': 'день_знаний',
    'день учителя': 'день_учителя',
    'день защитника отечества': 'день_защитника_отечества',
    'последний звонок': 'последний_звонок',
    'посвящение в студенты': 'посвящение_в_студенты',
    'выдача дипломов': 'выдача_дипломов',
    'клуб по интересам': 'клуб_по_интересам',
    'встреча со студентами': 'встреча_со_студентами',
    'группа студентов': 'группа_студентов',
    'год поступления': 'год_поступления',
    'год выпуска': 'год_выпуска',
    'юный следователь': 'юный_следователь',
    'день окружающей среды': 'день_окружающей_среды',
    'год единства народов': 'год_единства_народов',
    'гуманитарная помощь': 'гуманитарная_помощь',
    'читинский институт': 'читинский_институт',
    'пресс центр': 'пресс_центр',
    'книжная выставка': 'книжная_выставка',
    'научная конференция': 'научная_конференция',
    'ледовое побоище': 'ледовое_побоище',
    'блокада ленинграда': 'блокада_ленинграда',
}

# Неверные формы — только для поиска в тексте (KNOWN_PHRASES), не для словаря
DISALLOWED_DICTIONARY_PHRASES = frozenset({
    'великий отечественный война',
})

# При дубле хэштега в словаре оставляем каноническую фразу
CANONICAL_PHRASE_BY_HASHTAG = {
    '#великая_отечественная_война': 'великая отечественная война',
}

# Дополнение словаря по тематике группы vk.ru/bguchita (ЧИ БГУ)
BGUCHITA_TAG_DICTIONARY = [
    {'category': 'group', 'phrase': 'читинский институт', 'hashtag': '#читинский_институт', 'weight': 245},
    {'category': 'group', 'phrase': 'чибгу', 'hashtag': '#чибгу', 'weight': 240},
    {'category': 'group', 'phrase': 'колледж', 'hashtag': '#колледж', 'weight': 225},
    {'category': 'group', 'phrase': 'студсовет', 'hashtag': '#студсовет', 'weight': 220},
    {'category': 'group', 'phrase': 'пресс центр', 'hashtag': '#пресс_центр', 'weight': 210},
    {'category': 'group', 'phrase': 'библиотека', 'hashtag': '#библиотека', 'weight': 215},
    {'category': 'group', 'phrase': 'забайкалье', 'hashtag': '#забайкалье', 'weight': 210},
    {'category': 'group', 'phrase': 'юридический факультет', 'hashtag': '#юридический_факультет', 'weight': 215},
    {'category': 'personal', 'phrase': 'кадет', 'hashtag': '#кадет', 'weight': 200},
    {'category': 'event', 'phrase': 'юный следователь', 'hashtag': '#юный_следователь', 'weight': 255},
    {'category': 'event', 'phrase': 'сессия', 'hashtag': '#сессия', 'weight': 220},
    {'category': 'event', 'phrase': 'спартакиада', 'hashtag': '#спартакиада', 'weight': 230},
    {'category': 'event', 'phrase': 'стажировка', 'hashtag': '#стажировка', 'weight': 220},
    {'category': 'event', 'phrase': 'гуманитарная помощь', 'hashtag': '#гуманитарная_помощь', 'weight': 245},
    {'category': 'event', 'phrase': 'день окружающей среды', 'hashtag': '#день_окружающей_среды', 'weight': 235},
    {'category': 'event', 'phrase': 'день защиты детей', 'hashtag': '#день_защиты_детей', 'weight': 228},
    {'category': 'event', 'phrase': 'научная конференция', 'hashtag': '#научная_конференция', 'weight': 238},
    {'category': 'event', 'phrase': 'публикация ринц', 'hashtag': '#публикация_ринц', 'weight': 225},
    {'category': 'event', 'phrase': 'китайский язык', 'hashtag': '#китайский_язык', 'weight': 215},
    {'category': 'event', 'phrase': 'книжная выставка', 'hashtag': '#книжная_выставка', 'weight': 218},
    {'category': 'event', 'phrase': 'театр книги', 'hashtag': '#театр_книги', 'weight': 212},
    {'category': 'event', 'phrase': 'подкаст', 'hashtag': '#подкаст', 'weight': 205},
    {'category': 'event', 'phrase': 'воинская слава', 'hashtag': '#воинская_слава', 'weight': 222},
    {'category': 'event', 'phrase': 'блокада ленинграда', 'hashtag': '#блокада_ленинграда', 'weight': 228},
    {'category': 'event', 'phrase': 'ледовое побоище', 'hashtag': '#ледовое_побоище', 'weight': 222},
    {'category': 'event', 'phrase': 'год единства народов', 'hashtag': '#год_единства_народов', 'weight': 232},
    {'category': 'event', 'phrase': 'заповедник', 'hashtag': '#заповедник', 'weight': 215},
    {'category': 'event', 'phrase': 'повышение квалификации', 'hashtag': '#повышение_квалификации', 'weight': 205},
    {'category': 'event', 'phrase': 'национальная безопасность', 'hashtag': '#национальная_безопасность', 'weight': 215},
    {'category': 'event', 'phrase': 'криминалистика', 'hashtag': '#криминалистика', 'weight': 210},
    {'category': 'event', 'phrase': 'правовая викторина', 'hashtag': '#правовая_викторина', 'weight': 208},
]

DEFAULT_TAG_DICTIONARY = [
    {'category': 'personal', 'phrase': 'преподаватель', 'hashtag': '#преподаватель', 'weight': 220},
    {'category': 'personal', 'phrase': 'сотрудник', 'hashtag': '#сотрудник', 'weight': 200},
    {'category': 'personal', 'phrase': 'студент', 'hashtag': '#студент', 'weight': 200},
    {'category': 'personal', 'phrase': 'гость', 'hashtag': '#гость', 'weight': 180},
    {'category': 'group', 'phrase': 'группа студентов', 'hashtag': '#группа_студентов', 'weight': 190},
    {'category': 'group', 'phrase': 'кафедра', 'hashtag': '#кафедра', 'weight': 210},
    {'category': 'group', 'phrase': 'подразделение', 'hashtag': '#подразделение', 'weight': 180},
    {'category': 'group', 'phrase': 'факультет', 'hashtag': '#факультет', 'weight': 210},
    {'category': 'group', 'phrase': 'год поступления', 'hashtag': '#год_поступления', 'weight': 160},
    {'category': 'group', 'phrase': 'год выпуска', 'hashtag': '#год_выпуска', 'weight': 160},
    {'category': 'event', 'phrase': 'посвящение в студенты', 'hashtag': '#посвящение_в_студенты', 'weight': 260},
    {'category': 'event', 'phrase': 'последний звонок', 'hashtag': '#последний_звонок', 'weight': 260},
    {'category': 'event', 'phrase': 'выдача дипломов', 'hashtag': '#выдача_дипломов', 'weight': 260},
    {'category': 'event', 'phrase': 'выпускной', 'hashtag': '#выпускной', 'weight': 250},
    {'category': 'event', 'phrase': 'спорт', 'hashtag': '#спорт', 'weight': 220},
    {'category': 'event', 'phrase': 'конференция', 'hashtag': '#конференция', 'weight': 220},
    {'category': 'event', 'phrase': 'благотворительность', 'hashtag': '#благотворительность', 'weight': 230},
    {'category': 'event', 'phrase': 'шефство', 'hashtag': '#шефство', 'weight': 210},
    {'category': 'event', 'phrase': 'волонтерство', 'hashtag': '#волонтерство', 'weight': 230},
    {'category': 'event', 'phrase': 'конкурс', 'hashtag': '#конкурс', 'weight': 220},
    {'category': 'event', 'phrase': 'встреча со студентами', 'hashtag': '#встреча_со_студентами', 'weight': 210},
    {'category': 'event', 'phrase': 'кружок', 'hashtag': '#кружок', 'weight': 200},
    {'category': 'event', 'phrase': 'клуб по интересам', 'hashtag': '#клуб_по_интересам', 'weight': 200},
    {'category': 'event', 'phrase': 'профориентация', 'hashtag': '#профориентация', 'weight': 220},
    {'category': 'event', 'phrase': 'выставка', 'hashtag': '#выставка', 'weight': 220},
    {'category': 'event', 'phrase': 'день знаний', 'hashtag': '#день_знаний', 'weight': 250},
    {'category': 'event', 'phrase': 'день учителя', 'hashtag': '#день_учителя', 'weight': 250},
    {'category': 'event', 'phrase': 'день победы', 'hashtag': '#день_победы', 'weight': 260},
    {'category': 'event', 'phrase': 'новый год', 'hashtag': '#новый_год', 'weight': 240},
    {'category': 'event', 'phrase': 'международный женский день', 'hashtag': '#8_марта', 'weight': 240},
    {'category': 'event', 'phrase': 'день защитника отечества', 'hashtag': '#23_февраля', 'weight': 240},
    {'category': 'event', 'phrase': 'великая отечественная война', 'hashtag': '#великая_отечественная_война', 'weight': 300},
    {'category': 'event', 'phrase': 'патриотизм', 'hashtag': '#патриотизм', 'weight': 200},
    {'category': 'event', 'phrase': 'нравственность', 'hashtag': '#нравственность', 'weight': 200},
] + BGUCHITA_TAG_DICTIONARY


def normalize_text(value: str) -> str:
    return (value or '').lower().replace('ё', 'е')


def normalize_hashtag(value: str) -> str:
    if not value:
        return ''
    raw = value.strip()
    if not raw.startswith('#'):
        raw = f"#{raw}"
    raw = normalize_text(raw)
    # Убираем префиксы категорий из старых записей
    for prefix in (
        'персональные_', 'групповые_', 'событийные_', 'праздники_',
        'personal_', 'group_', 'event_',
    ):
        if raw.startswith(f'#{prefix}'):
            raw = '#' + raw[len(prefix) + 1:]
    raw = raw.replace(' ', '_')
    raw = re.sub(r'[^#a-zа-я0-9_]', '', raw, flags=re.IGNORECASE)
    raw = re.sub(r'_+', '_', raw).strip('_')
    return raw


def dedupe_hashtags(tags: list[str]) -> list[str]:
    seen = set()
    result = []
    for tag in tags:
        norm = normalize_hashtag(tag)
        if not norm or norm == '#':
            continue
        key = norm.lower().replace('ё', 'е')
        if key in seen:
            continue
        seen.add(key)
        result.append(norm)
    return result


class NLPProcessor:
    def __init__(self):
        self.natasha_ready = False
        self.morph = pymorphy3.MorphAnalyzer() if PYMORPHY_AVAILABLE else None
        self._dictionary_cache = []
        self._dictionary_hashtag_keys = set()
        self._dictionary_cache_ready = False

        if NATASHA_AVAILABLE:
            try:
                emb = NewsEmbedding()
                self.segmenter = Segmenter()
                self.morph_tagger = NewsMorphTagger(emb)
                self.natasha_ready = True
            except Exception as e:
                logger.warning("Ошибка инициализации Natasha: %s", e)

    def _parse_word(self, word: str):
        if not self.morph:
            return None
        try:
            return self.morph.parse(word)[0]
        except Exception:
            return None

    def _grammemes_from_head(self, head) -> frozenset[str]:
        """Именительный падеж; без None (pymorphy3 иначе падает с Unknown grammeme)."""
        grams: set[str] = {'nomn'}
        tag = getattr(head, 'tag', None)
        if tag is None:
            grams.add('sing')
            return frozenset(grams)
        gender = getattr(tag, 'gender', None)
        number = getattr(tag, 'number', None)
        if gender:
            grams.add(gender)
        if number:
            grams.add(number)
        else:
            grams.add('sing')
        return frozenset(grams)

    def _safe_inflect(self, parsed, grammemes: frozenset[str] | set[str] | None = None):
        if not parsed or not hasattr(parsed, 'inflect'):
            return None
        try:
            if grammemes is None:
                grams = frozenset({'nomn', 'sing'})
            else:
                grams = frozenset(g for g in grammemes if g)
            if not grams:
                grams = frozenset({'nomn', 'sing'})
            return parsed.inflect(grams)
        except Exception:
            return None

    def _normal_form(self, word: str) -> str:
        word = normalize_text(word).strip('-_')
        if not word or word.isdigit():
            return ''
        parsed = self._parse_word(word)
        if parsed:
            return parsed.normal_form.replace('ё', 'е')
        return word

    def _is_valid_normal_form(self, lemma: str, pos: str | None) -> bool:
        """Только именительный падеж, единственное число (для существительных)."""
        if not lemma or lemma in STOP_WORDS:
            return False
        parsed = self._parse_word(lemma)
        if not parsed:
            return True
        if pos == 'ADJ':
            inf = self._safe_inflect(parsed, {'nomn', 'sing'})
            return bool(inf)
        if pos in ('NOUN', 'PROPN'):
            inf = self._safe_inflect(parsed, {'nomn', 'sing'})
            if not inf:
                return False
            return inf.normal_form.replace('ё', 'е') == parsed.normal_form.replace('ё', 'е')
        return False

    def _inflect_phrase_tokens(self, tokens: list[tuple[str, str]]) -> str:
        """Согласование фразы: прилагательные подстраиваются под существительное."""
        if not tokens:
            return ''
        words = [t[0] for t in tokens]
        try:
            phrase_key = ' '.join(words)
            if phrase_key in KNOWN_PHRASES:
                return KNOWN_PHRASES[phrase_key]

            noun_idx = next((i for i, t in enumerate(tokens) if t[1] in ('NOUN', 'PROPN')), None)
            if noun_idx is None:
                return '_'.join(self._normal_form(w) for w in words if w)

            head = self._parse_word(tokens[noun_idx][0])
            if not head:
                return '_'.join(self._normal_form(w) for w in words if w)

            head_grams = self._grammemes_from_head(head)
            parts = []
            for word, pos in tokens:
                if pos == 'ADJ' and head:
                    p = self._parse_word(word)
                    if p:
                        inf = self._safe_inflect(p, head_grams)
                        parts.append((inf.normal_form if inf else word).replace('ё', 'е'))
                        continue
                parts.append(self._normal_form(word))
            return '_'.join(p for p in parts if p)
        except Exception:
            return '_'.join(self._normal_form(w) for w in words if w)

    def _token_weight(self, pos: str | None, idx: int) -> float:
        if pos == 'NOUN':
            bonus = 2.2
        elif pos == 'PROPN':
            bonus = 2.0
        elif pos == 'ADJ':
            bonus = 1.4
        else:
            bonus = 1.0
        return bonus + max(0.0, 0.6 - idx * 0.01)

    def _extract_candidates_natasha(self, text: str, exclude_words: set[str]) -> dict[str, float]:
        scores = defaultdict(float)
        doc = Doc(text)
        doc.segment(self.segmenter)
        doc.tag_morph(self.morph_tagger)

        seq = []
        for idx, token in enumerate(doc.tokens):
            raw = normalize_text(token.text)
            lemma = normalize_text(token.lemma or token.text)
            pos = token.pos
            if not VALID_TOKEN_RE.match(raw):
                seq.append(None)
                continue
            if len(raw) < MIN_WORD_LENGTH or raw in STOP_WORDS or raw.isdigit():
                seq.append(None)
                continue
            if raw in exclude_words or lemma in exclude_words:
                seq.append(None)
                continue
            if pos not in VALID_POS:
                seq.append(None)
                continue
            norm = self._normal_form(lemma)
            if not self._is_valid_normal_form(norm, pos):
                seq.append(None)
                continue
            seq.append((lemma, pos, norm))
            scores[norm] += self._token_weight(pos, idx)

        # Фразы 2-4 слова
        for i in range(len(seq)):
            if not seq[i]:
                continue
            for size, boost in ((4, 5.0), (3, 4.2), (2, 2.8)):
                chunk = seq[i:i + size]
                if len(chunk) != size or any(not x for x in chunk):
                    continue
                token_slice = [(c[0], c[1]) for c in chunk]
                phrase = self._inflect_phrase_tokens(token_slice)
                if phrase and len(phrase) >= (MIN_WORD_LENGTH * 2 + 1):
                    scores[phrase] += boost
        return scores

    def _extract_candidates_fallback(self, text: str, exclude_words: set[str]) -> dict[str, float]:
        scores = defaultdict(float)
        clean = re.sub(r'[^a-zа-яё0-9\s]', ' ', normalize_text(text))
        words = [w for w in clean.split() if len(w) >= MIN_WORD_LENGTH]

        for idx, word in enumerate(words):
            if word in STOP_WORDS or word.isdigit() or word in exclude_words:
                continue
            norm = self._normal_form(word)
            if not norm or norm in STOP_WORDS:
                continue
            if not self._is_valid_normal_form(norm, 'NOUN'):
                continue
            scores[norm] += 1.4 + max(0.0, 0.4 - idx * 0.01)

        joined = ' '.join(words)
        for src, dst in KNOWN_PHRASES.items():
            if src in joined:
                scores[dst] += 4.0
        return scores

    def _load_dictionary(self):
        if self._dictionary_cache_ready:
            return self._dictionary_cache
        try:
            db = Database()
            db.normalize_tag_dictionary_hashtags()
            inserted = db.seed_default_tag_dictionary(DEFAULT_TAG_DICTIONARY)
            if inserted:
                logger.info("Tag dictionary seeded: %s новых записей", inserted)
            self._dictionary_cache = db.get_tag_dictionary(only_active=True)
            self._dictionary_hashtag_keys = {
                normalize_hashtag(row.get('hashtag', '')).lower().replace('ё', 'е')
                for row in self._dictionary_cache
                if row.get('hashtag')
            }
        except Exception as e:
            logger.warning("Не удалось загрузить словарь тегов: %s", e)
            self._dictionary_cache = []
            self._dictionary_hashtag_keys = set()
        self._dictionary_cache_ready = True
        return self._dictionary_cache

    def refresh_dictionary(self):
        self._dictionary_cache_ready = False
        self._dictionary_cache = []
        self._dictionary_hashtag_keys = set()

    def matches_dictionary_hashtag(self, tag: str) -> bool:
        self._load_dictionary()
        return normalize_hashtag(tag).lower().replace('ё', 'е') in self._dictionary_hashtag_keys

    def get_active_dictionary_hashtags(self, limit: int = 50) -> list[str]:
        """Активные хэштеги словаря для подсказки локальной модели."""
        rows = self._load_dictionary()
        tags = []
        for row in rows:
            tag = normalize_hashtag(row.get('hashtag', ''))
            if tag and tag not in tags:
                tags.append(tag)
            if len(tags) >= limit:
                break
        return tags

    def _dictionary_tags(self, text: str) -> dict[str, float]:
        norm_text = f" {normalize_text(text)} "
        scores = {}
        for row in self._load_dictionary():
            phrase = normalize_text(row.get('phrase', ''))
            if not phrase:
                continue
            if phrase in KNOWN_PHRASES:
                pattern_phrase = phrase
            else:
                pattern_phrase = phrase
            pattern = rf'(?<!\w){re.escape(pattern_phrase)}(?!\w)'
            if re.search(pattern, norm_text):
                tag = normalize_hashtag(row.get('hashtag'))
                if tag:
                    key = tag.lstrip('#')
                    scores[key] = max(scores.get(key, 0.0), float(row.get('weight') or 100))
        for src, dst in KNOWN_PHRASES.items():
            if src in norm_text:
                scores[dst] = max(scores.get(dst, 0.0), 280.0)
        return scores

    def generate_tags(
        self,
        text: str,
        top_n: int = MAX_TAGS,
        exclude_words: set | None = None,
        reserved_hashtags: set | None = None,
    ) -> str:
        if not text or len(text.strip()) < MIN_WORD_LENGTH:
            return ""
        exclude_words = exclude_words or set()
        reserved = {normalize_hashtag(h).lower().replace('ё', 'е') for h in (reserved_hashtags or set())}

        try:
            scores = self._dictionary_tags(text)
            candidates = (
                self._extract_candidates_natasha(text, exclude_words)
                if self.natasha_ready
                else self._extract_candidates_fallback(text, exclude_words)
            )
            for token, score in candidates.items():
                if token in STOP_WORDS or token.isdigit():
                    continue
                key = normalize_hashtag(token).lower().replace('ё', 'е')
                if key in reserved:
                    continue
                scores[token] = max(scores.get(token, 0.0), score)

            if not scores:
                return ""

            ranked = sorted(scores.items(), key=lambda kv: (-kv[1], kv[0]))
            tags = []
            for token, _ in ranked:
                hashtag = normalize_hashtag(token)
                key = hashtag.lower().replace('ё', 'е')
                if not hashtag or hashtag == '#' or key in reserved:
                    continue
                tags.append(hashtag)
                if len(tags) >= top_n:
                    break
            return ' '.join(dedupe_hashtags(tags))
        except Exception as e:
            logger.error("Ошибка генерации тегов: %s", e, exc_info=True)
            return ""

    def extract_keywords(self, text: str, top_n: int = 10) -> list:
        tags = self.generate_tags(text, top_n)
        return [t.lstrip('#') for t in tags.split()] if tags else []
