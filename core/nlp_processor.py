"""
Модуль для обработки текста и генерации тегов.
Использует Natasha для точного NLP-анализа и лемматизации к именительному падежу.
"""
import re
from collections import Counter
from config.settings import MAX_TAGS, MIN_WORD_LENGTH
from core.logging_config import logger

# Попытка импорта Natasha
try:
    from natasha import Segmenter, NewsEmbedding, NewsMorphTagger, Doc
    NATASHA_AVAILABLE = True
except ImportError:
    NATASHA_AVAILABLE = False
    logger.warning("Natasha не найдена. Будет использован fallback на pymorphy3.")

# Минимальный список стоп-слов (основную фильтрацию делает POS-тегирование Natasha)
STOP_WORDS = {
    'год', 'года', 'лет', 'месяц', 'дня', 'час', 'раз', 'место', 'дело', 'время',
    'человек', 'люди', 'день', 'ночь', 'утро', 'вечер', 'жизнь', 'работа', 'путь',
    'вид', 'сторона', 'случай', 'вопрос', 'голова', 'рука', 'часть', 'раз'
}

class NLPProcessor:
    """Класс для обработки текста и генерации нормализованных хештегов"""
    def __init__(self):
        self.natasha_ready = False
        self.morph = None

        # Инициализация Natasha
        if NATASHA_AVAILABLE:
            try:
                emb = NewsEmbedding()
                self.segmenter = Segmenter()
                self.morph_tagger = NewsMorphTagger(emb)
                self.natasha_ready = True
            except Exception as e:
                logger.error(f"Ошибка инициализации Natasha: {e}")

        # Fallback на pymorphy3 если Natasha недоступна
        if not self.natasha_ready:
            try:
                import pymorphy3
                self.morph = pymorphy3.MorphAnalyzer()
            except ImportError:
                logger.error("Ни Natasha, ни pymorphy3 не найдены. Теги будут генерироваться без лемматизации.")

    def _extract_lemmas_natasha(self, text: str) -> list:
        """Извлекает леммы (именительный падеж) через Natasha"""
        doc = Doc(text)
        doc.segment(self.segmenter)
        doc.tag_morph(self.morph_tagger)
        
        keywords = []
        for token in doc.tokens:
            # Берем только существительные и прилагательные
            if token.pos in ('NOUN', 'ADJ'):
                lemma = (token.lemma or token.text).lower().replace('ё', 'е')
                if len(lemma) >= MIN_WORD_LENGTH and not lemma.isdigit() and lemma not in STOP_WORDS:
                    keywords.append(lemma)
        return keywords

    def _extract_lemmas_pymorphy(self, text: str) -> list:
        """Fallback: извлечение лемм через pymorphy3"""
        text = text.lower().replace('ё', 'е')
        words = re.sub(r'[^\w\sа-яё]', ' ', text).split()
        keywords = []
        
        for word in words:
            if len(word) < MIN_WORD_LENGTH or word.isdigit() or word in STOP_WORDS:
                continue
            try:
                parsed = self.morph.parse(word)
                if parsed:
                    normal = parsed[0].normal_form.lower()
                    if normal not in STOP_WORDS:
                        keywords.append(normal)
            except Exception:
                continue
        return keywords

    def generate_tags(self, text: str, top_n: int = MAX_TAGS) -> str:
        """
        Генерация хештегов из текста.
        Все слова приводятся к именительному падежу (лемме).
        """
        if not text or len(text.strip()) < MIN_WORD_LENGTH:
            return ""

        try:
            # Выбор движка лемматизации
            if self.natasha_ready:
                keywords = self._extract_lemmas_natasha(text)
            elif self.morph:
                keywords = self._extract_lemmas_pymorphy(text)
            else:
                # Минимальный fallback без морфологии
                keywords = [
                    w.lower().replace('ё', 'е') 
                    for w in re.sub(r'[^\w\sа-яё]', ' ', text).split()
                    if len(w) >= MIN_WORD_LENGTH and not w.isdigit() and w.lower() not in STOP_WORDS
                ]

            if not keywords:
                return ""

            # Топ частотных слов
            counter = Counter(keywords)
            top_words = [word for word, _ in counter.most_common(top_n)]
            return " ".join(f"#{w}" for w in top_words)

        except Exception as e:
            logger.error(f"Ошибка генерации тегов: {e}", exc_info=True)
            return ""

    def extract_keywords(self, text: str, top_n: int = 10) -> list:
        """Извлечение ключевых слов без решёток (для внутреннего поиска)"""
        tags = self.generate_tags(text, top_n)
        return [t.lstrip('#') for t in tags.split()] if tags else []