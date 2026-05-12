import os
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QFrame, QLabel, QScrollArea, QSizePolicy,
    QPushButton, QHBoxLayout, QGridLayout, QStackedWidget, QStackedLayout,
    QSlider, QMessageBox
)
from PySide6.QtCore import Qt, QUrl
from PySide6.QtGui import QPixmap
from PySide6.QtMultimedia import QMediaPlayer, QAudioOutput
from PySide6.QtMultimediaWidgets import QVideoWidget
from core.database import Database
from core.logging_config import logger
from ui.styles import STYLES
from worker.update_stats_worker import UpdateStatsWorker
from core.config_manager import load_env_settings

class StoragePage(QWidget):
    """Исправленная страница хранилища: поддержка множественных медиа, правильные пропорции, центрирование"""
    def __init__(self, styles=None):
        super().__init__()
        self.styles = styles or STYLES.get_styles()
        self.loaded_count = 0
        self.limit = 20
        self.active_players = {}
        self._last_posts = []
        self.stats_worker = None
        self.init_ui()

    def _theme_colors(self):
        if STYLES._theme == 'light':
            return {'title': '#111827', 'muted': '#6b7280', 'text': '#111827', 'tag': '#2f6fce',
                    'card_bg': '#ffffff', 'card_border': '#d8dce5', 'separator': '#e5e7eb',
                    'media_bg': '#f3f4f6', 'empty': '#9ca3af'}
        return {'title': '#f3f4f6', 'muted': '#9aa4b2', 'text': '#e5e7eb', 'tag': '#6ea8ff',
                'card_bg': '#262a32', 'card_border': '#3f4654', 'separator': '#3f4654',
                'media_bg': '#16191f', 'empty': '#7b8594'}

    def _post_card_style(self):
        c = self._theme_colors()
        return f"QFrame {{ background-color: {c['card_bg']}; border: 1px solid {c['card_border']}; border-radius: 14px; padding: 16px; }}"

    def _content_width(self):
        viewport = self.scroll_area.viewport()
        width = viewport.width() if viewport else self.width()
        return max(320, min(width - 28, 1320))

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        header = QLabel("📚 Хранилище постов")
        c = self._theme_colors()
        header.setStyleSheet(f"font-size: 24px; font-weight: 700; padding: 8px 2px 12px 2px; color: {c['title']};")
        self.header_label = header
        layout.addWidget(header)

        # ✅ КОНТЕЙНЕР: СТАТИСТИКА + КНОПКА ОБНОВЛЕНИЯ
        stats_row = QFrame()
        stats_row.setStyleSheet(self.styles['frame'])
        stats_layout = QHBoxLayout(stats_row)
        stats_layout.setContentsMargins(15, 10, 15, 10)
        
        self.storage_stats_label = QLabel()
        self.storage_stats_label.setStyleSheet(f"color: {c['text']}; font-size: 14px; padding: 5px; font-weight: 500;")
        stats_layout.addWidget(self.storage_stats_label)
        
        stats_layout.addStretch()
        
        self.update_stats_btn = QPushButton("🔄 Обновить статистику из VK")
        self.update_stats_btn.setStyleSheet(self.styles['button_secondary'])
        self.update_stats_btn.setMinimumHeight(35)
        self.update_stats_btn.clicked.connect(self.start_stats_update)
        self.update_stats_btn.setVisible(False)
        stats_layout.addWidget(self.update_stats_btn)
        
        layout.addWidget(stats_row)

        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setStyleSheet("background-color: transparent; border: none;")
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)

        self.posts_container = QWidget()
        self.posts_container.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        self.posts_layout = QVBoxLayout(self.posts_container)
        self.posts_layout.setSpacing(15)
        self.posts_layout.setAlignment(Qt.AlignTop)

        self.scroll_area.setWidget(self.posts_container)
        layout.addWidget(self.scroll_area)

        self.load_more_btn = QPushButton("Загрузить ещё посты")
        self.load_more_btn.setStyleSheet(self.styles['button'])
        self.load_more_btn.setMinimumHeight(45)
        self.load_more_btn.clicked.connect(self.load_more_posts)
        self.load_more_btn.setVisible(False)
        layout.addWidget(self.load_more_btn)

        self.update_storage_stats()

    def update_storage_stats(self):
        try:
            db = Database()
            stats = db.get_stats()
            db.close()
            self.storage_stats_label.setText(
                f"Всего постов: {stats['total']} | Фото: {stats['photos']} | Видео: {stats['videos']} | Клипы: {stats['clips']}"
            )
        except Exception as e:
            logger.error(f"Error updating storage stats: {e}")

    def load_posts(self, posts, clear=True):
        if clear:
            self._last_posts = list(posts)
            while self.posts_layout.count():
                child = self.posts_layout.takeAt(0)
                if child.widget(): child.widget().deleteLater()
            self.loaded_count = 0

        if not posts:
            if clear:
                lbl = QLabel("📭 Постов пока нет")
                lbl.setStyleSheet(f"color: {self._theme_colors()['muted']}; font-size: 16px; padding: 50px;")
                lbl.setAlignment(Qt.AlignCenter)
                self.posts_layout.addWidget(lbl)
            self.load_more_btn.setVisible(False)
            self.update_stats_btn.setVisible(False)
            return

        sorted_posts = sorted(posts, key=lambda x: x[2] if len(x) > 2 else '', reverse=True)
        for post in sorted_posts[self.loaded_count:self.loaded_count + self.limit]:
            self.posts_layout.addWidget(self.create_post_widget(post))

        self.loaded_count += len(sorted_posts[self.loaded_count:self.loaded_count + self.limit])
        self.load_more_btn.setVisible(self.loaded_count < len(sorted_posts))
        self.update_stats_btn.setVisible(len(posts) > 0)
        self.posts_layout.addStretch()

    def showEvent(self, event):
        super().showEvent(event)
        if self._last_posts: self.load_posts(self._last_posts, clear=True)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if self.isVisible() and self._last_posts: self.load_posts(self._last_posts, clear=True)

    def load_more_posts(self):
        try:
            db = Database()
            all_posts = db.get_all_posts(limit=500)
            db.close()
            self.load_posts(all_posts[self.loaded_count:], clear=False)
        except Exception as e:
            QMessageBox.warning(self, "Ошибка", f"Не удалось загрузить посты:\n{e}")

    def create_post_widget(self, post):
        post_id = str(post[1]) if len(post) > 1 and post[1] is not None else "Unknown"
        date = str(post[2]) if len(post) > 2 and post[2] is not None else ""
        text = str(post[3]) if len(post) > 3 and post[3] is not None else ""
        tags = str(post[4]) if len(post) > 4 and post[4] is not None else ""
        
        # ✅ Статистика (Без просмотров)
        likes = post[5] if len(post) > 5 else 0
        comments = post[6] if len(post) > 6 else 0
        shares = post[7] if len(post) > 7 else 0

        # Медиа
        media_type = str(post[8]) if len(post) > 8 and post[8] is not None else ""
        media_path = str(post[9]) if len(post) > 9 and post[9] is not None else ""

        frame = QFrame()
        frame.setStyleSheet(self._post_card_style())
        layout = QVBoxLayout(frame)
        layout.setSpacing(12)
        c = self._theme_colors()

        if date:
            d_lbl = QLabel(f"📅 {date}")
            d_lbl.setStyleSheet(f"color: {c['muted']}; font-size: 12px; font-weight: 500;")
            layout.addWidget(d_lbl)
            
        # ✅ Статистика (Лайки, Комменты, Репосты)
        stats_layout = QHBoxLayout()
        stats_layout.setContentsMargins(0, 0, 0, 5)
        stats_layout.setSpacing(15)
        
        lbl_likes = QLabel(f"❤️ {likes}")
        lbl_likes.setStyleSheet(f"color: {c['text']}; font-size: 13px; font-weight: 600;")
        stats_layout.addWidget(lbl_likes)
        
        lbl_comments = QLabel(f"💬 {comments}")
        lbl_comments.setStyleSheet(f"color: {c['text']}; font-size: 13px; font-weight: 600;")
        stats_layout.addWidget(lbl_comments)
        
        lbl_shares = QLabel(f"🔄 {shares}")
        lbl_shares.setStyleSheet(f"color: {c['text']}; font-size: 13px; font-weight: 600;")
        stats_layout.addWidget(lbl_shares)
        
        stats_layout.addStretch()
        layout.addLayout(stats_layout)

        if text:
            t_lbl = QLabel(text)
            t_lbl.setStyleSheet(f"color: {c['text']}; font-size: 14px; line-height: 1.6;")
            t_lbl.setWordWrap(True)
            layout.addWidget(t_lbl)
        if tags:
            tg_lbl = QLabel(tags)
            tg_lbl.setStyleSheet(f"color: {c['tag']}; font-size: 13px; font-weight: 600;")
            tg_lbl.setWordWrap(True)
            layout.addWidget(tg_lbl)

        if media_path and media_path != "None" and media_type and media_type != "None":
            paths_list = [p.strip() for p in media_path.split(',') if p.strip() and p.strip().lower() != 'none']
            types_list = [t.strip() for t in media_type.split(',') if t.strip() and t.strip().lower() != 'none']
            
            normalized_media = []
            for idx in range(len(paths_list)):
                m_path = paths_list[idx]
                m_type = types_list[idx] if idx < len(types_list) else "photo"
                normalized_media.append((m_path, m_type))
            
            normalized_media.sort(key=lambda item: 0 if str(item[1]).lower() in ("video", "clip") else 1)
            
            if normalized_media:
                media_block = self._create_media_collection_widget(normalized_media, post_id)
                layout.addWidget(media_block)

        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setStyleSheet(f"background-color: {c['separator']}; min-height: 1px; border: none;")
        layout.addWidget(line)
        return frame

    def _create_media_collection_widget(self, media_items, post_id):
        colors = self._theme_colors()
        wrapper = QFrame()
        wrapper.setStyleSheet("QFrame {background-color: transparent; border: none;}")
        wrapper_layout = QVBoxLayout(wrapper)
        wrapper_layout.setContentsMargins(0, 4, 0, 0)
        wrapper_layout.setSpacing(10)

        top_row = QHBoxLayout()
        top_row.setContentsMargins(0, 0, 0, 0)
        media_count = len(media_items)
        count_label = QLabel(f"Медиа: {media_count}")
        count_label.setStyleSheet(f"color: {colors['muted']}; font-size: 12px; font-weight: 600;")
        top_row.addWidget(count_label)
        top_row.addStretch()
        wrapper_layout.addLayout(top_row)

        videos = [item for item in media_items if str(item[1]).lower() in ("video", "clip")]
        photos = [item for item in media_items if str(item[1]).lower() not in ("video", "clip")]

        content_w = self._content_width()
        photo_columns = 1
        if content_w >= 1000: photo_columns = 4
        elif content_w >= 760: photo_columns = 3
        elif content_w >= 520: photo_columns = 2

        for idx, (path, media_type) in enumerate(videos):
            media_widget = self._create_media_widget(
                path, media_type, f"{post_id}_video_{idx}",
                target_w=min(800, content_w - 40), target_h=420
            )
            if media_widget: wrapper_layout.addWidget(media_widget)

        if photos:
            grid_page = QWidget()
            grid_layout = QGridLayout(grid_page)
            grid_layout.setContentsMargins(0, 0, 0, 0)
            grid_layout.setSpacing(10)

            for idx, (path, media_type) in enumerate(photos):
                row = idx // photo_columns
                col = idx % photo_columns
                tile_w = min(280, max(220, (content_w - (photo_columns - 1) * 10) // photo_columns))
                tile_h = 220
                media_widget = self._create_media_widget(
                    path, media_type, f"{post_id}_photo_{idx}",
                    target_w=tile_w, target_h=tile_h
                )
                if media_widget: grid_layout.addWidget(media_widget, row, col)

            wrapper_layout.addWidget(grid_page)

        return wrapper

    def _create_media_widget(self, media_path, media_type, post_id, target_w=None, target_h=None):
        if media_type.lower() == 'photo':
            return self._create_photo_widget(media_path, target_w, target_h)
        return self._create_video_widget(media_path, post_id, target_w, target_h)

    def _create_photo_widget(self, media_path, target_w=None, target_h=None):
        colors = self._theme_colors()
        target_w = target_w or min(680, self._content_width())
        target_h = target_h or 400
        
        photo_label = QLabel()
        photo_label.setAlignment(Qt.AlignCenter)
        photo_label.setMinimumHeight(target_h)
        photo_label.setMaximumHeight(target_h + 50)
        photo_label.setStyleSheet(f"background-color: {colors['media_bg']}; border-radius: 12px;")
        
        if os.path.exists(media_path):
            pixmap = QPixmap(media_path)
            fit_pixmap = pixmap.scaled(target_w, target_h, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            photo_label.setPixmap(fit_pixmap)
        else:
            photo_label.setText("Фото не найдено")
            photo_label.setStyleSheet(f"color: {colors['empty']}; font-size: 14px;")
        return photo_label

    def _create_video_widget(self, video_path, post_id, target_w, target_h):
        c = self._theme_colors()
        stack = QStackedWidget()
        stack.setFixedSize(target_w, target_h)
        stack.setStyleSheet(f"background-color: {c['media_bg']}; border-radius: 10px;")

        thumb_page = QWidget()
        thumb_layout = QVBoxLayout(thumb_page)
        thumb_layout.setContentsMargins(0, 0, 0, 0)

        thumb_lbl = QLabel()
        thumb_lbl.setAlignment(Qt.AlignCenter)
        thumb_lbl.setCursor(Qt.PointingHandCursor)
        
        thumb = self._generate_thumbnail(video_path)
        if thumb and os.path.exists(thumb):
            px = QPixmap(thumb)
            px = px.scaled(target_w, target_h, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            thumb_lbl.setPixmap(px)
        else:
            thumb_lbl.setText("Видео")
            thumb_lbl.setStyleSheet(f"color: {c['empty']}; font-size: 40px; background-color: {c['media_bg']};")

        thumb_layout.addWidget(thumb_lbl)

        play_icon = QLabel("▶")
        play_icon.setAlignment(Qt.AlignCenter)
        play_icon.setStyleSheet("background-color: rgba(0,0,0,0.6); color: white; border: 2px solid white; border-radius: 20px; font-size: 20px; padding: 8px 14px;")
        
        overlay = QStackedLayout(thumb_page)
        overlay.setStackingMode(QStackedLayout.StackAll)
        overlay.addWidget(thumb_lbl)
        overlay.addWidget(play_icon)
        stack.addWidget(thumb_page)

        player_page = QWidget()
        player_page.setStyleSheet(f"background-color: {c['media_bg']};")
        pl_layout = QVBoxLayout(player_page)
        pl_layout.setContentsMargins(0, 0, 0, 0)
        stack.addWidget(player_page)

        def click(ev, p=video_path, pid=post_id, s=stack, pl=pl_layout):
            self._play_video(p, pid, s, pl, target_h)
        thumb_page.mousePressEvent = click
        return stack

    def _play_video(self, video_path, post_id, stack, player_layout, target_h=320):
        if not os.path.exists(video_path): return
        if post_id in self.active_players:
            stack.setCurrentIndex(1)
            return

        while player_layout.count(): player_layout.takeAt(0).widget().deleteLater()

        player = QMediaPlayer()
        video_w = QVideoWidget()
        video_w.setMinimumHeight(max(200, target_h - 60))
        video_w.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        video_w.setAspectRatioMode(Qt.KeepAspectRatio)
        player.setVideoOutput(video_w)

        audio = QAudioOutput()
        audio.setVolume(1.0)
        player.setAudioOutput(audio)
        player.setSource(QUrl.fromLocalFile(video_path))

        controls, _, _, _ = self._create_video_controls(post_id)
        player_layout.addWidget(video_w)
        player_layout.addWidget(controls)

        self.active_players[post_id] = {'player': player, 'stack': stack, 'controls': controls, 'video_widget': video_w, 'seeking': False}
        player.positionChanged.connect(lambda pos, pid=post_id: self._update_timeline(pid, pos))
        player.durationChanged.connect(lambda dur, pid=post_id: self._update_duration(pid, dur))
        player.playbackStateChanged.connect(lambda state, pid=post_id: self._on_playback_changed(pid, state))

        stack.setCurrentIndex(1)
        player.play()
        controls.setVisible(True)

    def _create_video_controls(self, post_id):
        controls_widget = QWidget()
        controls_widget.setStyleSheet("""
            QWidget {
                background-color: rgba(15, 18, 25, 0.92);
                border-bottom-left-radius: 12px;
                border-bottom-right-radius: 12px;
            }
        """)
        controls_widget.setFocusPolicy(Qt.NoFocus)
        
        controls_layout = QHBoxLayout(controls_widget)
        controls_layout.setContentsMargins(10, 8, 10, 8)
        controls_layout.setSpacing(10)
        
        play_pause_btn = QPushButton("⏸")
        play_pause_btn.setStyleSheet("""
            QPushButton {
                background-color: #2f6fce;
                color: white;
                border: none;
                font-size: 16px;
                padding: 4px 8px;
                min-width: 36px;
                min-height: 30px;
                border-radius: 8px;
            }
            QPushButton:hover { background-color: #3a7bd5; }
        """)
        play_pause_btn.setFocusPolicy(Qt.NoFocus)
        play_pause_btn.clicked.connect(lambda checked, pid=post_id: self._toggle_play_pause(pid))
        controls_layout.addWidget(play_pause_btn)
        
        timeline = QSlider(Qt.Horizontal)
        timeline.setStyleSheet("""
            QSlider::groove:horizontal {
                border: none;
                height: 6px;
                background: rgba(255, 255, 255, 0.2);
                border-radius: 3px;
            }
            QSlider::handle:horizontal {
                background: #3a7bd5;
                width: 14px;
                height: 14px;
                margin: -4px 0;
                border-radius: 7px;
            }
            QSlider::sub-page:horizontal {
                background: #3a7bd5;
                border-radius: 3px;
            }
        """)
        timeline.setFocusPolicy(Qt.NoFocus)
        timeline.sliderPressed.connect(lambda pid=post_id: self._on_slider_pressed(pid))
        timeline.sliderReleased.connect(lambda pid=post_id: self._on_slider_released(pid))
        timeline.setFixedHeight(20)
        controls_layout.addWidget(timeline)
        
        time_label = QLabel("0:00 / 0:00")
        time_label.setStyleSheet("color: white; font-size: 13px; min-width: 100px;")
        time_label.setAlignment(Qt.AlignRight)
        controls_layout.addWidget(time_label)
        
        close_btn = QPushButton("✕")
        close_btn.setStyleSheet("""
            QPushButton {
                background-color: #dc3545;
                color: white;
                border: none;
                border-radius: 8px;
                padding: 5px 10px;
                font-size: 12px;
                min-height: 30px;
            }
        """)
        close_btn.setFocusPolicy(Qt.NoFocus)
        close_btn.clicked.connect(lambda checked, pid=post_id: self._stop_video(pid))
        controls_layout.addWidget(close_btn)
        
        controls_widget.setVisible(False)
        return controls_widget, play_pause_btn, timeline, time_label

    def _toggle_play_pause(self, post_id):
        data = self.active_players.get(post_id)
        if not data: return
        player = data['player']
        if player.playbackState() == QMediaPlayer.PlayingState:
            player.pause()
        else:
            player.play()

    def _on_slider_pressed(self, post_id):
        data = self.active_players.get(post_id)
        if not data: return
        data['seeking'] = True

    def _on_slider_released(self, post_id):
        data = self.active_players.get(post_id)
        if not data: return
        try:
            slider = data['controls'].findChild(QSlider)
            if slider:
                data['player'].setPosition(slider.value())
        except: pass
        data['seeking'] = False

    def _update_timeline(self, post_id, pos):
        data = self.active_players.get(post_id)
        if not data or data.get('seeking'): return
        try:
            slider = data['controls'].findChild(QSlider)
            lbl = data['controls'].findChild(QLabel)
            if slider: slider.setValue(pos)
            if lbl: lbl.setText(f"{self._fmt(pos)} / {self._fmt(data['player'].duration())}")
        except: pass

    def _update_duration(self, post_id, dur):
        data = self.active_players.get(post_id)
        if not data: return
        try:
            t = data.get('timeline') or data['controls'].findChild(QSlider)
            l = data.get('time_label') or data['controls'].findChild(QLabel)
            if t: t.setMaximum(dur)
            if l: l.setText(f"0:00 / {self._fmt(dur)}")
        except: pass

    def _on_playback_changed(self, post_id, state):
        data = self.active_players.get(post_id)
        if not data: return
        try:
            btn = data['controls'].findChild(QPushButton)
            if state == QMediaPlayer.PlayingState and btn: btn.setText("⏸")
            elif state == QMediaPlayer.PausedState and btn: btn.setText("▶")
            if state == QMediaPlayer.StoppedState: self._stop_video(post_id)
        except: pass

    def _stop_video(self, post_id):
        data = self.active_players.pop(post_id, None)
        if not data: return
        try:
            data['player'].stop()
            data['stack'].setCurrentIndex(0)
            data['player'].deleteLater()
        except: pass

    def _fmt(self, ms):
        s = ms // 1000
        return f"{s // 60}:{s % 60:02d}"

    def _generate_thumbnail(self, video_path):
        try:
            if not os.path.exists(video_path): return None
            d = os.path.join(os.path.dirname(video_path), "thumbnails")
            os.makedirs(d, exist_ok=True)
            tp = os.path.join(d, os.path.basename(video_path).rsplit('.', 1)[0] + ".thumb.jpg")
            if os.path.exists(tp): return tp
            alt = video_path.replace('.mp4', '_thumb.jpg')
            if os.path.exists(alt): return alt
            return None
        except: return None

    def cleanup_players(self):
        for pid, data in list(self.active_players.items()):
            try:
                data['player'].stop()
                data['player'].deleteLater()
            except Exception:
                pass
        self.active_players.clear()

    def update_styles(self, styles):
        self.styles = styles
        text_color = '#000000' if STYLES._theme == 'light' else '#ffffff'
        bg_color = '#f5f5f5' if STYLES._theme == 'light' else '#1e1e1e'
        self.header_label.setStyleSheet(f"font-size: 24px; font-weight: 700; padding: 8px 2px 12px 2px; color: {text_color};")
        self.setStyleSheet(f"background-color: {bg_color};")
        self.load_more_btn.setStyleSheet(self.styles['button'])
        self.update_stats_btn.setStyleSheet(self.styles['button_secondary'])

    # ===== ОБНОВЛЕНИЕ СТАТИСТИКИ ИЗ VK =====
    def start_stats_update(self):
        """Запускает обновление статистики из VK"""
        try:
            settings = load_env_settings()
            token = settings.get('token', '')
            group_link = settings.get('group_link', '')
            
            if not token:
                QMessageBox.warning(self, "Ошибка", "Не найден токен VK!\nПерейдите на страницу загрузки и введите токен.")
                return
            
            if not group_link:
                QMessageBox.warning(self, "Ошибка", "Не найдена ссылка на группу!\nПерейдите на страницу загрузки и укажите группу.")
                return
            
            # ✅ Диалог подтверждения (БЕЗ просмотров)
            reply = QMessageBox.question(
                self,
                "Подтверждение",
                "Обновить статистику для всех постов из VK?\n\n"
                "Это может занять несколько минут.\n"
                "Будут обновлены: лайки, комментарии, репосты",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )
            
            if reply == QMessageBox.Yes:
                self.update_stats_btn.setEnabled(False)
                self.load_more_btn.setEnabled(False)
                
                self.stats_worker = UpdateStatsWorker(token, group_link)
                self.stats_worker.signals.progress.connect(self.on_stats_progress)
                self.stats_worker.signals.finished.connect(self.on_stats_finished)
                self.stats_worker.signals.error.connect(self.on_stats_error)
                self.stats_worker.start()
                
                self.storage_stats_label.setText("🔄 Обновление статистики...")
                
        except Exception as e:
            logger.error(f"Error starting stats update: {e}")
            QMessageBox.critical(self, "Ошибка", f"Не удалось запустить обновление:\n{e}")

    def on_stats_progress(self, message):
        self.storage_stats_label.setText(message)

    def on_stats_finished(self):
        self.update_stats_btn.setEnabled(True)
        self.load_more_btn.setEnabled(True)
        self.update_storage_stats()
        self.load_posts(self._last_posts, clear=True)
        
        QMessageBox.information(
            self,
            "Готово",
            "Статистика успешно обновлена!\n\n"
            "Актуальные данные загружены из ВКонтакте."
        )

    def on_stats_error(self, error_msg):
        self.update_stats_btn.setEnabled(True)
        self.load_more_btn.setEnabled(True)
        QMessageBox.critical(self, "Ошибка", f"Произошла ошибка:\n\n{error_msg}")