from PySide6.QtCore import QThread, Signal, QObject
# Примечание: если у вас папка называется core, замените services на core
from services.vk_downloader import VKDownloader
from core.employee_tagger import EmployeeTagger
from core.nlp_processor import NLPProcessor
from core.media_processor import MediaProcessor
import vk_api
import datetime
import os
import re
import time
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
            
            if not self.token or not str(self.token).strip():
                self.signals.error.emit("❌ Ошибка: Токен VK API не указан!\n\nПолучите токен на https://vkhost.github.io/ и введите его в Настройки.")
                return
            
            try:
                vk = VKDownloader(self.token, self.group_identifier)
            except Exception as init_err:
                logger.error("VK Downloader initialization error: %s", init_err)
                self.signals.error.emit(f"❌ {str(init_err)}")
                return
            
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

                if vk.db.post_exists(post_id):
                    if vk.db.update_post_stats(post_id, likes, comments, shares):
                        self.signals.progress.emit(f"🔁 Обновлена статистика поста {post_id}")
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
                    likes=likes, comments=comments, shares=shares
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


class WallStatsRefreshSignals(QObject):
    """Сигналы воркера обновления счётчиков через wall.get (как при загрузке медиа)"""
    progress = Signal(str)
    finished = Signal(int, int)  # обновлено по данным стены; код -1 если в БД нет постов
    error = Signal(str)


class WallStatsRefreshWorker(QThread):
    """
    Обновляет лайки/комментарии/репосты для постов, уже лежащих в архиве,
    используя тот же API wall.get, что и DownloadWorker (пачки по 100, без wall.getById).
    Обновляются только посты, чей id есть в БД и который попадает в запрошенный срез стены.
    """

    def __init__(self, token, group_identifier, max_wall_posts=4000):
        super().__init__()
        self.token = token
        self.group_identifier = group_identifier
        self.max_wall_posts = max(100, int(max_wall_posts))
        self.signals = WallStatsRefreshSignals()
        self.is_running = True

    @staticmethod
    def _counters(post):
        lk = post.get("likes") or {}
        cm = post.get("comments") or {}
        rp = post.get("reposts") or {}
        likes = lk.get("count", 0) if isinstance(lk, dict) else int(lk or 0)
        comments = cm.get("count", 0) if isinstance(cm, dict) else int(cm or 0)
        shares = rp.get("count", 0) if isinstance(rp, dict) else int(rp or 0)
        return int(likes), int(comments), int(shares)

    def run(self):
        vk = None
        try:
            self.signals.progress.emit("🔄 Инициализация VK (wall.get)...")
            vk = VKDownloader(self.token, self.group_identifier)
            db = vk.db

            ids_in_db = {
                int(r[0])
                for r in db._get_cursor().execute("SELECT original_post_id FROM posts").fetchall()
                if r[0] is not None
            }
            if not ids_in_db:
                self.signals.progress.emit("⚠️ В базе нет постов")
                self.signals.finished.emit(-1, 0)
                return

            self.signals.progress.emit(
                f"📋 В архиве: {len(ids_in_db)} постов. Сканируем до {self.max_wall_posts} записей на стене..."
            )

            total_refreshed = 0
            offset = 0
            chunk = 100

            while offset < self.max_wall_posts and self.is_running:
                response = vk.vk.wall.get(
                    owner_id=vk.group_id,
                    count=chunk,
                    offset=offset,
                    v=VK_API_VERSION,
                    extended=1,
                )
                items = response.get("items", [])
                if not items:
                    break

                batch = []
                for post in items:
                    post_id = int(post["id"])
                    if post_id not in ids_in_db:
                        continue
                    likes, comments, shares = self._counters(post)
                    batch.append((post_id, likes, comments, shares))

                if batch:
                    if not db.update_post_stats_batch(batch):
                        raise RuntimeError("Не удалось записать пакет статистики в БД (см. лог)")
                    total_refreshed += len(batch)
                    self.signals.progress.emit(
                        f"⏩ Обновлено из стены: {total_refreshed} (смещение {offset}…{offset + len(items) - 1})"
                    )

                offset += len(items)
                time.sleep(0.34)

            self.signals.progress.emit(f"✅ Готово. Счётчики обновлены для {total_refreshed} постов архива.")
            self.signals.finished.emit(total_refreshed, 0)

        except vk_api.exceptions.ApiError as e:
            self.signals.error.emit(f"Ошибка VK API: {e}")
        except Exception as e:
            logger.error("WallStatsRefreshWorker: %s", e, exc_info=True)
            self.signals.error.emit(f"Ошибка: {e}")
        finally:
            if vk is not None:
                try:
                    vk.db.close()
                except Exception:
                    pass