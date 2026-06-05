@echo off
setlocal EnableExtensions
cd /d "%~dp0"

if exist ".venv\Scripts\python.exe" (
  set "PY=.venv\Scripts\python.exe"
  set "PIP=.venv\Scripts\pip.exe"
) else (
  set "PY=python"
  set "PIP=pip"
)

echo === VK Archiver CHIBGU: сборка exe ===
echo.

echo [1/3] Зависимости...
"%PIP%" install -r requirements.txt pyinstaller --quiet
if errorlevel 1 (
  echo Ошибка установки зависимостей.
  exit /b 1
)

echo [2/3] PyInstaller...
"%PY%" -m PyInstaller build.spec --noconfirm --clean
if errorlevel 1 (
  echo Сборка не удалась.
  exit /b 1
)

echo [3/3] Готово.
echo.
echo   dist\VK_Archiver_CHIBGU\VK_Archiver_CHIBGU.exe
echo.
echo Для демо преподавателю положите РЯДОМ с exe:
echo   Archive.db
echo   Exports_data\
echo   .env  ^(необязательно, для просмотра архива токен не нужен^)
echo.
echo Или распакуйте ZIP из Настройки -^> Резервная копия в эту же папку.
echo.
exit /b 0
