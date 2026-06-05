"""Cookies VK для yt-dlp и прямого скачивания с CDN."""
import os
import tempfile
from pathlib import Path
from urllib.parse import urlparse

import requests

from config.paths import get_data_root
from core.logging_config import logger

_COOKIE_FILE_NAMES = ("cookies.txt", "cookies_vk.txt", "vk_cookies.txt")
_VK_COOKIE_MARKERS = (".vk.com", ".vk.ru", "vk.com\t", "vk.ru\t")


def _project_root() -> Path:
    return get_data_root()


def find_cookie_file() -> str | None:
    env_path = (os.getenv("VK_COOKIES_FILE") or "").strip()
    if env_path:
        path = Path(env_path)
        if not path.is_absolute():
            path = _project_root() / path
        if path.is_file():
            return str(path.resolve())

    for name in _COOKIE_FILE_NAMES:
        path = _project_root() / name
        if path.is_file():
            return str(path.resolve())
    return None


def _browser_names() -> list[str]:
    raw = (os.getenv("VK_COOKIES_BROWSER") or "edge,chrome,firefox").strip()
    return [b.strip().lower() for b in raw.split(",") if b.strip()]


def cookies_from_browser_enabled() -> bool:
    """На Windows чтение cookies из браузера часто падает с DPAPI — по умолчанию выключено."""
    val = (os.getenv("VK_USE_BROWSER_COOKIES") or "").strip().lower()
    return val in ("1", "true", "yes", "on")


def is_valid_cookie_file(path: str) -> bool:
    try:
        text = Path(path).read_text(encoding="utf-8", errors="ignore")
    except OSError as e:
        logger.warning("Не удалось прочитать файл cookies %s: %s", path, e)
        return False
    if len(text.strip()) < 20:
        return False
    lower = text.lower()
    return any(marker in lower for marker in _VK_COOKIE_MARKERS)


def _cookie_file_opts(path: str) -> dict:
    return {"cookiefile": path}


def _browser_opts(browser: str) -> dict:
    return {"cookiesfrombrowser": (browser,)}


def iter_ytdlp_cookie_strategies():
    """
    Варианты для yt-dlp по приоритету:
    1) без cookies (публичные видео / access_key в URL)
    2) cookies.txt / VK_COOKIES_FILE (если файл валидный)
    3) cookiesfrombrowser — только при VK_USE_BROWSER_COOKIES=1
    4) browser-cookie3 (если установлен и включены браузерные cookies)
    """
    yield "none", {}

    cookie_file = find_cookie_file()
    if cookie_file:
        if is_valid_cookie_file(cookie_file):
            yield "cookiefile", _cookie_file_opts(cookie_file)
        else:
            logger.warning(
                "Файл cookies найден (%s), но не похож на экспорт VK — пропускаем. "
                "Экспортируйте cookies с vk.com через расширение «Get cookies.txt LOCALLY».",
                cookie_file,
            )

    if not cookies_from_browser_enabled():
        return

    for browser in _browser_names():
        yield f"browser:{browser}", _browser_opts(browser)

    try:
        import browser_cookie3
    except ImportError:
        return

    for browser in _browser_names():
        loader_name = f"_load_{browser}"
        loader = getattr(browser_cookie3, loader_name, None)
        if loader is None:
            continue
        try:
            jar = loader(domain_name=".vk.com")
            if not jar:
                continue
            fd, tmp_path = tempfile.mkstemp(suffix=".txt", prefix="vk_cookies_")
            os.close(fd)
            with open(tmp_path, "w", encoding="utf-8") as f:
                f.write("# Netscape HTTP Cookie File\n")
                for cookie in jar:
                    secure = "TRUE" if cookie.secure else "FALSE"
                    line = (
                        f"{cookie.domain}\tTRUE\t{cookie.path}\t{secure}\t"
                        f"{int(cookie.expires or 0)}\t{cookie.name}\t{cookie.value}\n"
                    )
                    f.write(line)
            yield f"browser_cookie3:{browser}", _cookie_file_opts(tmp_path)
        except Exception as e:
            logger.debug("browser_cookie3(%s): %s", browser, e)


def apply_cookie_strategy(ydl_opts: dict, strategy_opts: dict) -> dict:
    merged = dict(ydl_opts)
    merged.pop("cookiefile", None)
    merged.pop("cookiesfrombrowser", None)
    merged.update(strategy_opts)
    return merged


_VK_CDN_HOST_MARKERS = (
    "okcdn.ru",
    "vkuser.net",
    "vkuseraudio.net",
    "mycdn.me",
    "vk-cdn",
    "userapi.com",
)


def is_vk_cdn_url(url: str) -> bool:
    if not url:
        return False
    host = urlparse(url).netloc.lower()
    return any(marker in host for marker in _VK_CDN_HOST_MARKERS)


def build_vk_download_session() -> requests.Session | None:
    """Session с cookies для прямого скачивания с CDN VK (если есть cookies.txt)."""
    cookie_file = find_cookie_file()
    if not cookie_file or not is_valid_cookie_file(cookie_file):
        return None
    try:
        from http.cookiejar import MozillaCookieJar

        session = requests.Session()
        session.headers.update(
            {
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/120.0.0.0 Safari/537.36"
                ),
                "Referer": "https://vk.com/",
                "Origin": "https://vk.com",
                "Accept": "*/*",
            }
        )
        jar = MozillaCookieJar(cookie_file)
        jar.load(ignore_discard=True, ignore_expires=True)
        session.cookies = jar
        return session
    except Exception as e:
        logger.debug("build_vk_download_session: %s", e)
        return None
