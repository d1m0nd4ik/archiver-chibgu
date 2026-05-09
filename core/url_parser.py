import re
import vk_api
from config.settings import VK_API_VERSION


class VKUrlParser:
    """Утилита для извлечения ID группы из ссылок ВКонтакте"""
    
    @staticmethod
    def extract_id_from_url(url, vk_api_instance=None):
        """Извлекает цифровой ID группы из ссылки"""
        if not url:
            return None
        
        url = url.strip()
        url = url.split('?')[0]
        url = url.split('#')[0]
        
        match = re.search(r'vk\.com/(?:wall/)?(.+)', url)
        if not match:
            return None
        
        path = match.group(1)
        
        # Формат: public123456, club123456, event123456
        numeric_match = re.match(r'(public|club|event)(\d+)', path, re.IGNORECASE)
        if numeric_match:
            return -int(numeric_match.group(2))
        
        # Формат: просто цифры
        if path.isdigit():
            return -int(path)
        
        # Формат: wall-123456_123
        wall_match = re.search(r'wall-?(\d+)_', url)
        if wall_match:
            return -int(wall_match.group(1))
        
        # Буквенная ссылка (требуется API)
        if vk_api_instance and '/' not in path:
            try:
                api = vk_api_instance.get_api()
                response = api.groups.get(group_id=path, v=VK_API_VERSION)
                if response.get('items'):
                    group_id = response['items'][0]['id']
                    return -group_id
            except vk_api.exceptions.ApiError as e:
                if "invalid access_token" in str(e):
                    raise Exception("Неверный токен! Получите новый на https://vkhost.github.io/")
                print(f"Error resolving group alias: {e}")
                return None
            except Exception as e:
                print(f"Error resolving group alias: {e}")
                return None
        
        return None

    @staticmethod
    def is_valid_vk_url(url):
        """Проверка, является ли строка ссылкой на VK"""
        if not url:
            return False
        return bool(re.search(r'vk\.com/', url, re.IGNORECASE))