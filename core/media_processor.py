import os
import sys
import requests
import yt_dlp
import ffmpeg
import datetime
from urllib.parse import urlparse, parse_qs
from PIL import Image
from config.settings import WEBP_QUALITY, VIDEO_CRF, VIDEO_PRESET, PHOTOS_DIR, VIDEOS_DIR

class MediaProcessor:
    """Класс для обработки медиафайлов (фото и видео)"""

    @staticmethod
    def _normalize_vk_video_url(input_url):
        """Преобразует video_ext.php в canonical URL, понятный yt-dlp."""
        try:
            parsed = urlparse(input_url)
            if "vk.com" not in parsed.netloc or "video_ext.php" not in parsed.path:
                return input_url

            params = parse_qs(parsed.query)
            oid = params.get("oid", [None])[0]
            vid = params.get("id", [None])[0]
            if not oid or not vid:
                return input_url

            canonical_url = f"https://vk.com/video{oid}_{vid}"
            hash_value = params.get("hash", [None])[0]
            if hash_value:
                canonical_url = f"{canonical_url}?access_key={hash_value}"
            return canonical_url
        except Exception:
            return input_url

    @staticmethod
    def _is_okcdn_direct_url(url):
        """Определяет прямую CDN-ссылку VK/OK, где yt-dlp часто падает с HTTP 400."""
        try:
            parsed = urlparse(url or "")
            host = (parsed.netloc or "").lower()
            return "okcdn.ru" in host and "expires=" in (parsed.query or "")
        except Exception:
            return False

    @staticmethod
    def _download_direct_video(url, temp_file_base):
        """
        Прямое скачивание видео по URL (для okcdn-ссылок).
        Возвращает путь к временному файлу или None.
        """
        temp_path = f"{temp_file_base}.mp4"
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Referer": "https://vk.com/",
            "Accept": "*/*",
        }
        try:
            with requests.get(url, stream=True, headers=headers, timeout=60) as r:
                r.raise_for_status()
                with open(temp_path, "wb") as f:
                    for chunk in r.iter_content(chunk_size=1024 * 256):
                        if chunk:
                            f.write(chunk)
            return temp_path if os.path.exists(temp_path) else None
        except Exception as e:
            print(f"[Direct Download ERROR] {e}")
            return None
    
    @staticmethod
    def get_date_folder_path(post_date_timestamp):
        """Создает путь Год/Месяц/День на основе даты поста"""
        if not post_date_timestamp:
            now = datetime.datetime.now()
            return f"vk_archive_data/{now.year}/{now.month:02d}/{now.day:02d}"

        post_date = datetime.datetime.fromtimestamp(post_date_timestamp)
        return f"vk_archive_data/{post_date.year}/{post_date.month:02d}/{post_date.day:02d}"
    
    @staticmethod
    def get_file_size(path):
        """Получение размера файла в мегабайтах"""
        if os.path.exists(path):
            size_mb = os.path.getsize(path) / (1024 * 1024)
            return f"{size_mb:.2f} MB"
        return "0 MB"

    @staticmethod
    def convert_to_webp(input_path, output_path, quality=WEBP_QUALITY):
        """Конвертация изображения в формат WebP"""
        try:
            if not os.path.exists(input_path):
                print(f"Файл не найден: {input_path}")
                return None
            
            with Image.open(input_path) as img:
                if img.mode in ("RGBA", "P"):
                    img = img.convert("RGB")
                img.save(output_path, "WEBP", quality=quality, method=6, exact=False)
            
            return output_path
            
        except Exception as e:
            print(f"Photo Conversion Error: {e}")
            return None

    @staticmethod
    def enhance_and_convert_video(input_url, output_path):
        """Скачивание и обработка видео с улучшением качества"""
        try:
            # Проверка на пустой URL
            if not input_url or input_url.strip() == '':
                print("[yt-dlp ERROR] Пустой URL видео!")
                return None
            
            # Правильное имя временного файла
            output_dir = os.path.dirname(output_path)
            output_name = os.path.splitext(os.path.basename(output_path))[0]
            temp_file = os.path.join(output_dir, f"{output_name}.temp")
            
            cookie_path = None
            for path in [
                "cookies.txt",
                "cookie.txt",
                "coockie.txt",
                os.path.join(os.path.dirname(sys.argv[0]), "cookies.txt"),
                os.path.join(os.path.dirname(sys.argv[0]), "cookie.txt"),
                os.path.join(os.path.dirname(sys.argv[0]), "coockie.txt"),
                os.path.join(os.getcwd(), "cookies.txt"),
                os.path.join(os.getcwd(), "cookie.txt"),
                os.path.join(os.getcwd(), "coockie.txt"),
            ]:
                if os.path.exists(path):
                    cookie_path = path
                    break

            normalized_url = MediaProcessor._normalize_vk_video_url(input_url)
            
            downloaded_file = None
            # Для прямых okcdn-ссылок сначала используем requests:
            # это стабильнее, чем generic extractor в yt-dlp.
            if MediaProcessor._is_okcdn_direct_url(normalized_url):
                print(f"[Direct] Скачивание прямой ссылки: {normalized_url[:80]}...")
                downloaded_file = MediaProcessor._download_direct_video(normalized_url, temp_file)

            if not downloaded_file:
                ydl_opts = {
                    'format': 'best',
                    'outtmpl': temp_file,
                    'quiet': False,
                    'no_warnings': False,
                    'nocheckcertificate': True,
                    'ignoreerrors': False,
                    'socket_timeout': 60,
                    'retries': 3,
                    'fragment_retries': 3,
                    'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                    'merge_output_format': 'mp4',
                    **({'cookiefile': cookie_path} if cookie_path else {}),
                }
                
                print(f"[yt-dlp] Загрузка: {normalized_url}")
                if cookie_path:
                    print(f"[yt-dlp] Cookies: {os.path.abspath(cookie_path)}")
                print(f"[yt-dlp] Temp file pattern: {temp_file}*")
                
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    info = ydl.extract_info(normalized_url, download=True)
                    if not info:
                        print(f"[yt-dlp] Не удалось получить информацию о видео")
                        return None
            
                for ext in ['.mp4', '.mkv', '.webm', '.flv', '.avi']:
                    candidate = temp_file + ext
                    if os.path.exists(candidate):
                        downloaded_file = candidate
                        print(f"[yt-dlp] Найдено: {candidate}")
                        break
            
            if not downloaded_file and os.path.exists(temp_file):
                downloaded_file = temp_file
                print(f"[yt-dlp] Найдено (без расширения): {temp_file}")
            
            if not downloaded_file:
                print(f"[yt-dlp] Файл не найден после скачивания")
                if output_dir and os.path.exists(output_dir):
                    files = [f for f in os.listdir(output_dir) if output_name in f]
                    if files:
                        print(f"[yt-dlp] Похожие файлы: {files}")
                return None

            print(f"[FFmpeg] Конвертация: {downloaded_file} -> {output_path}")
            
            try:
                input_stream = ffmpeg.input(downloaded_file)
                video = input_stream.video
                audio = input_stream.audio

                video = video\
                    .filter('unsharp', 5, 5, 1.0, 5, 5, 0.0)\
                    .filter('eq', contrast=1.1, saturation=1.1, brightness=0.05)
                
                output_stream = ffmpeg.output(
                    video, 
                    audio, 
                    output_path,
                    vcodec='libx264',
                    preset=VIDEO_PRESET,
                    crf=VIDEO_CRF,
                    acodec='aac',
                    audio_bitrate='128k',
                    movflags='faststart'
                )

                ffmpeg.run(
                    output_stream, 
                    capture_stdout=False, 
                    capture_stderr=False,  
                    quiet=False,
                    overwrite_output=True
                )
                
            except ffmpeg.Error as e:
                stderr = e.stderr.decode('utf8') if e.stderr else "Unknown error"
                print(f"[FFmpeg ERROR] {stderr}")
                import shutil
                shutil.copy2(downloaded_file, output_path)
                print(f"[FFmpeg] Использован исходный файл без конвертации")
            
            if os.path.exists(downloaded_file) and downloaded_file != output_path:
                os.remove(downloaded_file)
                print(f"[Cleanup] Удалён временный файл: {downloaded_file}")
                
            print(f"[OK] Видео сохранено: {output_path}")
            print(f"[OK] Размер: {MediaProcessor.get_file_size(output_path)}")
            return output_path
            
        except yt_dlp.utils.DownloadError as e:
            print(f"[yt-dlp ERROR] {e}")
            return None
        except Exception as e:
            print(f"[ERROR] {type(e).__name__}: {e}")
            import traceback
            traceback.print_exc()
            return None

    @staticmethod
    def download_file(url, path):
        """Скачивание файла по URL"""
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
    def get_video_duration(path):
        """Получение длительности видео в секундах"""
        try:
            probe = ffmpeg.probe(path)
            duration = float(probe['format']['duration'])
            return duration
        except Exception:
            return 0

    @staticmethod
    def get_image_dimensions(path):
        """Получение размеров изображения"""
        try:
            with Image.open(path) as img:
                return img.size
        except Exception:
            return (0, 0)