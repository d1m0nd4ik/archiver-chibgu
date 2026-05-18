import re
from typing import Optional
import vk_api
from config.settings import VK_API_VERSION
from core.logging_config import logger

_VK_HOST = r'(?:vk\.com|vk\.ru|m\.vk\.com)'
_VK_URL_RE = re.compile(
    rf'(?:https?://)?(?:www\.)?{_VK_HOST}/(?P<path>[^?\s#]+)',
    re.IGNORECASE,
)


class VKUrlParser:
    """Извлечение и разрешение ID сообщества ВКонтакте из ссылки, screen_name или числа."""

    @staticmethod
    def is_vk_link(text: str) -> bool:
        if not text:
            return False
        t = text.strip()
        return bool(
            _VK_URL_RE.search(t)
            or re.search(rf'\b{_VK_HOST}/', t, re.IGNORECASE)
        )

    @staticmethod
    def _numeric_group_id(value: str):
        """Числовой ID: 236813059 или -236813059 → owner_id для wall.get."""
        value = value.strip()
        if not re.fullmatch(r'-?\d+', value):
            return None
        gid = int(value)
        if gid == 0:
            return None
        return -abs(gid) if gid > 0 else gid

    @staticmethod
    def _id_from_path(path: str):
        """public123, club123, event123 или просто цифры в пути."""
        path = path.strip().strip('/')
        if not path:
            return None

        prefix_match = re.match(r'^(public|club|event)(\d+)$', path, re.IGNORECASE)
        if prefix_match:
            return -int(prefix_match.group(2))

        if path.isdigit():
            return -int(path)

        wall_match = re.search(r'wall(-?\d+)_', path, re.IGNORECASE)
        if wall_match:
            gid = int(wall_match.group(1))
            return -abs(gid) if gid > 0 else gid

        return None

    @staticmethod
    def extract_screen_name(identifier: str) -> Optional[str]:
        """Короткое имя из URL или строки (durov, apng_archiver)."""
        if not identifier:
            return None
        raw = identifier.strip()
        raw = raw.split('?')[0].split('#')[0]

        numeric = VKUrlParser._numeric_group_id(raw)
        if numeric is not None and raw.lstrip('-').isdigit():
            return None

        url_match = _VK_URL_RE.search(raw)
        if url_match:
            path = url_match.group('path').strip('/')
        elif re.fullmatch(r'[\w.\-]+', raw, re.UNICODE) and not raw.isdigit():
            path = raw
        else:
            legacy = re.search(r'vk\.com/(?:wall/)?([^?\s#]+)', raw, re.IGNORECASE)
            if not legacy:
                return None
            path = legacy.group(1).strip('/')

        if VKUrlParser._id_from_path(path) is not None:
            return None

        if '/' in path:
            path = path.split('/')[0]

        if re.fullmatch(r'[\w.\-]+', path, re.UNICODE) and not path.isdigit():
            return path
        return None

    @staticmethod
    def _resolve_via_api(screen_name: str, vk_session) -> Optional[int]:
        api = vk_session.get_api()
        screen_name = screen_name.lstrip('@')

        try:
            resolved = api.utils.resolveScreenName(
                screen_name=screen_name,
                v=VK_API_VERSION,
            )
            if resolved:
                obj_type = resolved.get('type', '')
                obj_id = resolved.get('object_id')
                if obj_id is not None and obj_type in ('group', 'page', 'event'):
                    return -int(obj_id)
                if obj_type == 'user':
                    raise ValueError(
                        f'«{screen_name}» — страница пользователя, а не сообщество. '
                        'Укажите ссылку на группу или паблик.'
                    )
        except ValueError:
            raise
        except vk_api.exceptions.ApiError as e:
            err = str(e).lower()
            if 'invalid access_token' in err:
                raise ValueError(
                    'Неверный токен. Получите новый на https://vkhost.github.io/'
                ) from e
            logger.warning("resolveScreenName(%s): %s", screen_name, e)
        except Exception as e:
            logger.warning("resolveScreenName(%s): %s", screen_name, e)

        try:
            response = api.groups.getById(group_id=screen_name, v=VK_API_VERSION)
            groups = response if isinstance(response, list) else response.get('groups', response)
            if isinstance(groups, dict) and 'items' in groups:
                groups = groups['items']
            if groups:
                gid = groups[0].get('id') if isinstance(groups[0], dict) else groups[0]
                return -int(gid)
        except vk_api.exceptions.ApiError as e:
            err = str(e).lower()
            if 'invalid access_token' in err:
                raise ValueError(
                    'Неверный токен. Получите новый на https://vkhost.github.io/'
                ) from e
            logger.warning("groups.getById(%s): %s", screen_name, e)
        except Exception as e:
            logger.warning("groups.getById(%s): %s", screen_name, e)

        return None

    @staticmethod
    def resolve_group_id(identifier, vk_session=None) -> Optional[int]:
        """
        Преобразует ссылку, screen_name или числовой ID в owner_id (отрицательный для групп).
        """
        if not identifier:
            return None

        raw = str(identifier).strip()
        if not raw:
            return None

        numeric = VKUrlParser._numeric_group_id(raw)
        if numeric is not None:
            return numeric

        path = None
        url_match = _VK_URL_RE.search(raw)
        if url_match:
            path = url_match.group('path').strip('/')
        elif VKUrlParser.is_vk_link(raw):
            legacy = re.search(r'vk\.com/(?:wall/)?([^?\s#]+)', raw, re.IGNORECASE)
            path = legacy.group(1).strip('/') if legacy else None

        if path:
            from_path = VKUrlParser._id_from_path(path)
            if from_path is not None:
                return from_path
            screen_name = path.split('/')[0]
        else:
            screen_name = VKUrlParser.extract_screen_name(raw)

        if not screen_name:
            return None

        if not vk_session:
            logger.error("Для «%s» нужен токен VK (resolveScreenName)", screen_name)
            return None

        return VKUrlParser._resolve_via_api(screen_name, vk_session)

    @staticmethod
    def extract_id_from_url(url, vk_api_instance=None):
        """Обратная совместимость."""
        return VKUrlParser.resolve_group_id(url, vk_api_instance)

    @staticmethod
    def is_valid_vk_url(url):
        return VKUrlParser.is_vk_link(url)
