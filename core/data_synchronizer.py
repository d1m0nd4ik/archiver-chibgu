"""
Модуль для синхронизации базы данных с файловой системой и обновления статистики
"""

import os
import json
from datetime import datetime, timedelta
from typing import Dict, List, Tuple
import threading
import time

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
            print(f"Error reading directory {directory}: {e}")
        
        return files
    
    def verify_photo_consistency(self) -> Dict:
        """Проверяет консистентность фото в БД и папке"""
        files_in_folder = set(self.get_files_in_directory(PHOTOS_DIR, '.webp'))
        
        missing_in_folder = []
        missing_in_db = []
        
        # Получаем все фото из БД
        db_photos = self.db.get_posts_by_date_range('2000-01-01', 
                                                    (datetime.now() + timedelta(days=1)).strftime('%Y-%m-%d'),
                                                    'photo')
        
        db_files = set()
        for post in db_photos:
            media_paths = post[4]  # media_paths - это GROUP_CONCAT
            if media_paths:
                for path in media_paths.split(','):
                    filename = os.path.basename(path)
                    db_files.add(filename)
                    if filename not in files_in_folder:
                        missing_in_folder.append(path)
        
        # Ищем файлы, которые есть в папке, но нет в БД
        for file in files_in_folder:
            if file not in db_files:
                missing_in_db.append(file)
        
        return {
            'missing_in_folder': missing_in_folder,
            'missing_in_db': missing_in_db,
            'consistency_ok': len(missing_in_folder) == 0 and len(missing_in_db) == 0
        }
    
    def verify_video_consistency(self) -> Dict:
        """Проверяет консистентность видео в БД и папке"""
        files_in_folder = set(self.get_files_in_directory(VIDEOS_DIR, '.mp4'))
        
        missing_in_folder = []
        missing_in_db = []
        
        # Получаем все видео из БД
        db_videos = self.db.get_posts_by_date_range('2000-01-01',
                                                   (datetime.now() + timedelta(days=1)).strftime('%Y-%m-%d'),
                                                   'video')
        
        db_files = set()
        for post in db_videos:
            media_paths = post[4]
            if media_paths:
                for path in media_paths.split(','):
                    filename = os.path.basename(path)
                    db_files.add(filename)
                    if filename not in files_in_folder:
                        missing_in_folder.append(path)
        
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
                views = post.get('views', {}).get('count', 0)
                
                # Сохраняем в БД
                return self.db.update_post_stats(original_post_id, likes, comments, reposts, views)
        
        except Exception as e:
            print(f"Error updating post {original_post_id} statistics: {e}")
        
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
            'total_views': 0,
            'avg_likes': 0,
            'avg_views': 0
        }
        
        for post in posts:
            post_stats = self.db.get_post_stats(post[0])
            if post_stats:
                stats['total_likes'] += post_stats['likes']
                stats['total_comments'] += post_stats['comments']
                stats['total_shares'] += post_stats['shares']
                stats['total_views'] += post_stats['views']
        
        if len(posts) > 0:
            stats['avg_likes'] = stats['total_likes'] / len(posts)
            stats['avg_views'] = stats['total_views'] / len(posts)
        
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
        if self.is_running:
            print("[Sync] Автоматическая синхронизация уже запущена")
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
        print(f"[Sync] Автоматическая синхронизация запущена (интервал: {sync_interval_hours}ч)")
    
    def stop_automatic_sync(self) -> None:
        """Останавливает автоматическую синхронизацию"""
        self.is_running = False
        if self.sync_thread and self.sync_thread.is_alive():
            self.sync_thread.join(timeout=5)
        print("[Sync] Автоматическая синхронизация остановлена")
    
    def _sync_worker(self, update_stats: bool) -> None:
        """Рабочий поток для автоматической синхронизации"""
        while self.is_running:
            try:
                print(f"\n[Sync] Начало синхронизации: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
                
                # Проверка консистентности файлов
                consistency_check = self.verify_all_consistency()
                if not consistency_check['overall_ok']:
                    print(f"[Sync] ⚠ Обнаружены проблемы консистентности:")
                    if consistency_check['photos']['missing_in_db']:
                        print(f"  - Фото, которые есть в папке, но нет в БД: {len(consistency_check['photos']['missing_in_db'])}")
                    if consistency_check['videos']['missing_in_db']:
                        print(f"  - Видео, которые есть в папке, но нет в БД: {len(consistency_check['videos']['missing_in_db'])}")
                
                # Обновление статистики постов
                if update_stats and self.vk_api:
                    all_posts = self.db.get_posts_by_date_range('2000-01-01',
                                                                (datetime.now() + timedelta(days=1)).strftime('%Y-%m-%d'))
                    post_ids = [post[0] for post in all_posts]
                    success, errors = self.batch_update_statistics(post_ids, self.vk_api)
                    print(f"[Sync] Статистика обновлена: {success} успешно, {errors} ошибок")
                
                # Рассчитываем статистику за последние периоды
                for period_type in ['day', 'week', 'month', 'year']:
                    period_stats = self.calculate_period_statistics(period_type)
                    print(f"[Sync] {period_type.upper()}: {period_stats['total_posts']} постов, "
                          f"{period_stats['total_views']} просмотров")
                
                print(f"[Sync] Синхронизация завершена: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
                
                # Ждем перед следующей синхронизацией
                time.sleep(self.sync_interval)
            
            except Exception as e:
                print(f"[Sync] ⚠ Ошибка синхронизации: {e}")
                time.sleep(60)  # Пробуем снова через минуту
    
    # ===== УТИЛИТЫ =====
    
    def export_statistics_to_json(self, filename: str = 'statistics.json') -> bool:
        """Экспортирует статистику в JSON"""
        try:
            overall_stats = {
                'overall': self.db.get_stats(),
                'periods': {}
            }
            
            for period_type in ['day', 'week', 'month', 'year']:
                overall_stats['periods'][period_type] = self.calculate_period_statistics(period_type)
            
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(overall_stats, f, ensure_ascii=False, indent=2)
            
            print(f"[Export] Статистика экспортирована в {filename}")
            return True
        except Exception as e:
            print(f"[Export] Ошибка экспорта: {e}")
            return False
