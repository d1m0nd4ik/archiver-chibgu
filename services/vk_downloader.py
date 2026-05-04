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
    """Класс для загрузки контента из ВКонтакте"""
    
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
            temp_path = os.path.join(PHOTOS_DIR, filename)
            webp_path = os.path.join(PHOTOS_DIR, f"{post_id}_{photo_id}.webp")
            
            if self.processor.download_file(url, temp_path):
                result = self.processor.convert_to_webp(temp_path, webp_path)
                if os.path.exists(temp_path):
                    os.remove(temp_path)
                return result
            return None
        except Exception as e:
            print(f"Photo Download Error: {e}")
            return None

    def _extract_best_video_url(self, video_data):
        """Возвращает лучший доступный URL видео"""
        # Сначала пробуем player-ссылку VK: она стабильнее, чем okcdn links с srcIp.
        player_url = video_data.get('player')
        if player_url and "vk.com" in str(player_url):
            return player_url

        page_url = video_data.get('url')
        if page_url and "vk.com" in str(page_url):
            return page_url

        files = video_data.get('files', {})
        for quality in ('mp4_1080', 'mp4_720', 'mp4_480', 'mp4_360', 'mp4_240'):
            if files.get(quality):
                return files[quality]
        return page_url or player_url

    def _build_vk_video_page_url(self, video_owner_id, video_id, access_key=None):
        """Формирует canonical VK video URL для yt-dlp VK extractor."""
        url = f"https://vk.com/video{video_owner_id}_{video_id}"
        if access_key:
            url = f"{url}?access_key={access_key}"
        return url

    def _resolve_video_url(self, video_owner_id, video_id, access_key=None, fallback_video_data=None):
        """Получает рабочий URL видео через VK API"""
        # 1) Основной путь: video.get (поддерживается шире, чем getById)
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
                # 1) Предпочитаем URL страницы видео VK, а не прямой okcdn,
                # т.к. okcdn может быть привязан к srcIp и давать HTTP 400.
                player_url = item.get('player')
                page_url = item.get('url')
                if player_url and "vk.com" in str(player_url):
                    return player_url
                if page_url and "vk.com" in str(page_url):
                    return page_url

                canonical_url = self._build_vk_video_page_url(video_owner_id, video_id, access_key=access_key)
                if canonical_url:
                    return canonical_url

                best_url = self._extract_best_video_url(item)
                if best_url:
                    return best_url
        except Exception as e:
            print(f"[VK API video.get Error] {e}")

        # 2) Fallback: если в wall.attachments уже пришел player/url/files
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

            best_url = self._extract_best_video_url(fallback_video_data)
            if best_url:
                return best_url

        return None

    def download_video(self, video_owner_id, video_id, post_id, output_path=None, fallback_video_data=None, access_key=None):
        try:
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
            except Exception as e:
                print(f"[VK API Error] {e}")
                return None
            
            if not output_path:
                filename = f"{post_id}_{video_id}.mp4"
                output_path = os.path.join(VIDEOS_DIR, filename)
            
            if ".mp4" in video_url:
                if self.processor.download_file(video_url, output_path):
                    print(f"[VK] Видео успешно (прямой mp4): {output_path}")
                    return output_path

            print(f"[VK] Обработка видео: {video_url[:50]}...")
            result = self.processor.enhance_and_convert_video(video_url, output_path)
            
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
            # Проверка токена методом, который доступен и при group auth.
            # users.get недоступен для токена сообщества и давал ложную ошибку.
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
            success = 0
            
            for post in posts:
                try:
                    post_id = post['id']
                    date = datetime.fromtimestamp(post['date']).strftime('%Y-%m-%d %H:%M')
                    text = post.get('text', '')
                    tags = self.nlp.generate_tags(text)
                    
                    # Извлекаем метрики из поста
                    likes = post.get('likes', {}).get('count', 0) if isinstance(post.get('likes'), dict) else post.get('likes', 0)
                    comments = post.get('comments', {}).get('count', 0) if isinstance(post.get('comments'), dict) else post.get('comments', 0)
                    shares = post.get('reposts', {}).get('count', 0) if isinstance(post.get('reposts'), dict) else post.get('reposts', 0)
                    views = post.get('views', {}).get('count', 0) if isinstance(post.get('views'), dict) else post.get('views', 0)
                    
                    attachments = post.get('attachments', [])
                    
                    for attach in attachments:
                        att_type = attach['type']
                        print(f"[DEBUG] Тип вложения: {att_type}")  # ОТЛАДКА
                        media_path = None
                        media_id = None
                        media_metrics = {'likes': 0, 'comments': 0, 'shares': 0, 'views': 0}
                        
                        if att_type == 'photo':
                            photo = attach['photo']
                            media_id = f"photo_{photo['id']}"
                            url = (
                                photo.get('sizes', [])[-1].get('url') or 
                                photo.get('photo_2560') or
                                photo.get('photo_1280')
                            )
                            # Парсим метрики фото из VK API
                            photo_likes = photo.get('likes', {}).get('count', 0) if isinstance(photo.get('likes'), dict) else photo.get('likes', 0)
                            photo_comments = photo.get('comments', {}).get('count', 0) if isinstance(photo.get('comments'), dict) else photo.get('comments', 0)
                            photo_views = photo.get('views', 0)
                            media_metrics = {'likes': photo_likes, 'comments': photo_comments, 'shares': 0, 'views': photo_views}
                            print(f"[PHOTO METRICS] ID: {media_id} | Лайки: {photo_likes}, Комм: {photo_comments}, Просмотры: {photo_views}")
                            
                            if url:
                                print(f"[DEBUG] Скачиваем фото: {url[:50]}...")  # ОТЛАДКА
                                media_path = self.download_photo(url, post_id, photo['id'])
                        
                        elif att_type == 'video':
                            print(f"[DEBUG] Обнаружено видео!")  # ОТЛАДКА
                            video = attach['video']
                            media_id = f"video_{video['id']}"
                            print(f"[DEBUG] Video ID: {video.get('id')}, Owner: {video.get('owner_id')}")  # ОТЛАДКА
                            
                            # Парсим метрики видео из VK API
                            video_likes = video.get('likes', {}).get('count', 0) if isinstance(video.get('likes'), dict) else video.get('likes', 0)
                            video_comments = video.get('comments', {}).get('count', 0) if isinstance(video.get('comments'), dict) else video.get('comments', 0)
                            video_views = video.get('views', 0)
                            media_metrics = {'likes': video_likes, 'comments': video_comments, 'shares': 0, 'views': video_views}
                            print(f"[VIDEO METRICS] ID: {media_id} | Лайки: {video_likes}, Комм: {video_comments}, Просмотры: {video_views}")
                            
                            media_path = self.download_video(
                                video['owner_id'], 
                                video['id'], 
                                post_id
                            )
                            if media_path:
                                print(f"[DEBUG] Видео скачано: {media_path}")  # ОТЛАДКА
                            else:
                                print(f"[DEBUG] ⚠️ Видео НЕ скачано!")  # ОТЛАДКА
                        
                        if media_path:
                            size = self.processor.get_file_size(media_path)
                            
                            # Создаём УНИКАЛЬНЫЙ ID для каждого медиа (для БД)
                            import hashlib
                            unique_id = int(hashlib.md5(f"{post_id}_{att_type}".encode()).hexdigest()[:8], 16)
                            
                            print(f"[DB] Сохранение поста: type={att_type}, path={media_path}, original_post_id={post_id}")
                            print(f"[DB] Метрики поста: лайки={likes}, комм.={comments}, поделиться={shares}, просмотры={views}")
                            try:
                                result = self.db.save_post(
                                    post_id=unique_id,          # Уникальный ID для БД
                                    original_post_id=post_id,   # Оригинальный VK post_id для группировки
                                    date=date,
                                    text=text,
                                    tags=tags,
                                    media_type=att_type,
                                    media_path=media_path,
                                    file_size=size,
                                    likes=likes,
                                    comments=comments,
                                    shares=shares,
                                    views=views
                                )
                                print(f"[DB] Результат сохранения поста: {result}")
                                if result:
                                    success += 1
                                
                                # Сохраняем отдельные метрики медиа в media_statistics
                                print(f"[DB] Сохранение статистики медиа: {media_id}")
                                self.db.save_media_statistics(
                                    post_id=unique_id,
                                    media_key=media_id,
                                    media_type=att_type,
                                    date=date,
                                    likes=media_metrics['likes'],
                                    comments=media_metrics['comments'],
                                    shares=media_metrics['shares'],
                                    views=media_metrics['views']
                                )
                                print(f"[DB] Медиа-метрики сохранены: {media_id} | {media_metrics}")
                            except Exception as e:
                                print(f"[DB ERROR] {e}")
                                import traceback
                                traceback.print_exc()
                        
                        processed += 1
                
                except Exception as e:
                    print(f"Post processing error: {e}")
                    continue
            
            if callback:
                callback(f"Завершено! Сохранено: {success} медиафайлов")
            
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