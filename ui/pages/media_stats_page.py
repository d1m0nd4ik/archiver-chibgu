import datetime
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QFrame, QLabel, QGridLayout, QComboBox, 
    QDateEdit, QPushButton, QTextEdit, QProgressBar, QMessageBox
)
from PySide6.QtCore import Qt, QThread, Signal
from ui.styles import STYLES
from core.logging_config import logger

class MediaStatsWorker(QThread):
    """Воркер для сбора статистики медиа"""
    progress = Signal(str)
    finished = Signal()
    error = Signal(str)
    
    def __init__(self, token, group_id, media_type='all'):
        super().__init__()
        self.token = token
        self.group_id = group_id
        self.media_type = media_type
        
    def run(self):
        try:
            import vk_api
            from core.database import Database
            
            self.progress.emit("🔄 Инициализация VK API...")
            vk_session = vk_api.VkApi(token=self.token)
            vk = vk_session.get_api()
            db = Database()
            
            self.progress.emit("📊 Загрузка списка медиа из базы...")
            cursor = db._get_cursor()
            
            if self.media_type == 'all':
                query = "SELECT media_key, media_type, media_path FROM attachments"
                params = ()
            else:
                query = "SELECT media_key, media_type, media_path FROM attachments WHERE media_type = ?"
                params = (self.media_type,)
            
            media_list = cursor.execute(query, params).fetchall()
            total = len(media_list)
            
            if total == 0:
                self.progress.emit("⚠️ Медиа не найдено")
                return
            
            updated = 0
            errors = 0
            
            self.progress.emit(f"🔍 Найдено {total} медиафайлов. Начинаем сбор статистики...")
            
            for idx, (media_key, media_type, media_path) in enumerate(media_list, 1):
                try:
                    # ПАРСИМ MEDIA_KEY
                    # Формат: photo_457239050 или photo_-236813059_457239050
                    parts = media_key.split('_')
                    
                    if media_type == 'photo':
                        # Для фото
                        if len(parts) >= 3 and parts[1].lstrip('-').isdigit():
                            # Формат: photo_OWNER_ID_PHOTO_ID
                            owner_id = parts[1]
                            photo_id = parts[2]
                        elif len(parts) >= 2:
                            # Формат: photo_PHOTO_ID (нет owner_id)
                            # ИСПОЛЬЗУЕМ ID ГРУППЫ КАК ВЛАДЕЛЬЦА (ОТРИЦАТЕЛЬНЫЙ)
                            owner_id = str(self.group_id)
                            photo_id = parts[1]
                        else:
                            errors += 1
                            continue
                        
                        # ВАЖНО: Для группы owner_id должен быть отрицательным!
                        # VK API требует формат: "owner_id_photo_id"
                        photo_param = f"{owner_id}_{photo_id}"
                        
                        response = vk.photos.getById(
                            photos=photo_param,
                            v='5.199'
                        )
                        
                        if response and len(response) > 0:
                            photo = response[0]
                            likes = photo.get('likes', {}).get('count', 0)
                            comments = photo.get('comments', {}).get('count', 0)
                            
                            db.save_media_statistics(
                                post_id=0,
                                media_key=media_key,
                                media_type=media_type,
                                date=datetime.datetime.now().strftime('%Y-%m-%d'),
                                likes=likes,
                                comments=comments,
                                shares=0,
                            )
                            updated += 1
                        else:
                            errors += 1
                    
                    elif media_type in ('video', 'clip'):
                        # Для видео: video_OWNER_ID_VIDEO_ID
                        if len(parts) >= 3:
                            owner_id = parts[1]
                            video_id = parts[2]
                            
                            video_param = f"{owner_id}_{video_id}"
                            
                            try:
                                response = vk.video.getById(
                                    videos=video_param,
                                    v='5.199'
                                )
                                
                                if response and len(response) > 0:
                                    video = response[0]
                                    likes = video.get('likes', {}).get('count', 0)
                                    comments = video.get('comments', {}).get('count', 0)

                                    db.save_media_statistics(
                                        post_id=0,
                                        media_key=media_key,
                                        media_type=media_type,
                                        date=datetime.datetime.now().strftime('%Y-%m-%d'),
                                        likes=likes,
                                        comments=comments,
                                        shares=0,
                                    )
                                    updated += 1
                                else:
                                    errors += 1
                            except vk_api.exceptions.ApiError as e:
                                # Логируем детально, чтобы понять причину ошибки видео
                                logger.error(f"Video API Error for key '{video_param}': {e}")
                                errors += 1
                        else:
                            errors += 1
                    
                    if idx % 10 == 0:
                        self.progress.emit(f"⏩ Обработано {idx}/{total}...")
                        
                except Exception as e:
                    logger.error(f"Error processing {media_key}: {e}")
                    errors += 1
            
            db.close()
            self.progress.emit(f"✅ Готово! Обновлено: {updated}, Ошибок: {errors}")
            self.finished.emit()
            
        except Exception as e:
            self.error.emit(f"Ошибка: {str(e)}")

