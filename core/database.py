import sqlite3
from config.settings import DB_NAME

class Database:
    """Класс для работы с SQLite базой данных"""
    
    def __init__(self, db_name=DB_NAME):
        self.db_name = db_name
        self.conn = None
        self.cursor = None
        self.connect()
        self.create_table()

    def connect(self):
        """Подключение к базе данных (вызывать в каждом потоке!)"""
        try:
            self.conn = sqlite3.connect(self.db_name, check_same_thread=False)
            self.cursor = self.conn.cursor()
        except Exception as e:
            print(f"DB Connect Error: {e}")
            raise

    def create_table(self):
        """Создание таблиц постов и статистики"""
        try:
            # Основная таблица постов
            self.cursor.execute("""
                CREATE TABLE IF NOT EXISTS posts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    post_id INTEGER,
                    original_post_id INTEGER,
                    date TEXT,
                    text TEXT,
                    tags TEXT,
                    media_type TEXT,
                    media_key TEXT,
                    media_path TEXT,
                    file_size TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Обновление старой схемы БД - добавляем столбцы статистики
            self.cursor.execute("PRAGMA table_info(posts)")
            columns = [row[1] for row in self.cursor.fetchall()]
            
            if "media_key" not in columns:
                self.cursor.execute("ALTER TABLE posts ADD COLUMN media_key TEXT")
            if "likes" not in columns:
                self.cursor.execute("ALTER TABLE posts ADD COLUMN likes INTEGER DEFAULT 0")
            if "comments" not in columns:
                self.cursor.execute("ALTER TABLE posts ADD COLUMN comments INTEGER DEFAULT 0")
            if "shares" not in columns:
                self.cursor.execute("ALTER TABLE posts ADD COLUMN shares INTEGER DEFAULT 0")
            if "views" not in columns:
                self.cursor.execute("ALTER TABLE posts ADD COLUMN views INTEGER DEFAULT 0")
            if "last_stats_update" not in columns:
                self.cursor.execute("ALTER TABLE posts ADD COLUMN last_stats_update TIMESTAMP")

            self.cursor.execute("""
                CREATE UNIQUE INDEX IF NOT EXISTS idx_posts_unique_media
                ON posts(original_post_id, media_type, media_key)
            """)
            
            # Таблица статистики по постам за период
            self.cursor.execute("""
                CREATE TABLE IF NOT EXISTS post_statistics (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    post_id INTEGER,
                    original_post_id INTEGER,
                    period_type TEXT,
                    period_start TEXT,
                    period_end TEXT,
                    likes INTEGER DEFAULT 0,
                    comments INTEGER DEFAULT 0,
                    shares INTEGER DEFAULT 0,
                    views INTEGER DEFAULT 0,
                    rank INTEGER,
                    recorded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            self.cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_post_stats_period
                ON post_statistics(period_type, period_start, period_end)
            """)
            
            # Таблица статистики преподавателей
            self.cursor.execute("""
                CREATE TABLE IF NOT EXISTS employee_statistics (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    employee_name TEXT,
                    period_type TEXT,
                    period_start TEXT,
                    period_end TEXT,
                    mention_count INTEGER DEFAULT 0,
                    post_count INTEGER DEFAULT 0,
                    total_likes INTEGER DEFAULT 0,
                    total_views INTEGER DEFAULT 0,
                    rank INTEGER,
                    recorded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            self.cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_emp_stats_name_period
                ON employee_statistics(employee_name, period_type, period_start)
            """)
            
            # Таблица статистики медиа (фото/видео)
            self.cursor.execute("""
                CREATE TABLE IF NOT EXISTS media_statistics (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    post_id INTEGER,
                    media_key TEXT,
                    media_type TEXT,
                    date TEXT,
                    likes INTEGER DEFAULT 0,
                    comments INTEGER DEFAULT 0,
                    shares INTEGER DEFAULT 0,
                    views INTEGER DEFAULT 0,
                    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            self.cursor.execute("""
                CREATE UNIQUE INDEX IF NOT EXISTS idx_media_stats_unique
                ON media_statistics(media_key, media_type)
            """)
            
            self.conn.commit()
        except Exception as e:
            print(f"DB Create Table Error: {e}")

    def post_exists(self, original_post_id):
        """Проверяет, существует ли уже пост с таким original_post_id"""
        try:
            self.cursor.execute(
                "SELECT COUNT(*) FROM posts WHERE original_post_id = ?",
                (original_post_id,)
            )
            count = self.cursor.fetchone()[0]
            return count > 0
        except Exception as e:
            print(f"DB Check Exists Error: {e}")
            return False

    def save_post(self, post_id, original_post_id, date, text, tags, media_type, media_path, file_size, 
                   media_key=None, likes=0, comments=0, shares=0, views=0):
        """Сохранение поста в базу данных (с проверкой на дубликаты и метриками)"""
        try:
            # Проверяем, не существует ли уже такое медиа.
            # Если есть media_key, проверяем по нему (стабильно между перезапусками).
            if media_key:
                self.cursor.execute("""
                    SELECT COUNT(*) FROM posts
                    WHERE original_post_id = ? AND media_type = ? AND media_key = ?
                """, (original_post_id, media_type, media_key))
            else:
                self.cursor.execute("""
                    SELECT COUNT(*) FROM posts 
                    WHERE original_post_id = ? AND media_path = ?
                """, (original_post_id, media_path))
            
            count = self.cursor.fetchone()[0]
            if count > 0:
                print(f"[DB] Дубликат: media already exists for post {original_post_id}")
                return False
            
            self.cursor.execute("""
                INSERT INTO posts 
                (post_id, original_post_id, date, text, tags, media_type, media_key, media_path, file_size, 
                 likes, comments, shares, views, last_stats_update)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            """, (post_id, original_post_id, date, text, tags, media_type, media_key, media_path, file_size,
                   likes, comments, shares, views))
            self.conn.commit()
            return True
        except Exception as e:
            print(f"DB Save Error: {e}")
            return False

    def search(self, query):
        """Поиск постов по тексту или тегам (группируем по original_post_id)"""
        try:
            self.cursor.execute("""
                SELECT 
                    original_post_id,
                    MAX(id) as id,
                    MAX(date) as date,
                    MAX(text) as text,
                    MAX(tags) as tags,
                    GROUP_CONCAT(media_type) as media_types,
                    GROUP_CONCAT(media_path) as media_paths,
                    GROUP_CONCAT(file_size) as file_sizes
                FROM posts 
                WHERE text LIKE ? OR tags LIKE ? 
                GROUP BY original_post_id
                ORDER BY date DESC
            """, (f'%{query}%', f'%{query}%'))
            return self.cursor.fetchall()
        except Exception as e:
            print(f"DB Search Error: {e}")
            return []

    def get_all_posts(self, limit=500):
        """Получение всех постов (группируем медиа одного поста)"""
        try:
            self.cursor.execute("""
                SELECT 
                    original_post_id,
                    MAX(id) as id,
                    MAX(date) as date,
                    MAX(text) as text,
                    MAX(tags) as tags,
                    GROUP_CONCAT(media_type) as media_types,
                    GROUP_CONCAT(media_path) as media_paths,
                    GROUP_CONCAT(file_size) as file_sizes
                FROM posts 
                GROUP BY original_post_id
                ORDER BY date DESC 
                LIMIT ?
            """, (limit,))
            return self.cursor.fetchall()
        except Exception as e:
            print(f"DB Get All Error: {e}")
            return []

    def get_stats(self):
        """Получение статистики"""
        try:
            self.cursor.execute('SELECT COUNT(DISTINCT original_post_id) FROM posts')
            count = self.cursor.fetchone()[0]
            
            self.cursor.execute("SELECT COUNT(*) FROM posts WHERE LOWER(media_type) = 'photo'")
            photos = self.cursor.fetchone()[0]
            
            self.cursor.execute("SELECT COUNT(*) FROM posts WHERE LOWER(media_type) = 'video'")
            videos = self.cursor.fetchone()[0]
            
            return {
                'total': count,
                'photos': photos,
                'videos': videos
            }
        except Exception as e:
            print(f"DB Stats Error: {e}")
            return {'total': 0, 'photos': 0, 'videos': 0}

    def close(self):
        """Закрытие соединения"""
        try:
            if self.conn:
                self.conn.close()
                self.conn = None
                self.cursor = None
        except Exception as e:
            print(f"DB Close Error: {e}")

    def __del__(self):
        """Безопасное закрытие при удалении объекта"""
        try:
            self.close()
        except:
            pass

    # ===== МЕТОДЫ ДЛЯ РАБОТЫ СО СТАТИСТИКОЙ ПОСТОВ =====
    
    def update_post_stats(self, original_post_id, likes, comments, shares, views):
        """Обновляет статистику поста (лайки, комментарии, поделиться, просмотры)"""
        try:
            self.cursor.execute("""
                UPDATE posts 
                SET likes = ?, comments = ?, shares = ?, views = ?, last_stats_update = CURRENT_TIMESTAMP
                WHERE original_post_id = ?
            """, (likes, comments, shares, views, original_post_id))
            self.conn.commit()
            return True
        except Exception as e:
            print(f"DB Update Stats Error: {e}")
            return False

    def get_post_stats(self, original_post_id):
        """Получает статистику поста"""
        try:
            self.cursor.execute("""
                SELECT likes, comments, shares, views, date 
                FROM posts 
                WHERE original_post_id = ?
                LIMIT 1
            """, (original_post_id,))
            result = self.cursor.fetchone()
            if result:
                return {
                    'likes': result[0] or 0,
                    'comments': result[1] or 0,
                    'shares': result[2] or 0,
                    'views': result[3] or 0,
                    'date': result[4]
                }
            return None
        except Exception as e:
            print(f"DB Get Post Stats Error: {e}")
            return None

    def save_post_period_statistics(self, original_post_id, period_type, period_start, period_end, 
                                     likes, comments, shares, views, rank):
        """Сохраняет статистику поста за период"""
        try:
            self.cursor.execute("""
                INSERT INTO post_statistics 
                (original_post_id, period_type, period_start, period_end, likes, comments, shares, views, rank)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (original_post_id, period_type, period_start, period_end, 
                  likes, comments, shares, views, rank))
            self.conn.commit()
            return True
        except Exception as e:
            print(f"DB Save Post Period Stats Error: {e}")
            return False

    def get_top_posts_by_period(self, period_type, period_start, period_end, metric='likes', limit=10):
        """Получает топ постов за период по метрике"""
        try:
            metric_map = {
                'likes': 'likes',
                'comments': 'comments',
                'shares': 'shares',
                'views': 'views'
            }
            metric_col = metric_map.get(metric, 'likes')
            
            query = f"""
                SELECT ps.original_post_id, ps.{metric_col}, p.text, p.date
                FROM post_statistics ps
                JOIN posts p ON ps.original_post_id = p.original_post_id
                WHERE ps.period_type = ? AND ps.period_start = ? AND ps.period_end = ?
                GROUP BY ps.original_post_id
                ORDER BY ps.{metric_col} DESC
                LIMIT ?
            """
            self.cursor.execute(query, (period_type, period_start, period_end, limit))
            return self.cursor.fetchall()
        except Exception as e:
            print(f"DB Get Top Posts Error: {e}")
            return []

    def get_posts_by_date_range(self, start_date, end_date, media_type=None):
        """Получает посты в диапазоне дат"""
        try:
            if media_type:
                self.cursor.execute("""
                    SELECT DISTINCT original_post_id, date, text, tags, media_type
                    FROM posts
                    WHERE date >= ? AND date <= ? AND media_type = ?
                    ORDER BY date DESC
                """, (start_date, end_date, media_type))
            else:
                self.cursor.execute("""
                    SELECT DISTINCT original_post_id, date, text, tags, GROUP_CONCAT(media_type)
                    FROM posts
                    WHERE date >= ? AND date <= ?
                    GROUP BY original_post_id
                    ORDER BY date DESC
                """, (start_date, end_date))
            return self.cursor.fetchall()
        except Exception as e:
            print(f"DB Get Posts by Range Error: {e}")
            return []

    # ===== МЕТОДЫ ДЛЯ РАБОТЫ СО СТАТИСТИКОЙ ПРЕПОДАВАТЕЛЕЙ =====
    
    def save_employee_statistics(self, employee_name, period_type, period_start, period_end,
                                  mention_count, post_count, total_likes, total_views, rank):
        """Сохраняет статистику преподавателя за период"""
        try:
            self.cursor.execute("""
                INSERT INTO employee_statistics 
                (employee_name, period_type, period_start, period_end, mention_count, post_count, 
                 total_likes, total_views, rank)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (employee_name, period_type, period_start, period_end, mention_count, post_count,
                  total_likes, total_views, rank))
            self.conn.commit()
            return True
        except Exception as e:
            print(f"DB Save Employee Stats Error: {e}")
            return False

    def get_top_employees_by_period(self, period_type, period_start, period_end, metric='mention_count', limit=10):
        """Получает топ преподавателей за период по метрике"""
        try:
            metric_map = {
                'mention_count': 'mention_count',
                'post_count': 'post_count',
                'total_likes': 'total_likes',
                'total_views': 'total_views'
            }
            metric_col = metric_map.get(metric, 'mention_count')
            
            query = f"""
                SELECT employee_name, {metric_col}, post_count, mention_count, total_views
                FROM employee_statistics
                WHERE period_type = ? AND period_start = ? AND period_end = ?
                ORDER BY {metric_col} DESC
                LIMIT ?
            """
            self.cursor.execute(query, (period_type, period_start, period_end, limit))
            return self.cursor.fetchall()
        except Exception as e:
            print(f"DB Get Top Employees Error: {e}")
            return []

    def count_employee_mentions(self, employee_name, start_date=None, end_date=None):
        """Подсчитывает упоминания преподавателя в постах"""
        try:
            if start_date and end_date:
                self.cursor.execute("""
                    SELECT COUNT(DISTINCT original_post_id)
                    FROM posts
                    WHERE (text LIKE ? OR tags LIKE ?) AND date >= ? AND date <= ?
                """, (f'%{employee_name}%', f'%{employee_name}%', start_date, end_date))
            else:
                self.cursor.execute("""
                    SELECT COUNT(DISTINCT original_post_id)
                    FROM posts
                    WHERE text LIKE ? OR tags LIKE ?
                """, (f'%{employee_name}%', f'%{employee_name}%'))
            return self.cursor.fetchone()[0]
        except Exception as e:
            print(f"DB Count Employee Mentions Error: {e}")
            return 0

    # ===== МЕТОДЫ ДЛЯ РАБОТЫ СО СТАТИСТИКОЙ МЕДИА =====
    
    def save_media_statistics(self, post_id, media_key, media_type, date, 
                             likes, comments, shares, views):
        """Сохраняет статистику медиафайла"""
        try:
            self.cursor.execute("""
                INSERT OR REPLACE INTO media_statistics 
                (post_id, media_key, media_type, date, likes, comments, shares, views)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (post_id, media_key, media_type, date, likes, comments, shares, views))
            self.conn.commit()
            return True
        except Exception as e:
            print(f"DB Save Media Stats Error: {e}")
            return False

    def get_top_media_by_period(self, media_type, period_type, period_start, period_end, 
                               metric='views', limit=10):
        """Получает топ медиафайлов за период по метрике"""
        try:
            metric_map = {
                'likes': 'likes',
                'comments': 'comments',
                'shares': 'shares',
                'views': 'views'
            }
            metric_col = metric_map.get(metric, 'views')
            
            query = f"""
                SELECT media_key, media_type, {metric_col}, date
                FROM media_statistics
                WHERE media_type = ? AND date >= ? AND date <= ?
                ORDER BY {metric_col} DESC
                LIMIT ?
            """
            self.cursor.execute(query, (media_type, period_start, period_end, limit))
            return self.cursor.fetchall()
        except Exception as e:
            print(f"DB Get Top Media Error: {e}")
            return []

    def verify_post_consistency(self, original_post_id):
        """Проверяет наличие поста в БД"""
        try:
            self.cursor.execute(
                "SELECT COUNT(*) FROM posts WHERE original_post_id = ?",
                (original_post_id,)
            )
            count = self.cursor.fetchone()[0]
            return count > 0
        except Exception as e:
            print(f"DB Verify Consistency Error: {e}")
            return False