"""Проверка токена VK API."""
import vk_api

from config.settings import VK_API_VERSION

TOKEN_HELP_URL = "https://vkhost.github.io/"

TOKEN_INVALID_MSG = (
    "Токен VK недействителен или истёк.\n\n"
    f"Получите новый токен на {TOKEN_HELP_URL}\n"
    "и вставьте его в «Настройки» → «Токен доступа»."
)


def is_auth_error(exc: BaseException) -> bool:
    text = str(exc).lower()
    if "invalid access_token" in text:
        return True
    if "access_token has expired" in text or "user authorization failed" in text:
        return True
    if isinstance(exc, vk_api.exceptions.ApiError):
        code = getattr(exc, "code", None)
        if code in (5, 28):
            return True
    return False


def ensure_token_valid(vk_session) -> None:
    """Проверяет токен запросом к API. ValueError — если токен не работает."""
    api = vk_session.get_api()
    try:
        api.users.get(v=VK_API_VERSION)
    except vk_api.exceptions.ApiError as e:
        if is_auth_error(e):
            raise ValueError(TOKEN_INVALID_MSG) from e
        raise ValueError(f"Ошибка VK API при проверке токена:\n{e}") from e
    except ValueError:
        raise
    except Exception as e:
        raise ValueError(f"Не удалось проверить токен:\n{e}") from e
