import os
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QFrame, QLabel, QScrollArea, QSizePolicy,
    QPushButton, QHBoxLayout, QGridLayout, QStackedWidget, QStackedLayout,
    QSlider, QMessageBox, QDialog,
)
from PySide6.QtCore import Qt, QUrl
from PySide6.QtGui import QPixmap
from PySide6.QtMultimedia import QMediaPlayer, QAudioOutput
from PySide6.QtMultimediaWidgets import QVideoWidget
from core.database import Database
from core.statistics_analyzer import StatisticsAnalyzer
from ui.dialogs.post_edit_dialog import PostEditDialog
from core.logging_config import logger
from ui.styles import (
    STYLES, apply_theme_to_page, get_theme_colors, get_page_header_style,
    get_storage_summary_styles, get_compact_button_stylesheet, apply_panel_label_style,
)
from ui.ui_scale import UiScale
from worker.download_worker import WallStatsRefreshWorker
from core.config_manager import load_env_settings
from core.post_temp_folder import get_post_temp_folder_manager

class StoragePage(QWidget):
    """Исправленная страница хранилища: поддержка множественных медиа, правильные пропорции, центрирование"""
    def __init__(self, styles=None):
        super().__init__()
        self.styles = styles or STYLES.get_styles()
        self.loaded_count = 0
        self.limit = 20
        self.total_posts = 0
        self._rendered_posts = []
        self.active_players = {}
        self._last_posts = []
        self.stats_worker = None
        self._analyzer = StatisticsAnalyzer()
        self._temp_folder = get_post_temp_folder_manager()
        self.init_ui()
        self._update_temp_folder_bar()

    def _theme_colors(self):
        c = get_theme_colors()
        if STYLES._theme == 'light':
            return {
                'title': c['text'], 'muted': c['text_muted'], 'text': c['text'], 'tag': '#2f6fce',
                'card_bg': c['card'], 'card_border': c['separator'], 'separator': c['separator'],
                'media_bg': c['input_bg'], 'empty': c['text_muted'],
            }
        return {
            'title': c['text'], 'muted': c['text_muted'], 'text': c['text'], 'tag': '#6ea8ff',
            'card_bg': c['card'], 'card_border': c['input_border'], 'separator': c['separator'],
            'media_bg': c['input_bg'], 'empty': c['text_muted'],
        }

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

        header = QLabel("Хранилище постов")
        header.setStyleSheet(get_page_header_style())
        self.header_label = header
        layout.addWidget(header)

        self.summary_panel = QFrame()
        self.summary_panel.setObjectName("storageSummary")
        summary_layout = QVBoxLayout(self.summary_panel)
        summary_layout.setContentsMargins(UiScale.px(14), UiScale.px(10), UiScale.px(14), UiScale.px(10))
        summary_layout.setSpacing(UiScale.px(8))

        top_row = QHBoxLayout()
        self.storage_stats_label = QLabel()
        self.storage_stats_label.setWordWrap(True)
        self.storage_stats_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        top_row.addWidget(self.storage_stats_label, 1)
        self.refresh_summary_btn = QPushButton("Обновить")
        self.refresh_summary_btn.setToolTip("Обновить сводку архива")
        self.refresh_summary_btn.clicked.connect(self.update_storage_stats)
        top_row.addWidget(self.refresh_summary_btn)
        self.update_stats_btn = QPushButton("Статистика из VK")
        self.update_stats_btn.setToolTip("Обновить лайки, комментарии и репосты из ВКонтакте")
        self.update_stats_btn.clicked.connect(self.start_stats_update)
        self.update_stats_btn.setVisible(False)
        top_row.addWidget(self.update_stats_btn)
        summary_layout.addLayout(top_row)

        self.summary_sep = QFrame()
        self.summary_sep.setFrameShape(QFrame.HLine)
        self.summary_sep.setFixedHeight(1)
        summary_layout.addWidget(self.summary_sep)

        folder_row = QHBoxLayout()
        folder_row.setSpacing(UiScale.px(8))
        self.temp_folder_title = QLabel("Файлы поста на рабочем столе")
        folder_row.addWidget(self.temp_folder_title)
        self.temp_folder_path = QLabel("— выберите «Файлы на рабочий стол» на карточке поста")
        self.temp_folder_path.setWordWrap(True)
        self.temp_folder_path.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        folder_row.addWidget(self.temp_folder_path, 1)

        self._theme_custom_labels = [
            self.storage_stats_label, self.temp_folder_title, self.temp_folder_path,
        ]
        self.open_temp_folder_btn = QPushButton("Открыть")
        self.open_temp_folder_btn.clicked.connect(self._open_current_temp_folder)
        folder_row.addWidget(self.open_temp_folder_btn)
        self.remove_temp_folder_btn = QPushButton("Удалить")
        self.remove_temp_folder_btn.clicked.connect(self._remove_temp_folder)
        folder_row.addWidget(self.remove_temp_folder_btn)
        summary_layout.addLayout(folder_row)

        layout.addWidget(self.summary_panel)
        self._apply_summary_styles()
        self._update_temp_folder_bar()

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

    def _apply_summary_styles(self):
        ss = get_storage_summary_styles()
        self.summary_panel.setStyleSheet(ss['frame'])
        self.summary_sep.setStyleSheet(ss['sep'])
        apply_panel_label_style(self.storage_stats_label, ss['stats'])
        apply_panel_label_style(self.temp_folder_title, ss['folder'])
        apply_panel_label_style(self.temp_folder_path, ss['folder_path'])
        btn_h = UiScale.px(30)
        for btn in (
            self.refresh_summary_btn, self.update_stats_btn,
            self.open_temp_folder_btn, self.remove_temp_folder_btn,
        ):
            btn.setFixedHeight(btn_h)
        self.refresh_summary_btn.setStyleSheet(get_compact_button_stylesheet(False))
        self.update_stats_btn.setStyleSheet(get_compact_button_stylesheet(True))
        self.open_temp_folder_btn.setStyleSheet(get_compact_button_stylesheet(True))
        self.remove_temp_folder_btn.setStyleSheet(get_compact_button_stylesheet(False))

    def update_storage_stats(self):
        try:
            db = Database()
            stats = db.get_stats()
            db.close()
            self.storage_stats_label.setText(
                f"Постов: {stats['total']} "
                f"(ВК {stats.get('vk', stats['total'])}, ручные {stats.get('manual', 0)}) | "
                f"Файлов: {stats.get('files', 0)} "
                f"(фото {stats['photos']}, видео {stats['videos']}, клипы {stats['clips']}) | "
                f"лайки {stats.get('likes', 0)}, "
                f"коммент. {stats.get('comments', 0)}, "
                f"репосты {stats.get('shares', 0)}"
            )
        except Exception as e:
            logger.error(f"Error updating storage stats: {e}")

    def _clear_posts_layout(self):
        while self.posts_layout.count():
            child = self.posts_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()

    def _refresh_load_more_button(self):
        has_more = self.loaded_count < self.total_posts
        self.load_more_btn.setVisible(has_more)
        self.load_more_btn.setEnabled(has_more)

    def _render_posts(self):
        self._clear_posts_layout()

        if not self._rendered_posts:
            lbl = QLabel("Постов пока нет")
            lbl.setStyleSheet(f"color: {self._theme_colors()['muted']}; font-size: 16px; padding: 50px;")
            lbl.setAlignment(Qt.AlignCenter)
            self.posts_layout.addWidget(lbl)
            self.update_stats_btn.setVisible(False)
            self._refresh_load_more_button()
            return

        for post in self._rendered_posts:
            self.posts_layout.addWidget(self.create_post_widget(post))

        self.posts_layout.addStretch()
        self.update_stats_btn.setVisible(True)
        self._refresh_load_more_button()

    def load_posts(self, posts, clear=True):
        # Совместимость со старым API вызовов из других страниц
        if clear:
            self._rendered_posts = list(posts)
            self._last_posts = list(posts)
            self.loaded_count = len(posts)
            self.total_posts = max(self.total_posts, self.loaded_count)
        else:
            self._rendered_posts.extend(list(posts))
            self._last_posts = list(self._rendered_posts)
            self.loaded_count = len(self._rendered_posts)
        self._render_posts()

    def reload_posts(self):
        try:
            db = Database()
            db.recalculate_posts_importance()
            self.total_posts = db.get_posts_count()
            page = db.get_posts_paginated(limit=self.limit, offset=0)
            db.close()

            self._rendered_posts = list(page)
            self._last_posts = list(page)
            self.loaded_count = len(page)
            self._render_posts()
        except Exception as e:
            logger.error("reload_posts error: %s", e, exc_info=True)
            QMessageBox.warning(self, "Ошибка", f"Не удалось загрузить посты:\n{e}")

    def focus_post(self, original_post_id: int) -> bool:
        """Прокрутка к карточке поста; при необходимости подгружает запись в список."""
        oid = int(original_post_id)
        for i in range(self.posts_layout.count()):
            item = self.posts_layout.itemAt(i)
            w = item.widget() if item else None
            if w and getattr(w, "_post_oid", None) == oid:
                self.scroll_area.ensureWidgetVisible(w)
                w.setStyleSheet(self._post_card_style() + "border: 2px solid #3a7bd5;")
                return True
        try:
            db = Database()
            row = db.get_post_storage_row(oid)
            db.close()
            if row:
                self._rendered_posts = [row] + [
                    p for p in self._rendered_posts if (p[0] if p else None) != oid
                ]
                self._last_posts = list(self._rendered_posts)
                self.loaded_count = len(self._rendered_posts)
                self._render_posts()
                return self.focus_post(oid)
        except Exception as e:
            logger.error("focus_post: %s", e)
        return False

    def showEvent(self, event):
        super().showEvent(event)
        try:
            db = Database()
            db.recalculate_posts_importance()
            db.close()
        except Exception as e:
            logger.error("showEvent recalc importance: %s", e)
        if self._last_posts:
            self._render_posts()
        else:
            self.reload_posts()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if self.isVisible() and self._last_posts:
            self._render_posts()

    def load_more_posts(self):
        try:
            db = Database()
            batch = db.get_posts_paginated(limit=self.limit, offset=self.loaded_count)
            db.close()
            if batch:
                self.load_posts(batch, clear=False)
            else:
                self._refresh_load_more_button()
        except Exception as e:
            QMessageBox.warning(self, "Ошибка", f"Не удалось загрузить посты:\n{e}")

    def _is_manual_post(self, post) -> bool:
        source = (post[17] if len(post) > 17 else None) or ''
        if str(source).lower() == 'manual':
            return True
        try:
            orig = post[0]
            return orig is not None and int(orig) < 0
        except (TypeError, ValueError):
            return False

    def create_post_widget(self, post):
        post_id = str(post[1]) if len(post) > 1 and post[1] is not None else "Unknown"
        date = str(post[2]) if len(post) > 2 and post[2] is not None else ""
        text = str(post[3]) if len(post) > 3 and post[3] is not None else ""
        tags = str(post[4]) if len(post) > 4 and post[4] is not None else ""
        is_manual = self._is_manual_post(post)
        source_label = (post[18] if len(post) > 18 else None) or "Ручная загрузка"
        original_id = post[0]

        likes = post[5] if len(post) > 5 else 0
        comments = post[6] if len(post) > 6 else 0
        shares = post[7] if len(post) > 7 else 0

        # Медиа
        media_type = str(post[8]) if len(post) > 8 and post[8] is not None else ""
        media_path = str(post[9]) if len(post) > 9 and post[9] is not None else ""

        frame = QFrame()
        frame._post_oid = original_id  # type: ignore[attr-defined]
        frame.setStyleSheet(self._post_card_style())
        layout = QVBoxLayout(frame)
        layout.setSpacing(12)
        c = self._theme_colors()

        meta_row = QHBoxLayout()
        if date:
            d_lbl = QLabel(f"Дата: {date}")
            d_lbl.setStyleSheet(f"color: {c['muted']}; font-size: 12px; font-weight: 500;")
            meta_row.addWidget(d_lbl)
        if is_manual:
            src_lbl = QLabel(f"Источник: {source_label}")
            src_lbl.setStyleSheet(f"color: {c.get('tag', c['text'])}; font-size: 13px; font-weight: 600;")
            meta_row.addWidget(src_lbl)
        else:
            src_lbl = QLabel("Источник: ВКонтакте")
            src_lbl.setStyleSheet(f"color: {c['muted']}; font-size: 12px; font-weight: 500;")
            meta_row.addWidget(src_lbl)
        meta_row.addStretch()
        layout.addLayout(meta_row)

        show_stats = not is_manual and (likes or comments or shares)
        if show_stats:
            stats_layout = QHBoxLayout()
            stats_layout.setContentsMargins(0, 0, 0, 5)
            stats_layout.setSpacing(15)
            lbl_likes = QLabel(f"Лайки: {likes}")
            lbl_likes.setStyleSheet(f"color: {c['text']}; font-size: 13px; font-weight: 600;")
            stats_layout.addWidget(lbl_likes)
            lbl_comments = QLabel(f"Коммент.: {comments}")
            lbl_comments.setStyleSheet(f"color: {c['text']}; font-size: 13px; font-weight: 600;")
            stats_layout.addWidget(lbl_comments)
            lbl_shares = QLabel(f"Репосты: {shares}")
            lbl_shares.setStyleSheet(f"color: {c['text']}; font-size: 13px; font-weight: 600;")
            stats_layout.addWidget(lbl_shares)
            stats_layout.addStretch()
            layout.addLayout(stats_layout)

        if text:
            t_lbl = QLabel(text)
            t_lbl.setStyleSheet(f"color: {c['text']}; font-size: 14px; line-height: 1.6;")
            t_lbl.setWordWrap(True)
            layout.addWidget(t_lbl)
        display_tags = self._tags_for_display(post, tags)
        if display_tags:
            tg_lbl = QLabel(display_tags)
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

        actions_row = QHBoxLayout()
        actions_row.setContentsMargins(0, 4, 0, 0)
        actions_row.addStretch()
        files_btn = QPushButton("Файлы на рабочий стол")
        files_btn.setStyleSheet(self.styles['button_secondary'])
        files_btn.setFixedHeight(36)
        files_btn.setMinimumWidth(180)
        files_btn.setToolTip(
            "Копирует фото и видео поста во временную папку на рабочем столе и открывает её в проводнике"
        )
        files_btn.clicked.connect(
            lambda _=False, oid=original_id, dt=date: self._export_post_files(oid, dt)
        )
        actions_row.addWidget(files_btn)
        edit_btn = QPushButton("Редактировать")
        edit_btn.setStyleSheet(self.styles['button_secondary'])
        edit_btn.setFixedHeight(36)
        edit_btn.setMinimumWidth(140)
        edit_btn.clicked.connect(lambda _=False, oid=original_id: self._edit_post(oid))
        actions_row.addWidget(edit_btn)
        layout.addLayout(actions_row)

        author, teacher_tag, dept_tag = self._extract_author_meta(post)
        layout.addWidget(self._create_author_strip(author, teacher_tag, dept_tag, is_manual))
        return frame

    def _tags_for_display(self, post, tags_str: str) -> str:
        """Список тегов без дубля хэштега преподавателя (он только в блоке авторства)."""
        if not tags_str:
            return ''
        teacher_ht = post[12] if len(post) > 12 else ''
        teacher_key = (teacher_ht or '').strip().lower().replace('ё', 'е')
        parts = []
        for token in tags_str.split():
            key = token.strip().lower().replace('ё', 'е')
            if teacher_key and key == teacher_key:
                continue
            parts.append(token)
        return ' '.join(parts)

    def _edit_post(self, original_post_id):
        try:
            db = Database()
            full = db.get_post_by_original_id(original_post_id)
            db.close()
            if not full:
                QMessageBox.warning(self, "Ошибка", "Пост не найден.")
                return
            dlg = PostEditDialog(full, self, self.styles)
            if dlg.exec() == QDialog.Accepted and dlg.was_saved():
                self.reload_posts()
        except Exception as e:
            logger.error("_edit_post: %s", e, exc_info=True)
            QMessageBox.warning(self, "Ошибка", f"Не удалось открыть редактор:\n{e}")

    def _extract_author_meta(self, post):
        from core.post_tags import is_teacher_hashtag_in_text

        post_text = post[3] if len(post) > 3 else ''
        teacher_hashtag = (post[12] if len(post) > 12 else '') or ''
        teacher_hashtag = str(teacher_hashtag).strip()
        if (
            not teacher_hashtag
            or teacher_hashtag in ('—', 'None')
            or not is_teacher_hashtag_in_text(post_text, teacher_hashtag)
        ):
            return '—', '—', '—'
        department_hashtag = post[13] if len(post) > 13 else ''
        dept_hashtag = post[16] if len(post) > 16 else ''
        author = self._analyzer._resolve_author_fio('', '', teacher_hashtag)
        dept_tag = (department_hashtag or dept_hashtag or '').strip() or '—'
        return author or '—', teacher_hashtag, dept_tag

    def _create_author_strip(self, author, teacher_tag, dept_tag, is_manual=False):
        c = self._theme_colors()
        strip = QFrame()
        strip.setStyleSheet(
            f"QFrame {{ background-color: {c['media_bg']}; border-radius: 10px; border: none; }}"
        )
        strip_layout = QHBoxLayout(strip)
        strip_layout.setContentsMargins(14, 10, 14, 10)
        if is_manual and author == '—':
            author = 'не указан (материал не из ВК)'
        label = QLabel(
            f"Автор: {author}   ·   Хэштег преподавателя: {teacher_tag}   ·   Хэштег кафедры: {dept_tag}"
        )
        label.setWordWrap(True)
        label.setStyleSheet(f"color: {c['muted']}; font-size: 12px; line-height: 1.4;")
        strip_layout.addWidget(label)
        return strip

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

    def _update_temp_folder_bar(self):
        folder = self._temp_folder.current_folder
        ss = get_storage_summary_styles()
        if folder:
            pid = self._temp_folder.current_post_id
            self.temp_folder_title.setText(f"Папка поста #{pid}")
            path = str(folder)
            if len(path) > 72:
                path = "…" + path[-69:]
            self.temp_folder_path.setText(path)
            apply_panel_label_style(self.temp_folder_title, ss['folder'])
            apply_panel_label_style(self.temp_folder_path, ss['folder_path'])
            self.open_temp_folder_btn.setEnabled(True)
            self.remove_temp_folder_btn.setEnabled(True)
        else:
            self.temp_folder_title.setText("Файлы поста на рабочем столе")
            self.temp_folder_path.setText(
                "Кнопка «Файлы на рабочий стол» на карточке — копия вложений в папку на рабочем столе"
            )
            apply_panel_label_style(self.temp_folder_title, ss['folder'])
            apply_panel_label_style(self.temp_folder_path, ss['folder_path'])
            self.open_temp_folder_btn.setEnabled(False)
            self.remove_temp_folder_btn.setEnabled(False)

    def _export_post_files(self, original_post_id, date_str: str = ""):
        ok, message = self._temp_folder.export_post(
            original_post_id,
            date_str=date_str,
            open_explorer=True,
        )
        self._update_temp_folder_bar()
        win = self.window()
        if hasattr(win, 'log'):
            win.log(message.split('\n')[0] if message else "Готово")
        if ok:
            QMessageBox.information(self, "Файлы поста", message)
        else:
            QMessageBox.warning(self, "Файлы поста", message)

    def _open_current_temp_folder(self):
        folder = self._temp_folder.current_folder
        if not folder:
            QMessageBox.information(self, "Папка", "Временная папка не создана.")
            return
        self._temp_folder.open_in_explorer(folder)

    def _remove_temp_folder(self):
        if not self._temp_folder.current_folder:
            self._update_temp_folder_bar()
            return
        answer = QMessageBox.question(
            self,
            "Удалить папку",
            f"Удалить временную папку?\n\n{self._temp_folder.folder_label()}",
            QMessageBox.Yes | QMessageBox.No,
        )
        if answer != QMessageBox.Yes:
            return
        if self._temp_folder.remove_folder():
            self._update_temp_folder_bar()
            QMessageBox.information(self, "Готово", "Временная папка удалена.")
        else:
            QMessageBox.warning(
                self,
                "Ошибка",
                "Не удалось удалить папку. Закройте файлы в проводнике и повторите.",
            )

    def cleanup_temp_folder(self):
        self._temp_folder.cleanup()
        self._update_temp_folder_bar()

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
        self._secondary_buttons = [
            self.refresh_summary_btn,
            self.remove_temp_folder_btn,
            self.load_more_btn,
        ]
        apply_theme_to_page(self, styles)
        c = get_theme_colors()
        self.header_label.setStyleSheet(get_page_header_style())
        self._apply_summary_styles()
        self._update_temp_folder_bar()
        if self._last_posts:
            self._render_posts()

    # ===== ОБНОВЛЕНИЕ СТАТИСТИКИ ИЗ VK =====
    def start_stats_update(self):
        """Запускает обновление статистики из VK"""
        try:
            settings = load_env_settings()
            token = settings.get('token', '')
            group_link = settings.get('group_link', '')

            win = self.window()
            if hasattr(win, 'settings_page'):
                ui_token = win.settings_page.token_input.text().strip()
                ui_group = win.settings_page.group_input.text().strip()
                if ui_token:
                    token = ui_token
                if ui_group:
                    group_link = ui_group

            if not token:
                QMessageBox.warning(
                    self, "Ошибка",
                    "Не найден токен VK.\nОткройте «Настройки» и введите токен доступа.",
                )
                return

            if not group_link:
                QMessageBox.warning(
                    self, "Ошибка",
                    "Не указано сообщество.\nОткройте «Настройки» и укажите ссылку или ID группы.",
                )
                return
            
            reply = QMessageBox.question(
                self,
                "Подтверждение",
                "Обновить лайки, комментарии и репосты для постов из ВКонтакте?\n\n"
                "Материалы, добавленные вручную, не затрагиваются.\n\n"
                "Сначала сверка со стеной сообщества (wall.get), затем для оставшихся — "
                "точечный запрос wall.getById по ID поста.\n\n"
                "Нужны тот же токен и та же группа, что при загрузке медиа.",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )
            
            if reply == QMessageBox.Yes:
                win = self.window()
                if hasattr(win, 'save_settings'):
                    win.save_settings()

                self.update_stats_btn.setEnabled(False)
                self.load_more_btn.setEnabled(False)
                
                self.stats_worker = WallStatsRefreshWorker(token, group_link)
                self.stats_worker.signals.progress.connect(self.on_stats_progress)
                self.stats_worker.signals.finished.connect(self.on_stats_finished)
                self.stats_worker.signals.error.connect(self.on_stats_error)
                self.stats_worker.start()
                
                self.storage_stats_label.setText("Обновление статистики из VK…")
                
        except Exception as e:
            logger.error(f"Error starting stats update: {e}")
            QMessageBox.critical(self, "Ошибка", f"Не удалось запустить обновление:\n{e}")

    def on_stats_progress(self, message):
        self.storage_stats_label.setText(message)

    def _reload_posts_from_db(self):
        try:
            self.reload_posts()
        except Exception as e:
            logger.error("Reload posts after stats update: %s", e)

    def on_stats_finished(self, updated_count, not_found_count):
        self.update_stats_btn.setEnabled(True)
        self.load_more_btn.setEnabled(True)
        self.update_storage_stats()
        self._reload_posts_from_db()

        if updated_count == -1:
            QMessageBox.information(self, "Готово", "В базе нет постов для обновления.")
            return

        if updated_count == 0:
            QMessageBox.warning(
                self,
                "Статистика не обновлена",
                "Не удалось получить данные из VK.\n\n"
                f"Не найдено в VK: {not_found_count}.\n\n"
                "Проверьте токен, ссылку на ту же группу, что при загрузке, и лог приложения.",
            )
        elif not_found_count > 0:
            QMessageBox.information(
                self,
                "Готово",
                f"Обновлено постов: {updated_count}.\n"
                f"Не найдено в VK (удалены или другая группа): {not_found_count}.",
            )
        else:
            QMessageBox.information(
                self,
                "Готово",
                f"Статистика обновлена для {updated_count} постов.",
            )

    def on_stats_error(self, error_msg):
        self.update_stats_btn.setEnabled(True)
        self.load_more_btn.setEnabled(True)
        self.update_storage_stats()
        QMessageBox.critical(self, "Ошибка", f"Произошла ошибка:\n\n{error_msg}")