import os
import sys
import requests
import yt_dlp
import datetime
from urllib.parse import urlparse
from PIL import Image
from config.settings import PHOTOS_DIR, VIDEOS_DIR

class MediaProcessor:
    """Класс для простой загрузки медиафайлов (без конвертации)"""

    @staticmethod
    def get_date_folder_path(post_date_timestamp):
        if not post_date_timestamp:
            now = datetime.datetime.now()
            return f"vk_archive_data/{now.year}/{now.month:02d}/{now.day:02d}"
        post_date = datetime.datetime.fromtimestamp(post_date_timestamp)
        return f"vk_archive_data/{post_date.year}/{post_date.month:02d}/{post_date.day:02d}"

    @staticmethod
    def get_file_size(path):
        if os.path.exists(path):
            size_mb = os.path.getsize(path) / (1024 * 1024)
            return f"{size_mb:.2f} MB"
        return "0 MB"

    @staticmethod
    def download_file(url, path):
        """Простое скачивание файла по URL"""
        try:
            if os.path.exists(path):
                return True
            
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
            
            r = requests.get(url, stream=True, headers=headers, timeout=30)
            r.raise_for_status()
            
            with open(path, 'wb') as f:
                for chunk in r.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
            
            return True
            
        except Exception as e:
            print(f"Download Error: {e}")
            return False

    @staticmethod
    def download_thumbnail(thumb_url, output_path):
        """Скачивание превью видео из URL (предоставляется VK API)"""
        if not thumb_url or not isinstance(thumb_url, str) or not thumb_url.startswith('http'):
            print(f"[Thumb] Invalid URL: {thumb_url}")
            return None
        try:
            if os.path.exists(output_path):
                return output_path
            
            headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
            r = requests.get(thumb_url, headers=headers, timeout=15)
            r.raise_for_status()
            
            with open(output_path, 'wb') as f:
                f.write(r.content)
            print(f"[Thumb] Saved: {output_path}")
            return output_path
        except Exception as e:
            print(f"[Thumb] Error downloading {thumb_url[:80]}...: {e}")
            return None

    @staticmethod
    def download_video_raw(input_url, output_path):
        """
        Скачивание видео без конвертации.
        Пытается найти прямой MP4, иначе использует yt-dlp.
        """
        try:
            if not input_url or input_url.strip() == '':
                print("[Video ERROR] Пустой URL")
                return None

            # 1. Попытка прямого скачивания, если это ссылка на mp4
            if input_url.endswith('.mp4'):
                if MediaProcessor.download_file(input_url, output_path):
                    print(f"[Video OK] Direct download: {output_path}")
                    return output_path

            # 2. Использование yt-dlp для получения видео
            # Используем формат best[ext=mp4], чтобы избежать необходимости слияния потоков (что требует ffmpeg)
            ydl_opts = {
                'format': 'best[ext=mp4]/best', 
                'outtmpl': output_path,
                'quiet': True,
                'no_warnings': True,
                'nocheckcertificate': True,
                'ignoreerrors': False,
                'socket_timeout': 60,
                'retries': 3,
                'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            }
             
            print(f"[yt-dlp] Downloading video to: {output_path}")
            
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(input_url, download=True)
                if not info:
                    print(f"[yt-dlp] Failed to get info")
                    return None
            
            # Проверка, создался ли файл (yt-dlp может добавить расширение)
            if os.path.exists(output_path):
                return output_path
            
            # Ищем файл с добавленным расширением
            base_name = os.path.splitext(output_path)[0]
            for ext in ['.mp4', '.mkv', '.webm']:
                candidate = base_name + ext
                if os.path.exists(candidate):
                    # Переименовываем в нужный формат, если возможно
                    if ext != '.mp4':
                        print(f"[Warning] Video is {ext}, keeping original extension.")
                    return candidate
                    
            print(f"[Video ERROR] File not found after download")
            return None
            
        except Exception as e:
            print(f"[Video ERROR] {type(e).__name__}: {e}")
            import traceback
            traceback.print_exc()
            return None

    @staticmethod
    def get_image_dimensions(path):
        try:
            with Image.open(path) as img:
                return img.size
        except Exception:
            return (0, 0)