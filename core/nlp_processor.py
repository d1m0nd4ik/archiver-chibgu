from natasha import (
    Segmenter,
    MorphVocab,
    NewsEmbedding,
    NewsMorphTagger,
    Doc
)
from collections import Counter
from config.settings import MAX_TAGS
from core.logging_config import logger

class NLPProcessor:
    def __init__(self):
        # Инициализируем пайплайн Natasha (загружается один раз)
        self.segmenter = Segmenter()
        self.morph_vocab = MorphVocab()
        self.emb = NewsEmbedding()
        self.tagger = NewsMorphTagger(self.emb)
        
        # Кэшируем результаты для скорости
        self._cache = {}

    def _process_text(self, text):
        """Внутренний метод для разбора текста"""
        if text in self._cache:
            return self._cache[text]
            
        doc = Doc(text)
        doc.segment(self.segmenter)
        doc.tag_morph(self.tagger)
        
        self._cache[text] = doc
        return doc

    def generate_tags(self, text, top_n=MAX_TAGS):
        """Генерация хештегов с использованием Natasha"""
        if not text:
            return ""
        
        # Ограничиваем длину текста для анализа, чтобы не грузить память
        if len(text) > 5000:
            text = text[:5000] + "..."

        doc = self._process_text(text)
        
        keywords = []
        for token in doc.tokens:
            # Берем только существительные (NOUN) и прилагательные (ADJ)
            # Это автоматически убирает глаголы, предлоги, местоимения
            pos = token.pos
            if pos in ('NOUN', 'ADJ'):
                # Лемматизация (приведение к начальной форме)
                token.lemmatize(self.morph_vocab)
                lemma = token.lemma
                
                # Фильтры длины и цифр
                if len(lemma) > 3 and not lemma.isdigit():
                    keywords.append(lemma.lower())
        
        if not keywords:
            return ""

        counter = Counter(keywords)
        top_words = [word for word, count in counter.most_common(top_n)]
        return " ".join([f"#{w}" for w in top_words])

    def extract_keywords(self, text, top_n=10):
        """Извлечение ключевых слов (без #)"""
        if not text:
            return []
        
        if len(text) > 5000:
            text = text[:5000] + "..."

        doc = self._process_text(text)
        keywords = []
        
        for token in doc.tokens:
            if token.pos in ('NOUN', 'ADJ'):
                token.lemmatize(self.morph_vocab)
                lemma = token.lemma
                if len(lemma) > 3 and not lemma.isdigit():
                    keywords.append(lemma.lower())
                    
        counter = Counter(keywords)
        return [word for word, count in counter.most_common(top_n)]