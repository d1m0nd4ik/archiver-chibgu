from PySide6.QtCore import QThread, Signal, QObject
import vk_api
import time
from core.database import Database
from core.logging_config import logger
from core.url_parser import VKUrlParser
from config.settings import VK_API_VERSION

class UpdateStatsWorkerSignals(QObject):
    """Сигналы для воркера обновления статистики"""
    progress = Signal(str)
    finished = Signal()
    error = Signal(str)

class UpdateStatsWorker(QThread):
    """Воркер для обновления статистики постов из VK API"""
    
    def __init__(self, token, group_identifier):
        super().__init__()
        self.token = token
        self.group_identifier = group_identifier
        self.signals = UpdateStatsWorkerSignals()

    def run(self):
        try:
            self.signals.progress.emit("🔄 Инициализация VK API...")
            
            vk_session = vk_api.VkApi(token=self.token)
            vk = vk_session.get_api()
            db = Database()
            
            # 1. Определяем ID группы
            group_id = VKUrlParser.extract_id_from_url(self.group_identifier, vk_session)
            if not group_id:
                try:
                    group_id = -abs(int(self.group_identifier))
                except ValueError:
                    raise Exception("Не удалось определить ID группы из ссылки")
            
            # 2. Получаем список постов из БД
            self.signals.progress.emit("📋 Чтение списка постов из базы...")
            all_posts = db.get_all_posts(limit=2000)
            
            if not all_posts:
                self.signals.progress.emit("⚠️ В базе нет постов для обновления")
                return
            
            total_posts = len(all_posts)
            updated_count = 0
            error_count = 0
            
            self.signals.progress.emit(f"🔄 Найдено {total_posts} постов. Начинаем обновление...")
            
            # 3. Проходим по каждому посту и обновляем статистику
            for idx, post_data in enumerate(all_posts, 1):
                original_post_id = post_data[0]
                
                try:
                    vk_post_id = f"{group_id}_{original_post_id}"
                    
                    # Запрашиваем актуальные данные поста
                    response = vk.wall.getById(posts=vk_post_id, v=VK_API_VERSION)
                    
                    if response and len(response) > 0:
                        post = response[0]
                        
                        likes = post.get('likes', {}).get('count', 0)
                        comments = post.get('comments', {}).get('count', 0)
                        shares = post.get('reposts', {}).get('count', 0)
                        
                        # Обновляем в БД (views=0 передаётся только для сохранения сигнатуры метода)
                        if db.update_post_stats(original_post_id, likes, comments, shares, 0):
                            updated_count += 1
                        else:
                            error_count += 1
                    else:
                        error_count += 1
                        logger.warning(f"Пост {original_post_id} не найден в VK")
                    
                    if idx % 10 == 0:
                        self.signals.progress.emit(f"⏩ Обновлено {idx}/{total_posts} постов...")
                    
                    time.sleep(0.34)  # Соблюдение лимитов VK API
                    
                except vk_api.exceptions.ApiError as e:
                    error_count += 1
                    logger.error(f"VK API Error для поста {original_post_id}: {e}")
                    if "invalid access_token" in str(e).lower():
                        raise Exception("Токен устарел или неверен!")
                except Exception as e:
                    error_count += 1
                    logger.error(f"Ошибка обработки поста {original_post_id}: {e}")

            db.close()
            
            self.signals.progress.emit(f"✅ Готово! Обновлено: {updated_count}, Ошибок: {error_count}")
            self.signals.finished.emit()
            
        except Exception as e:
            self.signals.error.emit(f"❌ Критическая ошибка: {str(e)}")