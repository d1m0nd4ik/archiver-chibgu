import os
from datetime import datetime
import vk_api
import glob
from core.database import Database
from core.nlp_processor import NLPProcessor
from core.media_processor import MediaProcessor
from core.url_parser import VKUrlParser
from config.settings import DATA_DIR, PHOTOS_DIR, VIDEOS_DIR, VK_API_VERSION

class VKDownloader:
    """Класс для загрузки контента из ВКонтакте (без конвертации)"""
    def __init__(self, token, group_identifier):
        self.token = token
        self.vk_session = vk_api.VkApi(token=token)
        self.vk = self.vk_session.get_api()
        self.nlp = NLPProcessor()
        self.processor = MediaProcessor()
        self.db = Database()
        
        self.group_id = self._resolve_group_id(group_identifier)
        
        if not self.group_id:
            raise ValueError("Не удалось определить ID группы из ссылки")
        
        for folder in [DATA_DIR, PHOTOS_DIR, VIDEOS_DIR]:
            os.makedirs(folder, exist_ok=True)

    def _resolve_group_id(self, identifier):
        """Преобразует ссылку или ID в числовой ID группы"""
        identifier = str(identifier).strip()
        
        if VKUrlParser.is_valid_vk_url(identifier):
            return VKUrlParser.extract_id_from_url(identifier, self.vk_session)
        
        try:
            gid = int(identifier)
            return -abs(gid)
        except ValueError:
            return VKUrlParser.extract_id_from_url(f"https://vk.com/{identifier}", self.vk_session)

    def download_photo(self, url, post_id, photo_id):
        try:
            filename = f"{post_id}_{photo_id}.jpg"
            photo_path = os.path.join(PHOTOS_DIR, filename)
            
            if self.processor.download_file(url, photo_path):
                print(f"[OK] Фото сохранено: {photo_path}")
                return photo_path
            return None
        except Exception as e:
            print(f"Photo Download Error: {e}")
            return None

    def _build_vk_video_page_url(self, video_owner_id, video_id, access_key=None):
        """Формирует canonical VK video URL для yt-dlp VK extractor."""
        url = f"https://vk.com/video{video_owner_id}_{video_id}"
        if access_key:
            url = f"{url}?access_key={access_key}"
        return url

    def _resolve_video_url(self, video_owner_id, video_id, access_key=None, fallback_video_data=None):
        """Получает рабочий URL видео через VK API"""
        try:
            videos_value = f"{video_owner_id}_{video_id}"
            if access_key:
                videos_value = f"{videos_value}_{access_key}"

            video_info = self.vk.video.get(
                videos=videos_value,
                count=1,
                v=VK_API_VERSION
            )
            if 'items' in video_info and video_info['items']:
                item = video_info['items'][0]
                # Предпочитаем URL страницы видео VK, а не прямой okcdn
                player_url = item.get('player')
                page_url = item.get('url')
                if player_url and "vk.com" in str(player_url):
                    return player_url
                if page_url and "vk.com" in str(page_url):
                    return page_url

                canonical_url = self._build_vk_video_page_url(video_owner_id, video_id, access_key=access_key)
                if canonical_url:
                    return canonical_url

                # Пробуем найти прямой mp4 в files
                files = item.get('files', {})
                for quality in ('mp4_1080', 'mp4_720', 'mp4_480', 'mp4_360'):
                    if files.get(quality):
                        return files[quality]
                        
        except Exception as e:
            print(f"[VK API video.get Error] {e}")

        # Fallback: если в wall.attachments уже пришел player/url/files
        if fallback_video_data:
            player_url = fallback_video_data.get('player')
            page_url = fallback_video_data.get('url')
            if player_url and "vk.com" in str(player_url):
                return player_url
            if page_url and "vk.com" in str(page_url):
                return page_url

            canonical_url = self._build_vk_video_page_url(video_owner_id, video_id, access_key=access_key)
            if canonical_url:
                return canonical_url
                
            files = fallback_video_data.get('files', {})
            for quality in ('mp4_1080', 'mp4_720', 'mp4_480', 'mp4_360'):
                if files.get(quality):
                    return files[quality]

        return None

    def download_video(self, video_owner_id, video_id, post_id, output_path=None, fallback_video_data=None, access_key=None):
        try:
            video_url = self._resolve_video_url(
                video_owner_id,
                video_id,
                access_key=access_key,
                fallback_video_data=fallback_video_data
            )
            if not video_url:
                print(f"[VK] Видео {video_owner_id}_{video_id} не найдено")
                return None
            
            if not output_path:
                filename = f"{post_id}_{video_id}.mp4"
                output_path = os.path.join(VIDEOS_DIR, filename)
            
            # Скачиваем видео без конвертации
            result = self.processor.download_video_raw(video_url, output_path)
            
            if result:
                print(f"[VK] Видео успешно: {result}")
            else:
                print(f"[VK] Не удалось скачать видео: {video_url}")
            
            return result
        except Exception as e:
            print(f"[VK] Video Download Error: {e}")
            return None

    def parse_and_save(self, count=20, callback=None):
        """Парсинг стены группы и сохранение в базу"""
        # Удаляем зависшие временные файлы
        for temp_file in glob.glob(os.path.join(VIDEOS_DIR, "*.temp*")):
            try:
                os.remove(temp_file)
                print(f"[Cleanup] Удалён старый temp: {temp_file}")
            except:
                pass
        
        try:
            # Проверка токена
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
            
            posts = self.vk.wall.get(
                owner_id=self.group_id, 
                count=count, 
                v=VK_API_VERSION,
                extended=1  # ← Важно: возвращает полную информацию с метриками
            )['items']
            
            if not posts:
                if callback:
                    callback("Посты не найдены")
                return

            total = len(posts)
            processed = 0
            
            for post in posts:
                try:
                    post_id = post['id']
                    date = datetime.fromtimestamp(post['date']).strftime('%Y-%m-%d %H:%M')
                    text = post.get('text', '')
                    tags = self.nlp.generate_tags(text)
                    
                    # Извлекаем метрики из поста
                    likes = post.get('likes', {}).get('count', 0)
                    comments = post.get('comments', {}).get('count', 0)
                    shares = post.get('reposts', {}).get('count', 0)
                    views = post.get('views', {}).get('count', 0)
                    
                    # 1. Сохраняем пост (без медиа)
                    self.db.save_post(
                        original_post_id=post_id,
                        date=date,
                        text=text,
                        tags=tags,
                        likes=likes,
                        comments=comments,
                        shares=shares,
                        views=views
                    )

                    for attach in post.get('attachments', []):
                        att_type = attach['type']
                        media_path = None
                        media_key = None
                        media_id = None

                        if att_type == 'photo':
                            photo = attach['photo']
                            media_key = f"photo_{photo['id']}"
                            url = (
                                photo.get('sizes', [])[-1].get('url') or 
                                photo.get('photo_2560') or
                                photo.get('photo_1280')
                            )
                            if url:
                                # Скачиваем фото
                                filename = f"{post_id}_{photo['id']}.jpg"
                                temp_path = os.path.join(PHOTOS_DIR, filename)
                                
                                if self.processor.download_file(url, temp_path):
                                    media_path = temp_path
                                    print(f"[OK] Фото скачано: {media_path}")

                        elif att_type in ('video', 'clip'):
                            media_data = attach.get('video') or attach.get('clip')
                            if not media_data:
                                print(f"[WARNING] Пропущено {att_type} без данных в посте {post_id}")
                                continue

                            media_key = f"{att_type}_{media_data.get('id', 'unknown')}"
                            owner_id = media_data.get('owner_id')
                            access_key = media_data.get('access_key')
                            
                            print(f"[DEBUG] Обнаружено {att_type} | ID: {media_key} | Owner: {owner_id}")
                            
                            # Скачиваем видео
                            filename = f"{post_id}_{att_type}_{media_data.get('id')}.mp4"
                            output_path = os.path.join(VIDEOS_DIR, filename)
                            
                            media_path = self.download_video(
                                owner_id, 
                                media_data.get('id'), 
                                post_id, 
                                output_path=output_path,
                                fallback_video_data=media_data,
                                access_key=access_key
                            )
                            if media_path:
                                print(f"[OK] {att_type.title()} сохранён: {media_path}")
                            else:
                                print(f"[WARNING] Не удалось скачать {att_type} {media_key}")

                        # 2. Если файл скачался успешно, сохраняем его в attachments
                        if media_path and os.path.exists(media_path):
                            size = self.processor.get_file_size(media_path)
                            
                            self.db.save_media(
                                original_post_id=post_id,
                                media_type=att_type,
                                media_key=media_key,
                                media_path=media_path,
                                file_size=size
                            )
                            processed += 1
                            print(f"[DB] Медиа добавлено к посту {post_id}: {media_path}")

                except Exception as e:
                    print(f"Post processing error: {e}")
                    continue
        
            if callback:
                callback(f"Завершено! Сохранено: {processed} медиафайлов")
        
        except vk_api.exceptions.ApiError as e:
            if callback:
                callback(f"Ошибка VK API: {e}")
            raise
        except Exception as e:
            if callback:
                callback(f"Ошибка: {e}")
            raise
        finally:
            self.db.close()