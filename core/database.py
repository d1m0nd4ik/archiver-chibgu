import sqlite3
import threading
from config.settings import DB_NAME
from core.logging_config import logger

class Database:
    """Потокобезопасная БД с нормальной структурой (посты + вложения)"""
    
    CURRENT_SCHEMA_VERSION = 4
    _schema_initialized = False
    _init_lock = threading.Lock()

    def __init__(self, db_name=DB_NAME):
        self.db_name = db_name
        self._local = threading.local()
        
        # Инициализируем схему БД
        self._init_schema()

    def _get_conn(self):
        if not hasattr(self._local, 'conn') or self._local.conn is None:
            self._local.conn = sqlite3.connect(self.db_name, check_same_thread=False)
            self._local.conn.execute("PRAGMA journal_mode=WAL")
        return self._local.conn

    def _get_cursor(self):
        return self._get_conn().cursor()

    def _init_schema(self):
        with Database._init_lock:
            if Database._schema_initialized: 
                return

            conn = self._get_conn()
            cursor = conn.cursor()
            self._create_tables(cursor)
            
            cursor.execute("CREATE TABLE IF NOT EXISTS schema_version (id INTEGER PRIMARY KEY, version INTEGER DEFAULT 1)")
            row = cursor.execute("SELECT version FROM schema_version WHERE id=1").fetchone()
            current_version = row[0] if row else 1

            # === Миграция v1/v2 -> v3: разделение таблицы постов и медиа ===
            if current_version < 3:
                logger.info("[DB] Миграция v1/v2 -> v3 (разделение таблиц)...")
                cursor.execute("CREATE TABLE IF NOT EXISTS posts_backup AS SELECT * FROM posts")
                cursor.execute("DROP TABLE IF EXISTS posts")
                cursor.execute("DROP TABLE IF EXISTS attachments")
                self._create_tables(cursor)
                
                try:
                    cursor.execute("""
                        INSERT INTO posts (original_post_id, date, text, tags, likes, comments, shares, views)
                        SELECT original_post_id, date, text, tags, likes, comments, shares, views 
                        FROM posts_backup
                    """)
                    logger.info("[DB] Данные постов успешно перенесены в новую схему.")
                except Exception as e:
                    logger.warning("[DB] Перенос данных не удался (возможно, старая схема пустая): %s", e)
                    
                cursor.execute("DROP TABLE IF EXISTS posts_backup")
                cursor.execute("INSERT OR REPLACE INTO schema_version (id, version) VALUES (1, 3)")
                conn.commit()
                current_version = 3  # Обновляем локальную переменную для следующего check

            # === Миграция v3 -> v4: добавление колонки post_count в employees ===
            if current_version < 4:
                logger.info("[DB] Миграция v3 -> v4 (добавление post_count)...")
                try:
                    cursor.execute("ALTER TABLE employees ADD COLUMN post_count INTEGER DEFAULT 0")
                except Exception as e:
                    # Колонка уже может существовать, если миграция прерывалась
                    if "duplicate column name" not in str(e).lower():
                        logger.error("[DB] Ошибка миграции v4: %s", e)
                        
                cursor.execute("INSERT OR REPLACE INTO schema_version (id, version) VALUES (1, 4)")
                conn.commit()

            Database._schema_initialized = True

    def _create_tables(self, cursor):
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS posts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                original_post_id INTEGER UNIQUE,
                date TEXT,
                text TEXT,
                tags TEXT,
                likes INTEGER DEFAULT 0,
                comments INTEGER DEFAULT 0,
                shares INTEGER DEFAULT 0,
                views INTEGER DEFAULT 0, 
                last_stats_update TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
            # === Инициализация FTS5 для быстрого поиска ===
        cursor.execute("CREATE VIRTUAL TABLE IF NOT EXISTS posts_fts USING fts5(text, tags, tokenize='unicode61')")
        
        # Синхронизируем существующие данные (одноразово при обновлении)
        cursor.execute("INSERT OR IGNORE INTO posts_fts (rowid, text, tags) SELECT id, text, tags FROM posts")
        
        # Триггеры для автоматической синхронизации
        cursor.execute("""CREATE TRIGGER IF NOT EXISTS posts_fts_insert AFTER INSERT ON posts
            BEGIN INSERT INTO posts_fts (rowid, text, tags) VALUES (new.id, new.text, new.tags); END;""")
        cursor.execute("""CREATE TRIGGER IF NOT EXISTS posts_fts_update AFTER UPDATE ON posts
            BEGIN UPDATE posts_fts SET text=new.text, tags=new.tags WHERE rowid=old.id; END;""")
        cursor.execute("""CREATE TRIGGER IF NOT EXISTS posts_fts_delete AFTER DELETE ON posts
            BEGIN DELETE FROM posts_fts WHERE rowid=old.id; END;""")
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS attachments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                original_post_id INTEGER,
                media_type TEXT,
                media_key TEXT,
                media_path TEXT,
                file_size TEXT,
                FOREIGN KEY(original_post_id) REFERENCES posts(original_post_id)
            )
        """)
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_att_post_id ON attachments(original_post_id)")

        # Остальные таблицы статистики
        cursor.execute("""CREATE TABLE IF NOT EXISTS post_statistics (
            id INTEGER PRIMARY KEY AUTOINCREMENT, post_id INTEGER, original_post_id INTEGER,
            period_type TEXT, period_start TEXT, period_end TEXT,
            likes INTEGER DEFAULT 0, comments INTEGER DEFAULT 0, shares INTEGER DEFAULT 0,
            views INTEGER DEFAULT 0, rank INTEGER, recorded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)""")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_post_stats_period ON post_statistics(period_type, period_start, period_end)")

        cursor.execute("""CREATE TABLE IF NOT EXISTS employee_statistics (
            id INTEGER PRIMARY KEY AUTOINCREMENT, employee_name TEXT, period_type TEXT,
            period_start TEXT, period_end TEXT, mention_count INTEGER DEFAULT 0,
            post_count INTEGER DEFAULT 0, total_likes INTEGER DEFAULT 0, total_views INTEGER DEFAULT 0,
            rank INTEGER, recorded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)""")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_emp_stats_name_period ON employee_statistics(employee_name, period_type, period_start)")

        cursor.execute("""CREATE TABLE IF NOT EXISTS media_statistics (
            id INTEGER PRIMARY KEY AUTOINCREMENT, post_id INTEGER, media_key TEXT,
            media_type TEXT, date TEXT, likes INTEGER DEFAULT 0, comments INTEGER DEFAULT 0,
            shares INTEGER DEFAULT 0, views INTEGER DEFAULT 0, last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP)""")
        cursor.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_media_stats_unique ON media_statistics(media_key, media_type)")

        cursor.execute("""CREATE TABLE IF NOT EXISTS employees (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            full_name TEXT UNIQUE,
            normalized_name TEXT,
            source_url TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )""")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_employees_normalized ON employees(normalized_name)")

    # === ПУБЛИЧНЫЕ МЕТОДЫ ===

    def post_exists(self, original_post_id):
        try:
            return self._get_cursor().execute("SELECT COUNT(*) FROM posts WHERE original_post_id = ?", (original_post_id,)).fetchone()[0] > 0
        except Exception: 
            return False

    def save_post(self, original_post_id, date, text, tags, likes=0, comments=0, shares=0):  # Убрали views=0
        try:
            if self.post_exists(original_post_id):
                return False
            self._get_cursor().execute("""
                INSERT INTO posts (original_post_id, date, text, tags, likes, comments, shares, last_stats_update)
                VALUES (?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            """, (original_post_id, date, text, tags, likes, comments, shares))  # Убрали views
            self._get_conn().commit()
            return True
        except Exception as e:
            logger.error(f"DB Save Post Error: {e}")
            return False

    def save_media(self, original_post_id, media_type, media_key, media_path, file_size):
        try:
            self._get_cursor().execute("""
                INSERT INTO attachments (original_post_id, media_type, media_key, media_path, file_size)
                VALUES (?, ?, ?, ?, ?)
            """, (original_post_id, media_type, media_key, media_path, file_size))
            self._get_conn().commit()
            return True
        except Exception as e:
            logger.error(f"DB Save Media Error: {e}")
            return False

    def get_all_employees(self):
        try:
            rows = self._get_cursor().execute("SELECT full_name FROM employees ORDER BY full_name ASC").fetchall()
            return [row[0] for row in rows]
        except Exception:
            return []

    def clear_employees(self):
        try:
            self._get_cursor().execute("DELETE FROM employees")
            self._get_conn().commit()
            return True
        except Exception:
            return False

    def save_employee(self, full_name, normalized_name=None, source_url=None):
        try:
            if normalized_name is None:
                normalized_name = full_name.lower().replace('ё', 'е').strip()
            self._get_cursor().execute("""
                INSERT OR IGNORE INTO employees (full_name, normalized_name, source_url)
                VALUES (?, ?, ?)
            """, (full_name, normalized_name, source_url))
            self._get_conn().commit()
            return True
        except Exception:
            return False

    def update_employees(self, employee_names, source_url=None):
        try:
            self.clear_employees()
            normalized_rows = []
            for name in employee_names:
                if not name or len(name.strip()) < 3:
                    continue
                normalized = name.lower().replace('ё', 'е').strip()
                normalized_rows.append((name.strip(), normalized, source_url))
            self._get_cursor().executemany("""
                INSERT OR IGNORE INTO employees (full_name, normalized_name, source_url)
                VALUES (?, ?, ?)
            """, normalized_rows)
            self._get_conn().commit()
            return True
        except Exception as e:
            logger.error(f"DB Update Employees Error: {e}")
            return False

    def update_employee_post_count(self, employee_id, post_count):
        try:
            self._get_cursor().execute("""
                UPDATE employees SET post_count = ? WHERE id = ?
            """, (post_count, employee_id))
            self._get_conn().commit()
            return True
        except Exception as e:
            logger.error(f"DB Update Employee Post Count Error: {e}")
            return False
        
    def get_aggregated_stats(self, start_date: str, end_date: str) -> dict:
        try:
            cursor = self._get_cursor()
            row = cursor.execute("""
                SELECT 
                    COALESCE(SUM(likes), 0), 
                    COALESCE(SUM(comments), 0), 
                    COALESCE(SUM(shares), 0),
                    COUNT(*)
                FROM posts 
                WHERE date BETWEEN ? AND ?
            """, (start_date, end_date)).fetchone()
            return {
                'total_likes': row[0], 
                'total_comments': row[1],
                'total_shares': row[2],
                # 'total_views': row[3],  ← УДАЛЕНО
                'total_posts': row[3]  # Индекс сдвинулся
            }
        except Exception as e:
            logger.error(f"[DB] Aggregation error: {e}")
            return {
                'total_likes': 0, 
                'total_comments': 0, 
                'total_shares': 0,
                # 'total_views': 0,  ← УДАЛЕНО
                'total_posts': 0
            }

    def get_employees_with_post_count(self):
        try:
            rows = self._get_cursor().execute("""
                SELECT id, full_name, post_count FROM employees ORDER BY full_name ASC
            """).fetchall()
            return [{'id': row[0], 'name': row[1], 'post_count': row[2]} for row in rows]
        except Exception:
            logger.error("[DB] Error fetching employees with post count")
            return []

    def search(self, query):
        try:
            # FTS5 поиск с подсветкой релевантности
            cursor = self._get_cursor()
            results = cursor.execute("""
                SELECT p.original_post_id, p.id, p.date, p.text, p.tags,
                    GROUP_CONCAT(a.media_type), GROUP_CONCAT(a.media_path), GROUP_CONCAT(a.file_size)
                FROM posts p
                JOIN posts_fts fts ON p.id = fts.rowid
                LEFT JOIN attachments a ON p.original_post_id = a.original_post_id
                WHERE posts_fts MATCH ?
                GROUP BY p.original_post_id
                ORDER BY p.date DESC
            """, (query,)).fetchall()
            
            if not results:
                # Fallback на LIKE, если FTS не нашёл точных совпадений
                return cursor.execute("""
                    SELECT p.original_post_id, MAX(p.id), MAX(p.date), MAX(p.text), MAX(p.tags),
                        GROUP_CONCAT(a.media_type), GROUP_CONCAT(a.media_path), GROUP_CONCAT(a.file_size)
                    FROM posts p LEFT JOIN attachments a ON p.original_post_id = a.original_post_id
                    WHERE p.text LIKE ? OR p.tags LIKE ?
                    GROUP BY p.original_post_id ORDER BY p.date DESC
                """, (f'%{query}%', f'%{query}%')).fetchall()
            return results
        except Exception: 
            return []

    def get_all_posts(self, limit=500):
        #Читает посты И вложения (JOIN)
        try:
            result = self._get_cursor().execute("""
            SELECT p.original_post_id, MAX(p.id), MAX(p.date), MAX(p.text), MAX(p.tags),
                   MAX(p.likes), MAX(p.comments), MAX(p.shares),
                   GROUP_CONCAT(a.media_type), GROUP_CONCAT(a.media_path), GROUP_CONCAT(a.file_size)
            FROM posts p LEFT JOIN attachments a ON p.original_post_id = a.original_post_id
            GROUP BY p.original_post_id ORDER BY p.date DESC LIMIT ?
            """, (limit,)).fetchall()
            
            # ОТЛАДКА: проверяем что возвращаем
            logger.debug(f"[DB] get_all_posts вернул {len(result)} постов")
            for i, row in enumerate(result[:3]):
                logger.debug(f"  Row {i}: post_id={row[0]}, media_types={row[5]}, media_paths={row[6]}")
            
            return result
        except Exception as e:
            logger.error(f"[DB] get_all_posts Error: {e}")
            import traceback
            traceback.print_exc()
            return []

    def get_stats(self):
        try:
            c = self._get_cursor()
            total = c.execute('SELECT COUNT(*) FROM posts').fetchone()[0]
            photos = c.execute("SELECT COUNT(*) FROM attachments WHERE media_type='photo'").fetchone()[0]
            videos = c.execute("SELECT COUNT(*) FROM attachments WHERE media_type='video'").fetchone()[0]
            clips = c.execute("SELECT COUNT(*) FROM attachments WHERE media_type='clip'").fetchone()[0]
            return {'total': total, 'photos': photos, 'videos': videos, 'clips': clips}
        except Exception: 
            return {'total': 0, 'photos': 0, 'videos': 0, 'clips': 0}

    def close(self):
        try:
            if hasattr(self._local, 'conn') and self._local.conn:
                self._local.conn.close()
                self._local.conn = None
        except: 
            pass

    # === СТАТИСТИКА ===
    

    
    # === СТАТИСТИКА ===
    def update_post_stats(self, original_post_id, likes, comments, shares):  # Убрали views
        try:
            self._get_cursor().execute(
                "UPDATE posts SET likes=?, comments=?, shares=?, last_stats_update=CURRENT_TIMESTAMP WHERE original_post_id=?", 
                (likes, comments, shares, original_post_id)  # Убрали views
            )
            self._get_conn().commit()
            return True
        except Exception: 
            return False

    def get_post_stats(self, original_post_id):
        try:
            res = self._get_cursor().execute(
                "SELECT likes, comments, shares, date FROM posts WHERE original_post_id=? LIMIT 1", 
                (original_post_id,)
            ).fetchone()
            return {
                'likes': res[0] or 0, 
                'comments': res[1] or 0, 
                'shares': res[2] or 0, 
                # 'views': res[3] or 0,  ← УДАЛЕНО
                'date': res[3]  # Индекс сдвинулся
            } if res else None
        except Exception: 
            return None

    def save_post_period_statistics(self, original_post_id, period_type, period_start, period_end, likes, comments, shares, views, rank):
        try:
            self._get_cursor().execute("INSERT INTO post_statistics (original_post_id, period_type, period_start, period_end, likes, comments, shares, views, rank) VALUES (?,?,?,?,?,?,?,?,?)",
                                       (original_post_id, period_type, period_start, period_end, likes, comments, shares, views, rank))
            self._get_conn().commit()
            return True
        except Exception: 
            return False

    def get_top_posts_by_period(self, period_type, period_start, period_end, metric='likes', limit=10):
        try:
            metric_map = {'likes': 'likes', 'comments': 'comments', 'shares': 'shares', 'views': 'views'}
            col = metric_map.get(metric, 'likes')
            return self._get_cursor().execute(f"""
                SELECT ps.original_post_id, ps.{col}, p.text, p.date FROM post_statistics ps
                JOIN posts p ON ps.original_post_id = p.original_post_id
                WHERE ps.period_type=? AND ps.period_start=? AND ps.period_end=?
                GROUP BY ps.original_post_id ORDER BY ps.{col} DESC LIMIT ?
            """, (period_type, period_start, period_end, limit)).fetchall()
        except Exception: 
            return []

    def get_posts_by_date_range(self, start_date, end_date, media_type=None):
        try:
            c = self._get_cursor()
            if media_type:
                return c.execute("SELECT DISTINCT p.original_post_id, p.date, p.text, p.tags, a.media_type FROM posts p LEFT JOIN attachments a ON p.original_post_id = a.original_post_id WHERE p.date >= ? AND p.date <= ? AND a.media_type = ? ORDER BY p.date DESC", (start_date, end_date, media_type)).fetchall()
            return c.execute("SELECT DISTINCT p.original_post_id, p.date, p.text, p.tags, GROUP_CONCAT(a.media_type) FROM posts p LEFT JOIN attachments a ON p.original_post_id = a.original_post_id WHERE p.date >= ? AND p.date <= ? GROUP BY p.original_post_id ORDER BY p.date DESC", (start_date, end_date)).fetchall()
        except Exception: 
            return []

    def save_employee_statistics(self, employee_name, period_type, period_start, period_end, mention_count, post_count, total_likes, total_views, rank):
        try:
            self._get_cursor().execute("INSERT INTO employee_statistics (employee_name, period_type, period_start, period_end, mention_count, post_count, total_likes, total_views, rank) VALUES (?,?,?,?,?,?,?,?,?)",
                                       (employee_name, period_type, period_start, period_end, mention_count, post_count, total_likes, total_views, rank))
            self._get_conn().commit()
            return True
        except Exception: 
            return False

    def get_top_employees_by_period(self, period_type, period_start, period_end, metric='mention_count', limit=10):
        try:
            col = {'mention_count': 'mention_count', 'post_count': 'post_count', 'total_likes': 'total_likes', 'total_views': 'total_views'}.get(metric, 'mention_count')
            return self._get_cursor().execute(f"SELECT employee_name, {col}, post_count, mention_count, total_views FROM employee_statistics WHERE period_type=? AND period_start=? AND period_end=? ORDER BY {col} DESC LIMIT ?", 
                                              (period_type, period_start, period_end, limit)).fetchall()
        except Exception: 
            return []

    def count_employee_mentions(self, employee_name, start_date=None, end_date=None):
        try:
            c = self._get_cursor()
            if start_date and end_date:
                return c.execute("SELECT COUNT(DISTINCT original_post_id) FROM posts WHERE (text LIKE ? OR tags LIKE ?) AND date >= ? AND date <= ?", (f'%{employee_name}%', f'%{employee_name}%', start_date, end_date)).fetchone()[0]
            return c.execute("SELECT COUNT(DISTINCT original_post_id) FROM posts WHERE text LIKE ? OR tags LIKE ?", (f'%{employee_name}%', f'%{employee_name}%')).fetchone()[0]
        except Exception: 
            return 0

    def save_media_statistics(self, post_id, media_key, media_type, date, likes, comments, shares, views):
        try:
            self._get_cursor().execute("INSERT OR REPLACE INTO media_statistics (post_id, media_key, media_type, date, likes, comments, shares, views) VALUES (?,?,?,?,?,?,?,?)",
                                       (post_id, media_key, media_type, date, likes, comments, shares, views))
            self._get_conn().commit()
            return True
        except Exception: 
            return False

    def get_top_media_by_period(self, media_type, period_type, period_start, period_end, metric='views', limit=10):
        try:
            col = {'likes': 'likes', 'comments': 'comments', 'shares': 'shares', 'views': 'views'}.get(metric, 'views')
            return self._get_cursor().execute(f"SELECT media_key, media_type, {col}, date FROM media_statistics WHERE media_type=? AND date >= ? AND date <= ? ORDER BY {col} DESC LIMIT ?", 
                                              (media_type, period_start, period_end, limit)).fetchall()
        except Exception: 
            return []

    def verify_post_consistency(self, original_post_id):
        try:
            return self._get_cursor().execute("SELECT COUNT(*) FROM posts WHERE original_post_id = ?", (original_post_id,)).fetchone()[0] > 0
        except Exception: 
            return False