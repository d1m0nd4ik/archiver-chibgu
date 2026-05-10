import pymorphy3
from collections import Counter
from config.settings import MAX_TAGS, MIN_WORD_LENGTH
from core.logging_config import logger

STOP_WORDS = {
    'и', 'в', 'во', 'не', 'что', 'он', 'на', 'я', 'с', 'со', 'как', 'а', 'то',
    'все', 'она', 'так', 'его', 'но', 'да', 'ты', 'к', 'у', 'же', 'вы', 'за',
    'бы', 'по', 'только', 'ее', 'мне', 'было', 'вот', 'от', 'меня', 'еще',
    'нет', 'о', 'из', 'ему', 'теперь', 'когда', 'даже', 'ну', 'вдруг', 'ли',
    'если', 'уже', 'или', 'ни', 'быть', 'был', 'него', 'до', 'вас', 'нибудь',
    'опять', 'уж', 'вам', 'вед', 'сказал', 'ведь', 'там', 'потом', 'себя',
    'ничего', 'ей', 'может', 'они', 'тут', 'где', 'есть', 'надо', 'ней',
    'для', 'мы', 'тебя', 'их', 'чем', 'была', 'сам', 'чтоб', 'без', 'будто',
    'человек', 'чего', 'раз', 'тоже', 'себе', 'под', 'жизнь', 'будет', 'ж',
    'тогда', 'кто', 'этот', 'того', 'потому', 'этого', 'какой', 'совсем',
    'ним', 'здесь', 'этом', 'один', 'почти', 'мой', 'тем', 'чтобы', 'нее',
    'сейчас', 'были', 'куда', 'зачем', 'всех', 'никогда', 'можно', 'при',
    'наконец', 'два', 'об', 'другой', 'хоть', 'после', 'над', 'больше',
    'тот', 'через', 'эти', 'нас', 'про', 'всего', 'них', 'какая', 'много',
    'разве', 'три', 'эту', 'моя', 'впрочем', 'хорошо', 'свою', 'этой',
    'перед', 'иногда', 'лучше', 'чуть', 'том', 'нельзя', 'такой', 'им',
    'более', 'всегда', 'конечно', 'всю', 'между', 'это', 'зато'
}

class NLPProcessor:
    """Класс для обработки текста и генерации тегов"""
    
    def __init__(self):
        # Морфологический анализатор инициализируется один раз на инстанс
        self.morph = pymorphy3.MorphAnalyzer()

    def generate_tags(self, text, top_n=MAX_TAGS):
        """Генерация хештегов из текста"""
        if not text:
            return ""
        
        text = text.lower()
        words = text.split()
        clean_words = []
        
        for word in words:
            # Оставляем только буквы, цифры и 'ё'
            word = ''.join(c for c in word if c.isalnum() or c == 'ё')
            
            if len(word) < MIN_WORD_LENGTH or word in STOP_WORDS:
                continue
            if word.isdigit():
                continue
                
            try:
                normal_form = self.morph.parse(word)[0].normal_form
                if normal_form not in STOP_WORDS and len(normal_form) >= MIN_WORD_LENGTH:
                    clean_words.append(normal_form)
            except Exception as e:
                logger.debug("NLP parse error for word '%s': %s", word, e)
                continue
        
        counter = Counter(clean_words)
        top_words = [word for word, count in counter.most_common(top_n)]
        return " ".join([f"#{w}" for w in top_words])

    def extract_keywords(self, text, top_n=10):
        """Извлечение ключевых слов без хештегов"""
        if not text:
            return []
        
        text = text.lower()
        words = text.split()
        clean_words = []
        
        for word in words:
            word = ''.join(c for c in word if c.isalnum() or c == 'ё')
            if len(word) < MIN_WORD_LENGTH or word in STOP_WORDS or word.isdigit():
                continue
            try:
                normal_form = self.morph.parse(word)[0].normal_form
                if normal_form not in STOP_WORDS:
                    clean_words.append(normal_form)
            except Exception:
                continue
        
        counter = Counter(clean_words)
        return [word for word, count in counter.most_common(top_n)]