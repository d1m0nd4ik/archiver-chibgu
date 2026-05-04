from PySide6.QtCore import QThread, Signal, QObject
from services.vk_downloader import VKDownloader
from core.employee_tagger import EmployeeTagger
from core.nlp_processor import NLPProcessor
from core.media_processor import MediaProcessor
from core.database import Database
import vk_api
import datetime
import os
import time
import re
from config.settings import VK_API_VERSION

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
            
            # Создаем VKDownloader
            vk = VKDownloader(self.token, self.group_identifier)
            
            # Создаем теггер
            tagger = EmployeeTagger()
            nlp = NLPProcessor()
            
            self.signals.progress.emit(f"📥 Загрузка постов из группы {self.group_identifier}...")
            
            # Получаем посты
            try:
                posts = vk.vk.wall.get(
                    owner_id=vk.group_id,
                    count=self.count,
                    v=VK_API_VERSION  # ← Без vk.!
                )['items']
            except vk_api.exceptions.ApiError as e:
                error_text = str(e).lower()
                if "[27]" in error_text or "group authorization failed" in error_text:
                    raise Exception(
                        "Токен сообщества не подходит для wall.get/video.get. "
                        "Для загрузки фото/видео укажите пользовательский токен "
                        "с правами wall, groups, photos, video."
                    )
                if "invalid access_token" in error_text:
                    raise Exception("Неверный или устаревший токен. Получите новый токен и повторите.")
                raise
            
            if not posts:
                self.signals.progress.emit("❌ Посты не найдены")
                return
            
            total = len(posts)
            processed = 0
            
            for post in posts:
                if not self.is_running:
                    break
                
                post_date = post['date']
                post_id = post['id']

                # Быстрый фильтр: если пост уже загружался, пропускаем.
                if vk.db.post_exists(post_id):
                    self.signals.progress.emit(f"⏭ Пропуск поста {post_id}: уже загружен")
                    continue
                
                # Обработка
                date = datetime.datetime.fromtimestamp(post_date).strftime('%Y-%m-%d %H:%M')
                text = post.get('text', '')
                
                # Поиск преподавателей + ключевых слов (старый NLP) + уже существующих #хэштегов
                all_tags = set(tagger.get_all_tags(text, include_keywords=True))
                nlp_tags = nlp.generate_tags(text)
                if nlp_tags:
                    all_tags.update(nlp_tags.split())
                all_tags.update(f"#{tag}" for tag in re.findall(r'#([A-Za-zА-Яа-яЁё0-9_]+)', text))
                found_tags = sorted(all_tags)
                
                attachments = post.get('attachments', [])
                
                # Определяем папку по дате
                folder_path = MediaProcessor.get_date_folder_path(post_date)
                os.makedirs(folder_path, exist_ok=True)
                
                for index, attach in enumerate(attachments, 1):
                    att_type = attach['type']
                    media_path = None
                    media_key = f"{att_type}_{index}"
                    
                    if att_type == 'photo':
                        photo = attach['photo']
                        photo_id = photo.get('id', index)
                        url = (
                            photo.get('sizes', [])[-1].get('url') or
                            photo.get('photo_2560') or
                            photo.get('photo_1280')
                        )
                        if url:
                            media_key = f"photo_{photo_id}"
                            temp_path = os.path.join(folder_path, f"post_{post_id}_photo_{photo_id}.jpg")
                            webp_path = os.path.join(folder_path, f"post_{post_id}_photo_{photo_id}.webp")
                            
                            if MediaProcessor.download_file(url, temp_path):
                                media_path = MediaProcessor.convert_to_webp(temp_path, webp_path) or temp_path
                                if os.path.exists(temp_path) and media_path != temp_path:
                                    os.remove(temp_path)
                                processed += 1
                    
                    elif att_type == 'video':
                        video = attach['video']
                        video_id = video.get('id', index)
                        owner_id = video.get('owner_id')
                        access_key = video.get('access_key')
                        media_key = f"video_{owner_id}_{video_id}"
                        media_path = os.path.join(folder_path, f"post_{post_id}_video_{video_id}.mp4")
                        downloaded_video_path = vk.download_video(
                            owner_id,
                            video_id,
                            post_id,
                            output_path=media_path,
                            fallback_video_data=video,
                            access_key=access_key
                        )

                        if downloaded_video_path:
                            media_path = downloaded_video_path
                            processed += 1
                    
                    if media_path and os.path.exists(media_path):
                        size = MediaProcessor.get_file_size(media_path)
                        
                        # Уникальный ID для записи в таблице
                        import hashlib
                        unique_id = int(hashlib.md5(f"{post_id}_{media_key}".encode()).hexdigest()[:8], 16)
                        
                        # Сохраняем в БД с устойчивым ключом вложения (без дублей при повторной загрузке)
                        vk.db.save_post(
                            post_id=unique_id,
                            original_post_id=post_id,
                            date=date,
                            text=text,
                            tags=" ".join(found_tags) if found_tags else "",
                            media_type=att_type,
                            media_key=media_key,
                            media_path=media_path,
                            file_size=size
                        )
                    
                    self.signals.progress.emit(f"📥 Обработано: {processed}/{total}")
            
            vk.db.close()
            self.signals.progress.emit(f"✅ Завершено! Сохранено: {processed} файлов")
            self.signals.finished.emit()
            
        except Exception as e:
            self.signals.error.emit(f"❌ Ошибка: {str(e)}")