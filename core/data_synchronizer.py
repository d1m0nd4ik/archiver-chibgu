"""
Модуль для синхронизации базы данных с файловой системой и обновления статистики
"""

import os
import json
from datetime import datetime, timedelta
from typing import Dict, List, Tuple
import threading
import time
from core.logging_config import logger
from core.database import Database
from core.period_calculator import PeriodCalculator
from config.settings import PHOTOS_DIR, VIDEOS_DIR, DATA_DIR


class DataSynchronizer:
    """Класс для синхронизации данных и обновления статистики"""
    
    def __init__(self):
        self.db = Database()
        self.period_calc = PeriodCalculator()
        self.sync_thread = None
        self.is_running = False
        self.stop_event = threading.Event()
    
    # ===== СИНХРОНИЗАЦИЯ ФАЙЛОВ И БД =====
    
    def get_files_in_directory(self, directory: str, extension: str = None) -> List[str]:
        """Получает список файлов в директории"""
        if not os.path.exists(directory):
            return []
        
        files = []
        try:
            for filename in os.listdir(directory):
                filepath = os.path.join(directory, filename)
                if os.path.isfile(filepath):
                    if extension is None or filename.endswith(extension):
                        files.append(filename)
        except Exception as e:
            logger.error(f"Error reading directory {directory}: {e}")
        
        return files
    
    def verify_photo_consistency(self) -> Dict:
        files_in_folder = set(self.get_files_in_directory(PHOTOS_DIR, '.webp'))
        missing_in_folder = []
        missing_in_db = []
        
        # Запрашиваем пути напрямую из таблицы attachments
        cursor = self.db._get_cursor()
        db_files = set()
        for row in cursor.execute("SELECT media_path FROM attachments WHERE media_type='photo'").fetchall():
            if row[0]:
                filename = os.path.basename(row[0])
                db_files.add(filename)
                if filename not in files_in_folder:
                    missing_in_folder.append(row[0])
        
        for file in files_in_folder:
            if file not in db_files:
                missing_in_db.append(file)
                
        return {
            'missing_in_folder': missing_in_folder,
            'missing_in_db': missing_in_db,
            'consistency_ok': len(missing_in_folder) == 0 and len(missing_in_db) == 0
        }

    def verify_video_consistency(self) -> Dict:
        files_in_folder = set(self.get_files_in_directory(VIDEOS_DIR, '.mp4'))
        missing_in_folder = []
        missing_in_db = []
        
        cursor = self.db._get_cursor()
        db_files = set()
        for row in cursor.execute("SELECT media_path FROM attachments WHERE media_type IN ('video', 'clip')").fetchall():
            if row[0]:
                filename = os.path.basename(row[0])
                db_files.add(filename)
                if filename not in files_in_folder:
                    missing_in_folder.append(row[0])
                    
        for file in files_in_folder:
            if file not in db_files:
                missing_in_db.append(file)
                
        return {
            'missing_in_folder': missing_in_folder,
            'missing_in_db': missing_in_db,
            'consistency_ok': len(missing_in_folder) == 0 and len(missing_in_db) == 0
        }
    
    def verify_all_consistency(self) -> Dict:
        """Комплексная проверка консистентности всех данных"""
        photo_check = self.verify_photo_consistency()
        video_check = self.verify_video_consistency()
        
        return {
            'photos': photo_check,
            'videos': video_check,
            'overall_ok': photo_check['consistency_ok'] and video_check['consistency_ok']
        }
    
    # ===== ОБНОВЛЕНИЕ СТАТИСТИКИ =====
    
    def update_post_statistics(self, original_post_id: int, vk_api=None) -> bool:
        """
        Обновляет статистику поста из VK API
        
        Args:
            original_post_id: ID поста в ВКонтакте
            vk_api: объект VK API (если None, статистика не обновляется)
        
        Returns:
            True если успешно, False если ошибка
        """
        if vk_api is None:
            return False
        
        try:
            # Запрашиваем информацию о посте
            post_info = vk_api.wall.getById(posts=str(original_post_id))
            
            if post_info and len(post_info) > 0:
                post = post_info[0]
                likes = post.get('likes', {}).get('count', 0)
                comments = post.get('comments', {}).get('count', 0)
                reposts = post.get('reposts', {}).get('count', 0)

                return self.db.update_post_stats(original_post_id, likes, comments, reposts)
        
        except Exception as e:
            logger.error(f"Error updating post {original_post_id} statistics: {e}")
        
        return False
    
    def batch_update_statistics(self, post_ids: List[int], vk_api=None, 
                               update_interval: int = 0.33) -> Tuple[int, int]:
        """
        Пакетное обновление статистики для списка постов
        
        Args:
            post_ids: список ID постов
            vk_api: объект VK API
            update_interval: интервал между запросами (секунды, для соблюдения лимитов API)
        
        Returns:
            Кортеж (успешно_обновлено, ошибок)
        """
        if vk_api is None:
            return 0, len(post_ids)
        
        success_count = 0
        error_count = 0
        
        for post_id in post_ids:
            if self.update_post_statistics(post_id, vk_api):
                success_count += 1
            else:
                error_count += 1
            
            # Соблюдаем лимит API
            time.sleep(update_interval)
        
        return success_count, error_count
    
    def calculate_period_statistics(self, period_type: str, start_date: datetime = None,
                                   end_date: datetime = None) -> Dict:
        """
        Рассчитывает статистику за период
        
        Args:
            period_type: тип периода
            start_date: дата начала
            end_date: дата конца
        
        Returns:
            Словарь с рассчитанной статистикой
        """
        if start_date is None or end_date is None:
            start_date, end_date = self.period_calc.get_period_range(period_type)
        
        start_str = self.period_calc.format_date(start_date)
        end_str = self.period_calc.format_date(end_date)
        
        posts = self.db.get_posts_by_date_range(start_str, end_str)
        
        stats = {
            'period_type': period_type,
            'start_date': start_str,
            'end_date': end_str,
            'total_posts': len(posts),
            'total_likes': 0,
            'total_comments': 0,
            'total_shares': 0,
            'avg_likes': 0,
        }
        
        stats_db = self.db.get_aggregated_stats(start_str, end_str)
        stats['total_likes'] = stats_db['total_likes']
        stats['total_comments'] = stats_db['total_comments']
        stats['total_shares'] = stats_db['total_shares']
        stats['total_posts'] = stats_db['total_posts']

        if stats['total_posts'] > 0:
            stats['avg_likes'] = stats['total_likes'] / stats['total_posts']
        
        return stats
    
    # ===== АВТОМАТИЧЕСКАЯ СИНХРОНИЗАЦИЯ =====
    
    def start_automatic_sync(self, vk_api=None, sync_interval_hours: int = 24,
                            update_stats: bool = True) -> None:
        """
        Запускает автоматическую синхронизацию в фоновом потоке
        
        Args:
            vk_api: объект VK API для обновления статистики
            sync_interval_hours: интервал синхронизации (часы)
            update_stats: обновлять ли статистику постов
        """
        self.stop_event.clear()  # Сброс флага
        if self.is_running:
            logger.info("[Sync] Автоматическая синхронизация уже запущена")
            return
        
        self.is_running = True
        self.vk_api = vk_api
        self.sync_interval = sync_interval_hours * 3600  # В секунды
        
        self.sync_thread = threading.Thread(
            target=self._sync_worker,
            args=(update_stats,),
            daemon=True
        )
        self.sync_thread.start()
        logger.info(f"[Sync] Автоматическая синхронизация запущена (интервал: {sync_interval_hours}ч)")
    
    def stop_automatic_sync(self) -> None:
        """Останавливает автоматическую синхронизацию"""
        self.is_running = False
        self.stop_event.set()  # ← Добавить
        if self.sync_thread and self.sync_thread.is_alive():
            self.sync_thread.join(timeout=5)
        logger.info("[Sync] Автоматическая синхронизация остановлена")
    
    def _sync_worker(self, update_stats: bool) -> None:
        """Рабочий поток для автоматической синхронизации"""
        while self.is_running:
            try:
                logger.info(f"\n[Sync] Начало синхронизации: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
                
                # Проверка консистентности файлов
                consistency_check = self.verify_all_consistency()
                if not consistency_check['overall_ok']:
                    logger.warning(f"[Sync] ⚠ Обнаружены проблемы консистентности:")
                    if consistency_check['photos']['missing_in_db']:
                        logger.warning(f"  - Фото, которые есть в папке, но нет в БД: {len(consistency_check['photos']['missing_in_db'])}")
                    if consistency_check['videos']['missing_in_db']:
                        logger.warning(f"  - Видео, которые есть в папке, но нет в БД: {len(consistency_check['videos']['missing_in_db'])}")
                
                # Обновление статистики постов
                if update_stats and self.vk_api:
                    all_posts = self.db.get_posts_by_date_range('2000-01-01',
                                                                (datetime.now() + timedelta(days=1)).strftime('%Y-%m-%d'))
                    post_ids = [post[0] for post in all_posts]
                    success, errors = self.batch_update_statistics(post_ids, self.vk_api)
                    logger.info(f"[Sync] Статистика обновлена: {success} успешно, {errors} ошибок")
                
                # Рассчитываем статистику за последние периоды
                for period_type in ['day', 'week', 'month', 'year']:
                    period_stats = self.calculate_period_statistics(period_type)
                    logger.info(f"[Sync] {period_type.upper()}: {period_stats['total_posts']} постов")
                
                logger.info(f"[Sync] Синхронизация завершена: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
                
                # Ждем перед следующей синхронизацией
                if self.stop_event.wait(timeout=self.sync_interval):
                    break  # Флаг установлен → выходим из цикла
            
            except Exception as e:
                logger.error(f"[Sync] ⚠ Ошибка синхронизации: {e}")
                time.sleep(60)  # Пробуем снова через минуту
    
    # ===== УТИЛИТЫ =====
    
    def export_statistics_to_json(self, filename: str = 'statistics.json') -> bool:
        try:
            overall_stats = {
                'overall': self.db.get_stats(),
                'periods': {}
            }
            
            for period_type in ['day', 'week', 'month', 'year']:
                overall_stats['periods'][period_type] = self.calculate_period_statistics(period_type)
            
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(overall_stats, f, ensure_ascii=False, indent=2)
                
            logger.info("Статистика экспортирована в %s", filename)
            return True
        except Exception as e:
            logger.error("Ошибка экспорта статистики: %s", e, exc_info=True)
            return False
