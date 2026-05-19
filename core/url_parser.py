import re
from typing import Optional

import vk_api

from config.settings import VK_API_VERSION
from core.logging_config import logger
from core.vk_token import TOKEN_INVALID_MSG, ensure_token_valid, is_auth_error

# vk.com, vk.ru, мобильные и без схемы
_VK_HOST = r'(?:vk\.com|vk\.ru|m\.vk\.com|m\.vk\.ru)'
_VK_URL_RE = re.compile(
    rf'(?:https?://)?(?:www\.)?{_VK_HOST}/(?P<path>[^?\s#]+)',
    re.IGNORECASE,
)
_VK_PATH_FALLBACK_RE = re.compile(
    rf'(?:https?://)?(?:www\.)?{_VK_HOST}/(?:wall/)?(?P<path>[^?\s#]+)',
    re.IGNORECASE,
)
_SCREEN_NAME_RE = re.compile(r'^[A-Za-z0-9][A-Za-z0-9_.\-]{0,63}$')
_COMMUNITY_TYPES = frozenset({'group', 'page', 'event', 'vk_group', 'community'})


class VKUrlParser:
    """Извлечение и разрешение ID сообщества ВКонтакте из ссылки, screen_name или числа."""

    @staticmethod
    def is_vk_link(text: str) -> bool:
        if not text:
            return False
        t = text.strip()
        return bool(_VK_URL_RE.search(t) or re.search(rf'\b{_VK_HOST}/', t, re.IGNORECASE))

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
    def _owner_id_from_numeric_in_path(path: str):
        """public123, club123, event123, wall-123_45 или просто цифры."""
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
    def _extract_path_from_raw(raw: str) -> Optional[str]:
        raw = raw.strip()
        if not raw:
            return None

        url_match = _VK_URL_RE.search(raw)
        if url_match:
            return url_match.group('path').strip('/')

        fallback = _VK_PATH_FALLBACK_RE.search(raw)
        if fallback:
            return fallback.group('path').strip('/')

        bare = raw.lstrip('@').strip('/')
        if _SCREEN_NAME_RE.fullmatch(bare):
            return bare

        if re.fullmatch(r'[\w.\-]+', raw, re.UNICODE) and not raw.isdigit():
            return raw.strip('/').lstrip('@')

        return None

    @staticmethod
    def _screen_name_from_path(path: str) -> Optional[str]:
        if not path:
            return None

        first_segment = path.split('/')[0].strip()
        if not first_segment or VKUrlParser._owner_id_from_numeric_in_path(first_segment) is not None:
            return None

        name = first_segment.lstrip('@')
        if _SCREEN_NAME_RE.fullmatch(name):
            return name
        return None

    @staticmethod
    def extract_screen_name(identifier: str) -> Optional[str]:
        """Короткое имя из URL или строки (chibgu_archiver, @group)."""
        if not identifier:
            return None

        raw = identifier.strip().split('?')[0].split('#')[0]
        numeric = VKUrlParser._numeric_group_id(raw)
        if numeric is not None and raw.lstrip('-').isdigit():
            return None

        path = VKUrlParser._extract_path_from_raw(raw)
        if not path:
            return None

        if VKUrlParser._owner_id_from_numeric_in_path(path) is not None:
            return None

        return VKUrlParser._screen_name_from_path(path)

    @staticmethod
    def _parse_groups_list(response) -> list:
        if response is None:
            return []
        if isinstance(response, list):
            return response
        if isinstance(response, dict):
            groups = response.get('groups', response.get('items', []))
            if isinstance(groups, dict) and 'items' in groups:
                return groups['items'] or []
            if isinstance(groups, list):
                return groups
        return []

    @staticmethod
    def _group_id_from_item(item) -> Optional[int]:
        if isinstance(item, dict):
            gid = item.get('id')
        else:
            gid = item
        if gid is None:
            return None
        return -abs(int(gid))

    @staticmethod
    def _groups_get_by_id(api, screen_name: str) -> Optional[int]:
        """groups.getById по короткому имени или числовому ID."""
        for kwargs in (
            {'group_ids': screen_name},
            {'group_id': screen_name},
        ):
            try:
                response = api.groups.getById(v=VK_API_VERSION, **kwargs)
                groups = VKUrlParser._parse_groups_list(response)
                if groups:
                    return VKUrlParser._group_id_from_item(groups[0])
            except vk_api.exceptions.ApiError as e:
                if is_auth_error(e):
                    raise ValueError(TOKEN_INVALID_MSG) from e
                logger.debug("groups.getById(%s) %s: %s", screen_name, kwargs, e)
            except Exception as e:
                logger.debug("groups.getById(%s): %s", screen_name, e)
        return None

    @staticmethod
    def _groups_search(api, screen_name: str) -> Optional[int]:
        try:
            response = api.groups.search(
                q=screen_name,
                count=20,
                v=VK_API_VERSION,
            )
            items = response.get('items', []) if isinstance(response, dict) else (response or [])
            if not items:
                return None

            target = screen_name.lower()
            for item in items:
                if str(item.get('screen_name', '')).lower() == target:
                    return VKUrlParser._group_id_from_item(item)

            return VKUrlParser._group_id_from_item(items[0])
        except vk_api.exceptions.ApiError as e:
            logger.debug("groups.search(%s): %s", screen_name, e)
        except Exception as e:
            logger.debug("groups.search(%s): %s", screen_name, e)
        return None

    @staticmethod
    def _resolve_via_api(screen_name: str, vk_session) -> Optional[int]:
        api = vk_session.get_api()
        screen_name = screen_name.lstrip('@').strip()
        if not screen_name:
            return None

        try:
            resolved = api.utils.resolveScreenName(
                screen_name=screen_name,
                v=VK_API_VERSION,
            )
            if resolved:
                obj_type = (resolved.get('type') or '').lower()
                obj_id = resolved.get('object_id')
                if obj_id is not None and obj_type in _COMMUNITY_TYPES:
                    return -abs(int(obj_id))
                if obj_type == 'user':
                    raise ValueError(
                        f'«{screen_name}» — страница пользователя, а не сообщество. '
                        'Укажите ссылку на группу или паблик.'
                    )
        except ValueError:
            raise
        except vk_api.exceptions.ApiError as e:
            if is_auth_error(e):
                raise ValueError(TOKEN_INVALID_MSG) from e
            logger.warning("resolveScreenName(%s): %s", screen_name, e)
        except Exception as e:
            logger.warning("resolveScreenName(%s): %s", screen_name, e)

        gid = VKUrlParser._groups_get_by_id(api, screen_name)
        if gid is not None:
            return gid

        return VKUrlParser._groups_search(api, screen_name)

    @staticmethod
    def resolve_group_id(identifier, vk_session=None) -> Optional[int]:
        """
        Преобразует ссылку, screen_name или числовой ID в owner_id (отрицательный для групп).

        Поддерживаются форматы:
        - https://vk.ru/chibgu_archiver
        - https://vk.com/club123, public123, event123
        - vk.ru/group_name, @group_name, group_name
        - 236813059, -236813059
        """
        if not identifier:
            return None

        raw = str(identifier).strip()
        if not raw:
            return None

        numeric = VKUrlParser._numeric_group_id(raw)
        if numeric is not None:
            return numeric

        path = VKUrlParser._extract_path_from_raw(raw)
        if path:
            from_path = VKUrlParser._owner_id_from_numeric_in_path(path)
            if from_path is not None:
                return from_path
            screen_name = VKUrlParser._screen_name_from_path(path)
        else:
            screen_name = VKUrlParser.extract_screen_name(raw)

        if not screen_name:
            logger.warning("Не удалось извлечь имя сообщества из: %s", raw)
            return None

        if not vk_session:
            logger.error("Для «%s» нужен токен VK", screen_name)
            return None

        try:
            ensure_token_valid(vk_session)
        except ValueError:
            raise

        return VKUrlParser._resolve_via_api(screen_name, vk_session)

    @staticmethod
    def extract_id_from_url(url, vk_api_instance=None):
        """Обратная совместимость."""
        return VKUrlParser.resolve_group_id(url, vk_api_instance)

    @staticmethod
    def is_valid_vk_url(url):
        return VKUrlParser.is_vk_link(url)

    @staticmethod
    def format_resolve_hint(identifier: str) -> str:
        return (
            f"Не удалось определить сообщество по «{identifier}».\n\n"
            "Укажите одно из:\n"
            "• ссылку: https://vk.ru/имя_группы или https://vk.com/club123\n"
            "• короткое имя: chibgu_archiver\n"
            "• числовой ID: 236813059"
        )