class MediaStatsPage(QWidget):
    """Страница статистики медиафайлов"""
    def __init__(self, styles=None):
        super().__init__()
        self.styles = styles or STYLES.get_styles()
        self.worker = None
        self.init_ui()
        
    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(30, 30, 30, 30)
        layout.setSpacing(20)

        header = QLabel("📊 Статистика медиафайлов")
        text_color = '#000000' if STYLES._theme == 'light' else '#ffffff'
        header.setStyleSheet(f"color: {text_color}; font-size: 22px; font-weight: bold; padding: 10px 0;")
        self.header_label = header
        layout.addWidget(header)

        # Панель управления
        controls_frame = QFrame()
        controls_frame.setStyleSheet(self.styles['frame'])
        controls_layout = QGridLayout(controls_frame)
        controls_layout.setSpacing(16)

        controls_layout.addWidget(QLabel("Тип медиа: "), 0, 0)
        self.media_type_combo = QComboBox()
        self.media_type_combo.addItems(["Все", "Фото", "Видео", "Клипы"])
        self.media_type_combo.setStyleSheet(self.styles['input'])
        controls_layout.addWidget(self.media_type_combo, 0, 1)

        controls_layout.addWidget(QLabel("Сортировка: "), 0, 2)
        self.sort_combo = QComboBox()
        self.sort_combo.addItems(["По лайкам", "По комментариям", "По дате"])
        self.sort_combo.setStyleSheet(self.styles['input'])
        controls_layout.addWidget(self.sort_combo, 0, 3)

        self.collect_stats_btn = QPushButton("🔄 Собрать статистику из VK")
        self.collect_stats_btn.setStyleSheet(self.styles['button'])
        self.collect_stats_btn.setMinimumHeight(45)
        self.collect_stats_btn.clicked.connect(self.start_stats_collection)
        controls_layout.addWidget(self.collect_stats_btn, 1, 0, 1, 4)

        layout.addWidget(controls_frame)

        # Прогресс бар
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        self.progress_bar.setStyleSheet(self.styles['progressbar'])
        layout.addWidget(self.progress_bar)

        # Статистика
        self.stats_label = QLabel()
        self.stats_label.setStyleSheet(f"color: {text_color}; font-size: 14px; padding: 10px;")
        layout.addWidget(self.stats_label)

        # Результаты
        self.results_text = QTextEdit()
        self.results_text.setReadOnly(True)
        self.results_text.setStyleSheet(self.styles['textedit'])
        self.results_text.setMinimumHeight(300)
        layout.addWidget(self.results_text)

        layout.addStretch()

    def start_stats_collection(self):
        """Запускает сбор статистики"""
        from core.config_manager import load_env_settings
        from core.url_parser import VKUrlParser
        import vk_api
        
        settings = load_env_settings()
        token = settings.get('token', '')
        group_link = settings.get('group_link', '')
        
        if not token:
            QMessageBox.warning(self, "Ошибка", "Не найден токен VK!")
            return
        
        if not group_link:
            QMessageBox.warning(self, "Ошибка", "Не найдена ссылка на группу!")
            return
        
        media_type_map = {
            "Все": "all",
            "Фото": "photo",
            "Видео": "video",
            "Клипы": "clip"
        }
        media_type = media_type_map[self.media_type_combo.currentText()]
        
        try:
            vk_session = vk_api.VkApi(token=token)
            group_id = VKUrlParser.extract_id_from_url(group_link, vk_session)
            if not group_id:
                group_id = -abs(int(group_link))
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", f"Не удалось определить ID группы: {e}")
            return
        
        self.collect_stats_btn.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, 0)
        
        self.worker = MediaStatsWorker(token, group_id, media_type)
        self.worker.progress.connect(self.on_progress)
        self.worker.finished.connect(self.on_finished)
        self.worker.error.connect(self.on_error)
        self.worker.start()
        
    def on_progress(self, message):
        self.stats_label.setText(message)
        
    def on_finished(self):
        self.collect_stats_btn.setEnabled(True)
        self.progress_bar.setVisible(False)
        self.refresh_stats()
        QMessageBox.information(self, "Готово", "Статистика медиа собрана!")
        
    def on_error(self, error_msg):
        self.collect_stats_btn.setEnabled(True)
        self.progress_bar.setVisible(False)
        QMessageBox.critical(self, "Ошибка", error_msg)
        
    def refresh_stats(self):
        """Обновляет отображение статистики"""
        try:
            from core.database import Database
            db = Database()
            cursor = db._get_cursor()
            
            media_type_map = {
                "Все": "all",
                "Фото": "photo",
                "Видео": "video",
                "Клипы": "clip"
            }
            selected_type = media_type_map[self.media_type_combo.currentText()]
            
            sort_map = {
                "По лайкам": "likes",
                "По комментариям": "comments",
                "По дате": "date"
            }
            sort_by = sort_map[self.sort_combo.currentText()]
            
            if selected_type == "all":
                query = f"""
                    SELECT media_key, media_type, likes, comments, date
                    FROM media_statistics
                    ORDER BY {sort_by} DESC
                    LIMIT 50
                """
                results = cursor.execute(query).fetchall()
            else:
                query = f"""
                    SELECT media_key, media_type, likes, comments, date
                    FROM media_statistics
                    WHERE media_type = ?
                    ORDER BY {sort_by} DESC
                    LIMIT 50
                """
                results = cursor.execute(query, (selected_type,)).fetchall()
            
            db.close()
            
            output = []
            output.append(f"📊 Статистика медиафайлов\n")
            output.append(f"Всего записей: {len(results)}\n")
            output.append("=" * 70 + "\n\n")
            
            total_likes = 0
            total_comments = 0

            for idx, (media_key, media_type, likes, comments, date) in enumerate(results, 1):
                type_emoji = {"photo": "📷", "video": "🎬", "clip": "🎥"}.get(media_type, "📎")
                
                output.append(f"{idx}. {type_emoji} {media_key}\n")
                output.append(f"   Тип: {media_type}\n")
                output.append(f"   ❤️ Лайки: {likes}\n")
                output.append(f"   💬 Комментарии: {comments}\n")
                output.append(f"   📅 Дата: {date}\n")
                output.append("\n")
                
                total_likes += likes or 0
                total_comments += comments or 0

            output.append("=" * 70 + "\n")
            output.append(f"📈 Итого:\n")
            output.append(f"   Всего лайков: {total_likes}\n")
            output.append(f"   Всего комментариев: {total_comments}\n")
            
            self.results_text.setPlainText("".join(output))
            
        except Exception as e:
            logger.error(f"Error refreshing stats: {e}")
            self.results_text.setPlainText(f"Ошибка: {e}")

    def update_styles(self, styles):
        self.styles = styles
        text_color = '#000000' if STYLES._theme == 'light' else '#ffffff'
        bg_color = '#f5f5f5' if STYLES._theme == 'light' else '#1e1e1e'
        
        self.header_label.setStyleSheet(f"color: {text_color}; font-size: 22px; font-weight: bold; padding: 10px 0;")
        self.setStyleSheet(f"background-color: {bg_color};")
        self.results_text.setStyleSheet(self.styles['textedit'])