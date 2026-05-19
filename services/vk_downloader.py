import os, time
from datetime import datetime
import vk_api
import glob
from core.database import Database
from core.nlp_processor import NLPProcessor
from core.media_processor import MediaProcessor
from core.url_parser import VKUrlParser
from core.vk_token import TOKEN_INVALID_MSG, is_auth_error
from config.settings import DATA_DIR, VK_API_VERSION
from core.logging_config import logger

class VKDownloader:
    """Класс для загрузки контента из ВКонтакте (без конвертации)"""
    
    def __init__(self, token, group_identifier):
        if not token or not str(token).strip():
            raise ValueError("Токен VK API не может быть пустым!")
        
        try:
            self.token = token
            self.vk_session = vk_api.VkApi(token=token)
            self.vk = self.vk_session.get_api()
        except Exception as e:
            error_msg = str(e)
            logger.error("VK API initialization failed: %s", error_msg)
            
            if "pka_resources" in error_msg:
                raise Exception("Ошибка библиотеки vk_api. Попробуйте переустановить: pip install --upgrade vk-api requests") from e
            elif is_auth_error(e):
                raise Exception(TOKEN_INVALID_MSG) from e
            else:
                raise Exception(f"Ошибка инициализации VK API: {error_msg}") from e
        
        self.nlp = NLPProcessor()
        self.processor = MediaProcessor()
        self.db = Database()
        self.group_id = self._resolve_group_id(group_identifier)
        
        if not self.group_id:
            raise ValueError("Не удалось определить ID группы из ссылки")
            
        for folder in [DATA_DIR]:
            os.makedirs(folder, exist_ok=True)

    def _fetch_posts_paginated(self, target_count: int) -> list:
        """Загружает посты порциями по 100 с соблюдением лимитов VK"""
        posts = []
        offset = 0
        limit_per_call = 100
        
        while offset < target_count:
            chunk = min(limit_per_call, target_count - offset)
            try:
                response = self.vk.wall.get(
                    owner_id=self.group_id, 
                    count=chunk, 
                    offset=offset,
                    v=VK_API_VERSION,
                    extended=1
                )
                items = response.get('items', [])
                if not items:
                    break
                posts.extend(items)
                offset += chunk
                time.sleep(0.35)  # Соблюдаем rate-limit
            except Exception as e:
                logger.error("[VK Pagination] Error at offset %d: %s", offset, e)
                break
        return posts

    def _resolve_group_id(self, identifier):
        """Преобразует ссылку, screen_name или числовой ID в owner_id группы."""
        group_id = VKUrlParser.resolve_group_id(identifier, self.vk_session)
        if group_id is not None:
            return group_id
        raise ValueError(VKUrlParser.format_resolve_hint(identifier))

    def download_photo(self, url, post_id, photo_id):
        try:
            filename = f"{post_id}_{photo_id}.jpg"
            photo_path = os.path.join(filename)
            
            if self.processor.download_file(url, photo_path):
                logger.info("[OK] Фото сохранено: %s", photo_path)
                return photo_path
            return None
        except Exception as e:
            logger.error("Photo Download Error: %s", e)
            return None

    def _build_vk_video_page_url(self, video_owner_id, video_id, access_key=None):
        """Формирует canonical VK video URL для yt-dlp VK extractor."""
        url = f"https://vk.com/video{video_owner_id}_{video_id}"
        if access_key:
            url = f"{url}?access_key={access_key}"
        return url

    _MP4_QUALITIES = (
        "mp4_2160", "mp4_1440", "mp4_1080", "mp4_720", "mp4_480", "mp4_360", "mp4_240", "mp4_144",
        "external", "src",
    )

    @classmethod
    def _pick_direct_mp4(cls, video_item):
        if not video_item or not isinstance(video_item, dict):
            return None
        files = video_item.get("files") or {}
        if isinstance(files, dict):
            for quality in cls._MP4_QUALITIES:
                url = files.get(quality)
                if url and str(url).startswith("http"):
                    return str(url)
        for key, url in video_item.items():
            if isinstance(key, str) and key.startswith("mp4_") and url and str(url).startswith("http"):
                return str(url)
        return None

    def _fetch_video_item(self, video_owner_id, video_id, access_key=None):
        videos_value = f"{video_owner_id}_{video_id}"
        if access_key:
            videos_value = f"{videos_value}_{access_key}"
        video_info = self.vk.video.get(videos=videos_value, count=1, v=VK_API_VERSION)
        items = video_info.get("items") if isinstance(video_info, dict) else video_info
        if items:
            return items[0]
        return None

    def _resolve_direct_mp4_url(self, video_owner_id, video_id, access_key=None, fallback_video_data=None):
        """Прямая ссылка на MP4 из VK API — без cookies и yt-dlp."""
        item = None
        try:
            item = self._fetch_video_item(video_owner_id, video_id, access_key=access_key)
        except Exception as e:
            logger.warning("[VK API video.get] %s", e)

        direct = self._pick_direct_mp4(item)
        if direct:
            return direct
        if fallback_video_data:
            return self._pick_direct_mp4(fallback_video_data)
        return None

    def _resolve_page_url(self, video_owner_id, video_id, access_key=None, fallback_video_data=None):
        """Страница VK для yt-dlp (если прямой MP4 недоступен)."""
        return self._build_vk_video_page_url(video_owner_id, video_id, access_key=access_key)

    def download_video(self, video_owner_id, video_id, post_id, output_path=None, fallback_video_data=None, access_key=None):
        try:
            if not output_path:
                output_path = os.path.join(f"{post_id}_{video_id}.mp4")

            direct_url = self._resolve_direct_mp4_url(
                video_owner_id, video_id, access_key=access_key, fallback_video_data=fallback_video_data
            )
            if direct_url:
                logger.info("[VK] Прямая ссылка MP4 (video.get)")
                if self.processor.download_file(direct_url, output_path):
                    logger.info("[VK] Видео успешно: %s", output_path)
                    return output_path
                logger.warning("[VK] Прямое скачивание не удалось, пробуем yt-dlp")

            page_url = self._resolve_page_url(
                video_owner_id, video_id, access_key=access_key, fallback_video_data=fallback_video_data
            )
            if not page_url:
                logger.info("[VK] Видео %s_%s не найдено", video_owner_id, video_id)
                return None

            result = self.processor.download_video_raw(page_url, output_path)

            if result:
                logger.info("[VK] Видео успешно: %s", result)
            else:
                logger.error(
                    "[VK] Не удалось скачать видео: %s. "
                    "Для закрытых роликов положите cookies.txt в папку проекта "
                    "(экспорт с vk.com) или укажите VK_USE_BROWSER_COOKIES=1 в .env.",
                    page_url,
                )

            return result
        except Exception as e:
            logger.error("[VK] Video Download Error: %s", e)
            return None

    def parse_and_save(self, count=20, callback=None):
        """Парсинг стены группы и сохранение в базу"""
        for temp_file in glob.glob(os.path.join("*.temp*")):
            try:
                os.remove(temp_file)
                logger.info("[Cleanup] Удалён старый temp: %s", temp_file)
            except Exception:
                pass
        
        try:
            try:
                self.vk.groups.getById(v=VK_API_VERSION)
            except vk_api.exceptions.ApiError as e:
                error_text = str(e).lower()
                if "invalid access_token" in error_text:
                    raise Exception("Неверный или устаревший токен! Получите новый на: https://vkhost.github.io/")
                if "[27]" in error_text or "group authorization failed" in error_text:
                    raise Exception(
                        "Текущий токен не подходит для чтения стены/видео. "
                        "Используйте пользовательский токен с правами wall, groups, photos, video."
                    )
                raise
            
            posts = self._fetch_posts_paginated(count)
            
            if not posts:
                if callback: callback("Посты не найдены")
                return

            total = len(posts)
            processed = 0
            
            for post in posts:
                try:
                    post_id = post['id']
                    date = datetime.fromtimestamp(post['date']).strftime('%Y-%m-%d %H:%M')
                    text = post.get('text', '')
                    tags = self.nlp.generate_tags(text)
                    
                    likes = post.get('likes', {}).get('count', 0)
                    comments = post.get('comments', {}).get('count', 0)
                    shares = post.get('reposts', {}).get('count', 0)

                    self.db.save_post(
                        original_post_id=post_id, date=date, text=text, tags=tags,
                        likes=likes, comments=comments, shares=shares
                    )

                    for attach in post.get('attachments', []):
                        att_type = attach['type']
                        media_path = None
                        media_key = None

                        if att_type == 'photo':
                            photo = attach['photo']
                            media_key = f"photo_{photo['id']}"
                            url = (photo.get('sizes', [])[-1].get('url') or 
                                   photo.get('photo_2560') or photo.get('photo_1280'))
                            if url:
                                filename = f"{post_id}_{photo['id']}.jpg"
                                temp_path = os.path.join(filename)
                                
                                if self.processor.download_file(url, temp_path):
                                    media_path = temp_path
                                    logger.info("[OK] Фото скачано: %s", media_path)

                        elif att_type in ('video', 'clip'):
                            media_data = attach.get('video') or attach.get('clip')
                            if not media_data:
                                logger.warning("[WARNING] Пропущено %s без данных в посте %d", att_type, post_id)
                                continue

                            media_key = f"{att_type}_{media_data.get('id', 'unknown')}"
                            owner_id = media_data.get('owner_id')
                            access_key = media_data.get('access_key')
                            
                            logger.info("[DEBUG] Обнаружено %s | ID: %s | Owner: %s", att_type, media_key, owner_id)
                            
                            filename = f"{post_id}_{att_type}_{media_data.get('id')}.mp4"
                            output_path = os.path.join(filename)
                            
                            media_path = self.download_video(
                                owner_id, media_data.get('id'), post_id, 
                                output_path=output_path, fallback_video_data=media_data, access_key=access_key
                            )
                            if media_path:
                                logger.info("[OK] %s сохранён: %s", att_type.title(), media_path)
                            else:
                                logger.warning("[WARNING] Не удалось скачать %s %s", att_type, media_key)

                        if media_path and os.path.exists(media_path):
                            size = self.processor.get_file_size(media_path)
                            self.db.save_media(
                                original_post_id=post_id, media_type=att_type, 
                                media_key=media_key, media_path=media_path, file_size=size
                            )
                            processed += 1
                            logger.info("[DB] Медиа добавлено к посту %d: %s", post_id, media_path)

                except Exception as e:
                    logger.error("Post processing error: %s", e)
                    continue
        
            if callback: callback(f"Завершено! Сохранено: {processed} медиафайлов")
        
        except vk_api.exceptions.ApiError as e:
            if callback: callback(f"Ошибка VK API: {e}")
            raise
        except Exception as e:
            if callback: callback(f"Ошибка: {e}")
            raise
        finally:
            self.db.close()