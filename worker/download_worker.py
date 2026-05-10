from PySide6.QtCore import QThread, Signal, QObject
# Примечание: если у вас папка называется core, замените services на core
from services.vk_downloader import VKDownloader
from core.employee_tagger import EmployeeTagger
from core.nlp_processor import NLPProcessor
from core.media_processor import MediaProcessor
from core.database import Database
import vk_api
import datetime
import os
import re
from config.settings import VK_API_VERSION
from core.logging_config import logger

class WorkerSignals(QObject):
    """Сигналы для воркера"""
    progress = Signal(str)
    finished = Signal()
    error = Signal(str)

class DownloadWorker(QThread):
    """Воркер для загрузки в отдельном потоке"""
    def __init__(self, token, group_identifier, count=20):
        super().__init__()
        self.token = token
        self.group_identifier = group_identifier
        self.count = count
        self.signals = WorkerSignals()
        self.is_running = True

    def run(self):
        try:
            self.signals.progress.emit("🔄 Инициализация...")
            
            vk = VKDownloader(self.token, self.group_identifier)
            tagger = EmployeeTagger()
            nlp = NLPProcessor()
            
            self.signals.progress.emit(f"📥 Загрузка постов из группы {self.group_identifier}...")
            
            # 🔹 ПАГИНАЦИЯ VK API (максимум 100 за запрос)
            posts = []
            offset = 0
            limit_per_call = 100
            
            while offset < self.count:
                if not self.is_running: break
                chunk = min(limit_per_call, self.count - offset)
                try:
                    response = vk.vk.wall.get(
                        owner_id=vk.group_id,
                        count=chunk,
                        offset=offset,
                        v=VK_API_VERSION,
                        extended=1
                    )
                    items = response.get('items', [])
                    if not items: break
                    posts.extend(items)
                    offset += chunk
                    self.signals.progress.emit(f"Загружено {len(posts)}/{self.count} постов...")
                except vk_api.exceptions.ApiError as e:
                    error_text = str(e).lower()
                    if "[27]" in error_text or "group authorization failed" in error_text:
                        raise Exception("Токен сообщества не подходит для wall.get. Используйте пользовательский токен с правами wall, groups, photos, video.")
                    if "invalid access_token" in error_text:
                        raise Exception("Неверный или устаревший токен. Получите новый токен и повторите.")
                    raise
                except Exception as e:
                    self.signals.error.emit(f"Ошибка сети: {e}")
                    return

            if not posts:
                self.signals.progress.emit("Посты не найдены")
                return
            
            total = len(posts)
            processed = 0
            
            for post in posts:
                if not self.is_running: break
                  
                post_date = post['date']
                post_id = post['id']

                likes = post.get('likes', {}).get('count', 0)
                comments = post.get('comments', {}).get('count', 0)
                shares = post.get('reposts', {}).get('count', 0)
                views = post.get('views', {}).get('count', 0)

                if vk.db.post_exists(post_id):
                    if vk.db.update_post_stats(post_id, likes, comments, shares, views):
                        self.signals.progress.emit(f"🔁 Обновлены лайки/просмотры поста {post_id}")
                    else:
                        self.signals.progress.emit(f"⚠️ Не удалось обновить статистику поста {post_id}")
                    continue
                
                date = datetime.datetime.fromtimestamp(post_date).strftime('%Y-%m-%d %H:%M')
                text = post.get('text', '')
                 
                all_tags = set(tagger.get_all_tags(text, include_keywords=True))
                nlp_tags = nlp.generate_tags(text)
                if nlp_tags:
                    all_tags.update(nlp_tags.split())
                all_tags.update(f"#{tag}" for tag in re.findall(r'#([A-Za-zА-Яа-яЁё0-9_]+)', text))
                found_tags = sorted(all_tags)
                
                attachments = post.get('attachments', [])
                folder_path = MediaProcessor.get_date_folder_path(post_date)
                os.makedirs(folder_path, exist_ok=True)
                
                vk.db.save_post(
                    original_post_id=post_id, date=date, text=text,
                    tags=" ".join(found_tags) if found_tags else "",
                    likes=likes, comments=comments, shares=shares, views=views
                )
                
                for index, attach in enumerate(attachments, 1):
                    att_type = attach['type']
                    media_path = None
                    media_key = f"{att_type}_{index}"
                    
                    if att_type == 'photo':
                        photo = attach['photo']
                        photo_id = photo.get('id', index)
                        url = (photo.get('sizes', [])[-1].get('url') or 
                               photo.get('photo_2560') or photo.get('photo_1280'))
                        if url:
                            media_key = f"photo_{photo_id}"
                            photo_path = os.path.join(folder_path, f"post_{post_id}_photo_{photo_id}.jpg")
                            if MediaProcessor.download_file(url, photo_path):
                                media_path = photo_path
                                processed += 1
                                logger.info("Фото сохранено: %s", media_path)

                    elif att_type in ('video', 'clip'):
                        media_data = attach.get('video') or attach.get('clip')
                        if not media_data: continue

                        video_id = media_data.get('id', index)
                        owner_id = media_data.get('owner_id')
                        access_key = media_data.get('access_key')
                        media_key = f"{att_type}_{owner_id}_{video_id}"
                        
                        thumb_url = None
                        if 'image' in media_data and media_data['image']:
                            images = media_data['image']
                            if isinstance(images, list) and len(images) > 0:
                                last_img = images[-1]
                                thumb_url = last_img.get('url') if isinstance(last_img, dict) else last_img
                            elif isinstance(images, str):
                                thumb_url = images

                        if thumb_url and isinstance(thumb_url, str) and thumb_url.startswith('http'):
                            try:
                                thumb_filename = f"post_{post_id}_{att_type}_{video_id}_thumb.jpg"
                                thumb_path = os.path.join(folder_path, thumb_filename)
                                MediaProcessor.download_thumbnail(thumb_url, thumb_path)
                            except Exception as e:
                                logger.error("Ошибка превью: %s", e)
                        
                        media_path = os.path.join(folder_path, f"post_{post_id}_{att_type}_{video_id}.mp4")
                        downloaded_video_path = vk.download_video(
                            owner_id, video_id, post_id, output_path=media_path,
                            fallback_video_data=media_data, access_key=access_key
                        )

                        if downloaded_video_path:
                            media_path = downloaded_video_path
                            processed += 1
                        else:
                            logger.info("Пропуск %s %s", att_type, video_id)

                    if media_path and os.path.exists(media_path):
                        size = MediaProcessor.get_file_size(media_path)
                        vk.db.save_media(
                            original_post_id=post_id, media_type=att_type,
                            media_key=media_key, media_path=media_path, file_size=size
                        )
                        logger.info("Медиа добавлено к посту %d: %s", post_id, media_path)

            self.signals.progress.emit(f"Обработано: {processed}/{total}")
            vk.db.close()
            self.signals.progress.emit(f"Завершено! Сохранено: {processed} файлов")
            self.signals.finished.emit()
            
        except Exception as e:
            self.signals.error.emit(f"Ошибка: {str(e)}")