import subprocess
import shutil

# Проверка 1: Доступен ли ffmpeg в системе
ffmpeg_path = shutil.which("ffmpeg")
print(f"FFmpeg путь: {ffmpeg_path}")

if ffmpeg_path:
    # Проверка 2: Запуск ffmpeg
    result = subprocess.run(['ffmpeg', '-version'], capture_output=True, text=True)
    if result.returncode == 0:
        print("✅ FFmpeg работает корректно!")
        print(result.stdout.split('\n')[0])
    else:
        print("❌ FFmpeg не запускается")
else:
    print("❌ FFmpeg не найден в PATH!")
    print("\nРешение:")
    print("1. Скачайте FFmpeg с https://www.gyan.dev/ffmpeg/builds/")
    print("2. Распакуйте в C:\\ffmpeg")
    print("3. Добавьте C:\\ffmpeg\\bin в переменную PATH")
    print("4. Перезапустите терминал/VS Code")