import datetime
import sqlite3
import threading
import time
from config.settings import DB_NAME
from core.logging_config import logger

_MAX_DB_RETRIES = 8
_RETRY_BASE_DELAY = 0.15
_UNSET = object()


class Database:
    CURRENT_SCHEMA_VERSION = 10
    _schema_ready: set[str] = set()
    _init_lock = threading.Lock()
    _instances = {}
    _instances_lock = threading.Lock()
    _write_lock = threading.RLock()

    def __new__(cls, db_name=DB_NAME):
        with cls._instances_lock:
            if db_name not in cls._instances:
                inst = super().__new__(cls)
                inst._singleton_ready = False
                cls._instances[db_name] = inst
            return cls._instances[db_name]

    def __init__(self, db_name=DB_NAME):
        if getattr(self, "_singleton_ready", False):
            return
        self.db_name = db_name
        self._local = threading.local()
        self._singleton_ready = True
        self._init_schema()

    def _get_conn(self):
        if not hasattr(self._local, 'conn') or self._local.conn is None:
            # ⏱ Timeout: 10 секунд (баланс между ожиданием и отзывчивостью UI)
            self._local.conn = sqlite3.connect(
                self.db_name,
                check_same_thread=False,
                timeout=30.0,
            )
            self._local.conn.execute("PRAGMA journal_mode=WAL")
            self._local.conn.execute("PRAGMA busy_timeout=30000")
            self._local.conn.execute("PRAGMA synchronous=NORMAL")
            self._local.conn.execute("PRAGMA cache_size=-64000")
            self._local.conn.execute("PRAGMA temp_store=MEMORY")
            self._local.conn.execute("PRAGMA wal_autocheckpoint=1000")

        return self._local.conn

    @staticmethod
    def _is_locked_error(exc):
        return isinstance(exc, sqlite3.OperationalError) and "locked" in str(exc).lower()

    def _run_write(self, fn, op_name="DB write"):
        last_err = None
        for attempt in range(_MAX_DB_RETRIES):
            try:
                with Database._write_lock:
                    return fn()
            except sqlite3.OperationalError as e:
                last_err = e
                if self._is_locked_error(e) and attempt < _MAX_DB_RETRIES - 1:
                    delay = min(_RETRY_BASE_DELAY * (2 ** attempt), 2.0)
                    logger.warning(
                        "[DB] %s: блокировка (попытка %s/%s), ждём %.2fс...",
                        op_name, attempt + 1, _MAX_DB_RETRIES, delay,
                    )
                    time.sleep(delay)
                else:
                    raise
        if last_err:
            raise last_err
        return None

    def _get_cursor(self):
        return self._get_conn().cursor()

    def _init_schema(self):
        with Database._init_lock:
            if self.db_name in Database._schema_ready:
                return

            conn = self._get_conn()
            cursor = conn.cursor()
            self._create_base_tables(cursor)
            self._ensure_schema_columns(cursor)
            self._ensure_fts_and_triggers(cursor)
            self._apply_schema_migrations(cursor)
            self._ensure_posts_indexes(cursor)
            if not cursor.execute(
                "SELECT 1 FROM sqlite_master WHERE type='table' AND name='posts'"
            ).fetchone():
                logger.error("Таблица posts отсутствует после инициализации — повторное создание")
                self._create_base_tables(cursor)
                self._ensure_schema_columns(cursor)
                self._ensure_fts_and_triggers(cursor)
            conn.commit()

            Database._schema_ready.add(self.db_name)

    def _create_base_tables(self, cursor):
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
                last_stats_update TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                post_url TEXT,
                author_employee_id INTEGER,
                author_department_id INTEGER,
                teacher_hashtag TEXT,
                department_hashtag TEXT,
                post_source TEXT DEFAULT 'vk',
                source_label TEXT,
                importance INTEGER DEFAULT 0
            )
        """)

        # attachments — медиафайлы
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

        cursor.execute("""CREATE TABLE IF NOT EXISTS post_statistics (
            id INTEGER PRIMARY KEY AUTOINCREMENT, post_id INTEGER, original_post_id INTEGER,
            period_type TEXT, period_start TEXT, period_end TEXT,
            likes INTEGER DEFAULT 0, comments INTEGER DEFAULT 0, shares INTEGER DEFAULT 0,
            rank INTEGER, recorded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)""")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_post_stats_period ON post_statistics(period_type, period_start, period_end)")

        cursor.execute("""CREATE TABLE IF NOT EXISTS employee_statistics (
            id INTEGER PRIMARY KEY AUTOINCREMENT, employee_name TEXT, period_type TEXT,
            period_start TEXT, period_end TEXT, mention_count INTEGER DEFAULT 0,
            post_count INTEGER DEFAULT 0, total_likes INTEGER DEFAULT 0,
            rank INTEGER, recorded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)""")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_emp_stats_name_period ON employee_statistics(employee_name, period_type, period_start)")

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS departments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE NOT NULL,
                hashtag TEXT UNIQUE,
                url TEXT,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )""")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_departments_hashtag ON departments(hashtag)")

        cursor.execute("""CREATE TABLE IF NOT EXISTS employees (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            full_name TEXT UNIQUE,
            normalized_name TEXT,
            surname TEXT,
            firstname TEXT,
            patronymic TEXT,
            hashtag TEXT UNIQUE,
            department_id INTEGER,
            source_url TEXT,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(department_id) REFERENCES departments(id)
        )""")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_employees_normalized ON employees(normalized_name)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_employees_hashtag ON employees(hashtag)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_employees_department ON employees(department_id)")

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS tag_dictionary (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                category TEXT NOT NULL,
                phrase TEXT NOT NULL,
                hashtag TEXT NOT NULL,
                weight INTEGER DEFAULT 100,
                active INTEGER DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(category, phrase)
            )
        """)
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_tag_dict_category ON tag_dictionary(category)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_tag_dict_active ON tag_dictionary(active)")

    def _ensure_fts_and_triggers(self, cursor):
        """FTS и триггеры — после всех колонок posts (в т.ч. source_label)."""
        cursor.execute(
            "CREATE VIRTUAL TABLE IF NOT EXISTS posts_fts "
            "USING fts5(text, tags, source_label, tokenize='unicode61')"
        )
        for trig in ("posts_fts_insert", "posts_fts_update", "posts_fts_delete"):
            cursor.execute(f"DROP TRIGGER IF EXISTS {trig}")
        cursor.execute("""CREATE TRIGGER posts_fts_insert AFTER INSERT ON posts
            BEGIN INSERT INTO posts_fts (rowid, text, tags, source_label)
            VALUES (new.id, new.text, new.tags, COALESCE(new.source_label, '')); END;""")
        cursor.execute("""CREATE TRIGGER posts_fts_update AFTER UPDATE ON posts
            BEGIN UPDATE posts_fts SET text=new.text, tags=new.tags,
            source_label=COALESCE(new.source_label, '') WHERE rowid=old.id; END;""")
        cursor.execute("""CREATE TRIGGER posts_fts_delete AFTER DELETE ON posts
            BEGIN DELETE FROM posts_fts WHERE rowid=old.id; END;""")

    def _ensure_schema_columns(self, cursor):
        try:
            employees_columns = {row[1] for row in cursor.execute('PRAGMA table_info(employees)').fetchall()}
            if 'surname' not in employees_columns:
                cursor.execute('ALTER TABLE employees ADD COLUMN surname TEXT')
            if 'firstname' not in employees_columns:
                cursor.execute('ALTER TABLE employees ADD COLUMN firstname TEXT')
            if 'patronymic' not in employees_columns:
                cursor.execute('ALTER TABLE employees ADD COLUMN patronymic TEXT')
            if 'hashtag' not in employees_columns:
                cursor.execute('ALTER TABLE employees ADD COLUMN hashtag TEXT')
            if 'department_id' not in employees_columns:
                cursor.execute('ALTER TABLE employees ADD COLUMN department_id INTEGER')
            if 'updated_at' not in employees_columns:
                cursor.execute('ALTER TABLE employees ADD COLUMN updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP')

            posts_columns = {row[1] for row in cursor.execute('PRAGMA table_info(posts)').fetchall()}
            if 'post_url' not in posts_columns:
                cursor.execute('ALTER TABLE posts ADD COLUMN post_url TEXT')
            if 'author_employee_id' not in posts_columns:
                cursor.execute('ALTER TABLE posts ADD COLUMN author_employee_id INTEGER')
            if 'author_department_id' not in posts_columns:
                cursor.execute('ALTER TABLE posts ADD COLUMN author_department_id INTEGER')
            if 'teacher_hashtag' not in posts_columns:
                cursor.execute('ALTER TABLE posts ADD COLUMN teacher_hashtag TEXT')
            if 'department_hashtag' not in posts_columns:
                cursor.execute('ALTER TABLE posts ADD COLUMN department_hashtag TEXT')
            if 'post_source' not in posts_columns:
                cursor.execute("ALTER TABLE posts ADD COLUMN post_source TEXT DEFAULT 'vk'")
            if 'source_label' not in posts_columns:
                cursor.execute('ALTER TABLE posts ADD COLUMN source_label TEXT')
            if 'importance' not in posts_columns:
                cursor.execute('ALTER TABLE posts ADD COLUMN importance INTEGER DEFAULT 0')

            tag_columns = {row[1] for row in cursor.execute('PRAGMA table_info(tag_dictionary)').fetchall()}
            if 'parent_hashtag' not in tag_columns:
                cursor.execute('ALTER TABLE tag_dictionary ADD COLUMN parent_hashtag TEXT')

        except Exception as e:
            logger.warning("_ensure_schema_columns: %s", e)

    def _apply_schema_migrations(self, cursor):
        try:
            ver = int(cursor.execute("PRAGMA user_version").fetchone()[0] or 0)
            if ver < 10:
                self._migrate_schema_v10(cursor)
                cursor.execute("PRAGMA user_version = 10")
        except Exception as e:
            logger.warning("_apply_schema_migrations: %s", e)

    def _migrate_schema_v10(self, cursor):
        if not cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='posts'"
        ).fetchone():
            logger.warning("migrate v10: таблица posts отсутствует, пропуск FTS")
            return
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_posts_date ON posts(date)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_posts_post_source ON posts(post_source)")
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_posts_author_department ON posts(author_department_id)"
        )
        for trig in ("posts_fts_insert", "posts_fts_update", "posts_fts_delete"):
            cursor.execute(f"DROP TRIGGER IF EXISTS {trig}")
        cursor.execute("DROP TABLE IF EXISTS posts_fts")
        cursor.execute(
            "CREATE VIRTUAL TABLE posts_fts "
            "USING fts5(text, tags, source_label, tokenize='unicode61')"
        )
        cursor.execute("""
            INSERT INTO posts_fts(rowid, text, tags, source_label)
            SELECT id, COALESCE(text,''), COALESCE(tags,''),
                   COALESCE(source_label,'') FROM posts
        """)
        cursor.execute("""CREATE TRIGGER posts_fts_insert AFTER INSERT ON posts
            BEGIN INSERT INTO posts_fts (rowid, text, tags, source_label)
            VALUES (new.id, new.text, new.tags, COALESCE(new.source_label, '')); END;""")
        cursor.execute("""CREATE TRIGGER posts_fts_update AFTER UPDATE ON posts
            BEGIN UPDATE posts_fts SET text=new.text, tags=new.tags,
            source_label=COALESCE(new.source_label, '') WHERE rowid=old.id; END;""")
        cursor.execute("""CREATE TRIGGER posts_fts_delete AFTER DELETE ON posts
            BEGIN DELETE FROM posts_fts WHERE rowid=old.id; END;""")
        try:
            cursor.execute("ANALYZE")
        except Exception:
            pass
        logger.info("Schema migrated to v10 (FTS source_label, indexes)")

    @staticmethod
    def _ensure_posts_indexes(cursor):
        try:
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_posts_date ON posts(date)")
            cursor.execute(
                "CREATE INDEX IF NOT EXISTS idx_posts_post_source ON posts(post_source)"
            )
            cursor.execute(
                "CREATE INDEX IF NOT EXISTS idx_posts_author_department "
                "ON posts(author_department_id)"
            )
        except Exception as e:
            logger.warning("_ensure_posts_indexes: %s", e)

    # === ПУБЛИЧНЫЕ МЕТОДЫ ===

    def post_exists(self, original_post_id):
        try:
            return self._get_cursor().execute("SELECT COUNT(*) FROM posts WHERE original_post_id = ?", (original_post_id,)).fetchone()[0] > 0
        except Exception: 
            return False

    def get_all_original_post_ids(self):
        try:
            rows = self._get_cursor().execute(
                "SELECT original_post_id FROM posts WHERE original_post_id IS NOT NULL"
            ).fetchall()
            return {int(row[0]) for row in rows if row[0] is not None}
        except Exception as e:
            logger.error("get_all_original_post_ids: %s", e)
            return set()

    def get_vk_original_post_ids(self):
        """ID постов из ВК (для обновления статистики со стены)."""
        try:
            rows = self._get_cursor().execute("""
                SELECT original_post_id FROM posts
                WHERE original_post_id IS NOT NULL
                  AND original_post_id > 0
                  AND COALESCE(post_source, 'vk') = 'vk'
            """).fetchall()
            return {int(row[0]) for row in rows if row[0] is not None}
        except Exception as e:
            logger.error("get_vk_original_post_ids: %s", e)
            return set()

    def allocate_manual_post_id(self) -> int | None:
        """Отрицательные ID для материалов не из ВК."""
        try:
            def _write():
                row = self._get_cursor().execute(
                    "SELECT MIN(original_post_id) FROM posts WHERE original_post_id < 0"
                ).fetchone()
                if row and row[0] is not None:
                    return int(row[0]) - 1
                return -1

            return self._run_write(_write, "allocate_manual_post_id")
        except Exception as e:
            logger.error("allocate_manual_post_id: %s", e)
            return None

    def recalculate_posts_importance(self) -> int:
        """Пересчитывает актуальность всех постов по дате публикации и сегодняшнему дню."""
        from core.post_importance import compute_importance_from_date

        try:
            def _write():
                cur = self._get_cursor()
                rows = cur.execute(
                    "SELECT original_post_id, date FROM posts"
                ).fetchall()
                updated = 0
                for oid, date_str in rows:
                    level = compute_importance_from_date(date_str)
                    cur.execute(
                        "UPDATE posts SET importance = ? WHERE original_post_id = ?",
                        (level, oid),
                    )
                    if cur.rowcount:
                        updated += 1
                self._get_conn().commit()
                return updated

            return self._run_write(_write, "recalculate_posts_importance") or 0
        except Exception as e:
            logger.error("recalculate_posts_importance: %s", e)
            return 0

    def save_post(self, original_post_id, date, text, tags, likes=0, comments=0, shares=0,
                  post_url=None, author_employee_id=None, author_department_id=None,
                  teacher_hashtag=None, department_hashtag=None,
                  post_source='vk', source_label=None, importance=None):
        try:
            if self.post_exists(original_post_id):
                return False

            from core.post_importance import compute_importance_from_date
            if importance is None:
                importance = compute_importance_from_date(date)

            def _write():
                self._get_cursor().execute("""
                    INSERT INTO posts (original_post_id, date, text, tags, likes, comments, shares,
                                       post_url, author_employee_id, author_department_id,
                                       teacher_hashtag, department_hashtag,
                                       post_source, source_label, importance, last_stats_update)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                """, (
                    original_post_id, date, text, tags, likes, comments, shares,
                    post_url, author_employee_id, author_department_id,
                    teacher_hashtag, department_hashtag,
                    (post_source or 'vk'), source_label, int(importance),
                ))
                self._get_conn().commit()
                return True

            return self._run_write(_write, "save_post")
        except Exception as e:
            logger.error(f"DB Save Post Error: {e}")
            return False

    def get_post_by_original_id(self, original_post_id: int) -> dict | None:
        try:
            row = self._get_cursor().execute("""
                SELECT original_post_id, date, text, tags, likes, comments, shares,
                       post_url, author_employee_id, author_department_id,
                       teacher_hashtag, department_hashtag, post_source, source_label, importance
                FROM posts WHERE original_post_id = ? LIMIT 1
            """, (int(original_post_id),)).fetchone()
            if not row:
                return None
            return {
                'original_post_id': row[0],
                'date': row[1],
                'text': row[2],
                'tags': row[3],
                'likes': row[4],
                'comments': row[5],
                'shares': row[6],
                'post_url': row[7],
                'author_employee_id': row[8],
                'author_department_id': row[9],
                'teacher_hashtag': row[10],
                'department_hashtag': row[11],
                'post_source': row[12] or 'vk',
                'source_label': row[13],
                'importance': row[14] if row[14] is not None else 0,
            }
        except Exception as e:
            logger.error("get_post_by_original_id: %s", e)
            return None

    def update_post(
        self,
        original_post_id: int,
        *,
        date: str | None = _UNSET,
        text: str | None = _UNSET,
        tags: str | None = _UNSET,
        source_label: str | None = _UNSET,
        teacher_hashtag: str | None = _UNSET,
        department_hashtag: str | None = _UNSET,
        author_employee_id: int | None = _UNSET,
        author_department_id: int | None = _UNSET,
        likes: int | None = _UNSET,
        comments: int | None = _UNSET,
        shares: int | None = _UNSET,
        post_url: str | None = _UNSET,
    ) -> bool:
        fields = []
        params = []
        mapping = {
            'date': date,
            'text': text,
            'tags': tags,
            'source_label': source_label,
            'teacher_hashtag': teacher_hashtag,
            'department_hashtag': department_hashtag,
            'author_employee_id': author_employee_id,
            'author_department_id': author_department_id,
            'likes': likes,
            'comments': comments,
            'shares': shares,
            'post_url': post_url,
        }
        for col, val in mapping.items():
            if val is _UNSET:
                continue
            fields.append(f"{col} = ?")
            params.append(val)
        if date is not _UNSET and date is not None:
            from core.post_importance import compute_importance_from_date
            fields.append("importance = ?")
            params.append(compute_importance_from_date(date))
        if not fields:
            return True
        try:
            def _write():
                params.append(int(original_post_id))
                self._get_cursor().execute(
                    f"UPDATE posts SET {', '.join(fields)} WHERE original_post_id = ?",
                    tuple(params),
                )
                self._get_conn().commit()
                return True

            return self._run_write(_write, "update_post")
        except Exception as e:
            logger.error("update_post: %s", e)
            return False

    def delete_post(self, original_post_id: int, remove_files: bool = True) -> bool:
        try:
            paths = []
            if remove_files:
                rows = self._get_cursor().execute(
                    "SELECT media_path FROM attachments WHERE original_post_id = ?",
                    (int(original_post_id),),
                ).fetchall()
                paths = [r[0] for r in rows if r and r[0]]

            def _write():
                oid = int(original_post_id)
                self._get_cursor().execute(
                    "DELETE FROM attachments WHERE original_post_id = ?", (oid,)
                )
                self._get_cursor().execute(
                    "DELETE FROM posts WHERE original_post_id = ?", (oid,)
                )
                self._get_conn().commit()
                return True

            ok = self._run_write(_write, "delete_post")
            if ok and remove_files:
                import os
                for path in paths:
                    try:
                        if path and os.path.isfile(path):
                            os.remove(path)
                    except OSError as e:
                        logger.warning("delete_post file %s: %s", path, e)
            return ok
        except Exception as e:
            logger.error("delete_post: %s", e)
            return False

    def list_posts_admin(
        self,
        *,
        source: str | None = None,
        importance: int | None = None,
        search: str = "",
        limit: int = 500,
        offset: int = 0,
    ) -> list[dict]:
        try:
            clauses = []
            params: list = []
            if source == "vk":
                clauses.append("COALESCE(post_source, 'vk') = 'vk'")
            elif source == "manual":
                clauses.append("COALESCE(post_source, 'vk') = 'manual'")
            if importance is not None:
                clauses.append("COALESCE(importance, 0) = ?")
                params.append(int(importance))
            q = (search or "").strip()
            if q:
                clauses.append("(text LIKE ? OR tags LIKE ? OR COALESCE(source_label, '') LIKE ?)")
                like = f"%{q}%"
                params.extend([like, like, like])
            where = (" WHERE " + " AND ".join(clauses)) if clauses else ""
            params.extend([max(1, int(limit)), max(0, int(offset))])
            rows = self._get_cursor().execute(f"""
                SELECT original_post_id, date, text, tags, COALESCE(post_source, 'vk'),
                       COALESCE(source_label, ''), COALESCE(importance, 0),
                       likes, comments, shares
                FROM posts
                {where}
                ORDER BY date DESC
                LIMIT ? OFFSET ?
            """, tuple(params)).fetchall()
            return [
                {
                    'original_post_id': r[0],
                    'date': r[1],
                    'text': r[2] or '',
                    'tags': r[3] or '',
                    'post_source': r[4],
                    'source_label': r[5],
                    'importance': r[6],
                    'likes': r[7],
                    'comments': r[8],
                    'shares': r[9],
                }
                for r in rows
            ]
        except Exception as e:
            logger.error("list_posts_admin: %s", e)
            return []

    def save_media(self, original_post_id, media_type, media_key, media_path, file_size):
        try:
            def _write():
                self._get_cursor().execute("""
                    INSERT INTO attachments (original_post_id, media_type, media_key, media_path, file_size)
                    VALUES (?, ?, ?, ?, ?)
                """, (original_post_id, media_type, media_key, media_path, file_size))
                self._get_conn().commit()
                return True

            return self._run_write(_write, "save_media")
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
            def _write():
                self._get_cursor().execute("DELETE FROM employees")
                self._get_conn().commit()
                return True

            return self._run_write(_write, "clear_employees")
        except Exception:
            return False

    def save_employee(self, full_name, normalized_name=None, surname=None, firstname=None,
                      patronymic=None, hashtag=None, department_id=None, source_url=None):
        try:
            if normalized_name is None:
                normalized_name = full_name.lower().replace('ё', 'е').strip()

            def _write():
                self._get_cursor().execute("""
                    INSERT OR IGNORE INTO employees (
                        full_name, normalized_name, surname, firstname, patronymic,
                        hashtag, department_id, source_url, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                """, (
                    full_name, normalized_name, surname, firstname,
                    patronymic, hashtag, department_id, source_url))
                self._get_conn().commit()
                return True

            return self._run_write(_write, "save_employee")
        except Exception as e:
            logger.error(f"DB Save Employee Error: {e}")
            return False

    def update_employees(self, employee_names, source_url=None):
        """Обновляет список сотрудников одной транзакцией."""
        normalized_rows = []
        for name in employee_names:
            if not name or len(name.strip()) < 3:
                continue
            normalized = name.lower().replace('ё', 'е').strip()
            normalized_rows.append((name.strip(), normalized, source_url))

        if not normalized_rows:
            logger.warning("update_employees: пустой список — существующие записи не удаляются")
            return False

        try:
            def _write():
                conn = self._get_conn()
                conn.execute("BEGIN IMMEDIATE")
                try:
                    conn.execute("DELETE FROM employees")
                    if normalized_rows:
                        conn.executemany(
                            """
                            INSERT OR IGNORE INTO employees (full_name, normalized_name, source_url)
                            VALUES (?, ?, ?)
                            """,
                            normalized_rows,
                        )
                    conn.commit()
                except Exception:
                    conn.rollback()
                    raise
                return True

            return self._run_write(_write, "update_employees")
        except Exception as e:
            logger.error(f"DB Update Employees Error: {e}")
            return False

    def get_department_by_hashtag(self, hashtag):
        try:
            tag = (hashtag or '').strip()
            if tag and not tag.startswith('#'):
                tag = f"#{tag}"
            norm = tag.lower().replace('ё', 'е')
            row = self._get_cursor().execute(
                """
                SELECT id, name, hashtag, url FROM departments
                WHERE lower(replace(hashtag, 'ё', 'е')) = ?
                LIMIT 1
                """,
                (norm,),
            ).fetchone()
            return {'id': row[0], 'name': row[1], 'hashtag': row[2], 'url': row[3]} if row else None
        except Exception:
            return None

    def get_department_by_name(self, name):
        try:
            row = self._get_cursor().execute(
                "SELECT id, name, hashtag, url FROM departments WHERE name = ? LIMIT 1", (name,)
            ).fetchone()
            return {'id': row[0], 'name': row[1], 'hashtag': row[2], 'url': row[3]} if row else None
        except Exception:
            return None

    def get_department_by_id(self, department_id):
        try:
            row = self._get_cursor().execute(
                "SELECT id, name, hashtag, url FROM departments WHERE id = ? LIMIT 1", (department_id,)
            ).fetchone()
            return {'id': row[0], 'name': row[1], 'hashtag': row[2], 'url': row[3]} if row else None
        except Exception:
            return None

    def get_departments(self):
        try:
            rows = self._get_cursor().execute(
                "SELECT id, name, hashtag, url FROM departments ORDER BY name COLLATE NOCASE ASC"
            ).fetchall()
            return [{'id': row[0], 'name': row[1], 'hashtag': row[2], 'url': row[3]} for row in rows]
        except Exception:
            return []

    def upsert_department(self, name, hashtag=None, url=None):
        try:
            existing = self.get_department_by_name(name)
            if existing:
                if hashtag and hashtag != existing.get('hashtag'):
                    self._get_cursor().execute(
                        "UPDATE departments SET hashtag = ?, url = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                        (hashtag, url, existing['id'])
                    )
                    self._get_conn().commit()
                return existing

            self._get_cursor().execute(
                "INSERT INTO departments (name, hashtag, url) VALUES (?, ?, ?)",
                (name, hashtag, url)
            )
            self._get_conn().commit()
            return self.get_department_by_name(name)
        except Exception as e:
            logger.error(f"DB Upsert Department Error: {e}")
            return None

    def get_employee_by_hashtag(self, hashtag):
        try:
            row = self._get_cursor().execute(
                "SELECT e.id, e.full_name, e.surname, e.firstname, e.patronymic, e.hashtag, e.department_id, d.name, d.hashtag FROM employees e LEFT JOIN departments d ON e.department_id = d.id WHERE e.hashtag = ? LIMIT 1",
                (hashtag,)
            ).fetchone()
            if not row:
                return None
            return {
                'id': row[0], 'full_name': row[1], 'surname': row[2], 'firstname': row[3],
                'patronymic': row[4], 'hashtag': row[5], 'department_id': row[6],
                'department_name': row[7], 'department_hashtag': row[8]
            }
        except Exception:
            return None

    def get_employee_by_normalized_name(self, normalized_name):
        try:
            row = self._get_cursor().execute(
                "SELECT id, full_name, surname, firstname, patronymic, hashtag, department_id FROM employees WHERE normalized_name = ? LIMIT 1",
                (normalized_name,)
            ).fetchone()
            if not row:
                return None
            return {
                'id': row[0], 'full_name': row[1], 'surname': row[2], 'firstname': row[3],
                'patronymic': row[4], 'hashtag': row[5], 'department_id': row[6]
            }
        except Exception:
            return None

    def get_employee_by_id(self, employee_id):
        try:
            row = self._get_cursor().execute(
                "SELECT e.id, e.full_name, e.surname, e.firstname, e.patronymic, e.hashtag, e.department_id, d.name, d.hashtag FROM employees e LEFT JOIN departments d ON e.department_id = d.id WHERE e.id = ? LIMIT 1",
                (employee_id,)
            ).fetchone()
            if not row:
                return None
            return {
                'id': row[0], 'full_name': row[1], 'surname': row[2], 'firstname': row[3],
                'patronymic': row[4], 'hashtag': row[5], 'department_id': row[6],
                'department_name': row[7], 'department_hashtag': row[8]
            }
        except Exception:
            return None

    def get_employees_by_department_id(self, department_id):
        try:
            rows = self._get_cursor().execute(
                "SELECT id, full_name, surname, firstname, patronymic, hashtag, department_id, source_url FROM employees WHERE department_id = ? ORDER BY full_name COLLATE NOCASE ASC",
                (department_id,)
            ).fetchall()
            return [
                {
                    'id': row[0], 'full_name': row[1], 'surname': row[2], 'firstname': row[3],
                    'patronymic': row[4], 'hashtag': row[5], 'department_id': row[6], 'source_url': row[7]
                }
                for row in rows
            ]
        except Exception:
            return []

    def update_employee(self, employee_id, hashtag=None, department_id=None, source_url=None):
        try:
            update_fields = []
            values = []
            if hashtag is not None:
                update_fields.append('hashtag = ?')
                values.append(hashtag)
            if department_id is not None:
                update_fields.append('department_id = ?')
                values.append(department_id)
            if source_url is not None:
                update_fields.append('source_url = ?')
                values.append(source_url)
            if not update_fields:
                return False
            values.append(employee_id)
            self._get_cursor().execute(
                f"UPDATE employees SET {', '.join(update_fields)}, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                tuple(values)
            )
            self._get_conn().commit()
            return True
        except Exception as e:
            logger.error(f"DB Update Employee Error: {e}")
            return False

    def get_all_employee_details(self):
        try:
            rows = self._get_cursor().execute("""
                SELECT e.id, e.full_name, e.surname, e.firstname, e.patronymic, e.hashtag,
                       e.department_id, e.source_url, d.name, d.hashtag
                FROM employees e
                LEFT JOIN departments d ON e.department_id = d.id
                ORDER BY e.full_name COLLATE NOCASE ASC
            """).fetchall()
            return [
                {
                    'id': row[0], 'full_name': row[1], 'surname': row[2], 'firstname': row[3],
                    'patronymic': row[4], 'hashtag': row[5], 'department_id': row[6],
                    'source_url': row[7], 'department_name': row[8], 'department_hashtag': row[9]
                }
                for row in rows
            ]
        except Exception:
            return []

    def upsert_employee(self, full_name, normalized_name=None, surname=None, firstname=None,
                        patronymic=None, hashtag=None, department_id=None, source_url=None):
        try:
            if normalized_name is None:
                normalized_name = full_name.lower().replace('ё', 'е').strip()
            existing = self._get_cursor().execute(
                "SELECT id, hashtag, department_id FROM employees WHERE normalized_name = ? LIMIT 1",
                (normalized_name,)
            ).fetchone()
            if existing:
                emp_id, existing_hashtag, existing_department_id = existing
                update_fields = []
                update_values = []
                if hashtag and hashtag != existing_hashtag:
                    update_fields.append('hashtag = ?')
                    update_values.append(hashtag)
                if department_id and department_id != existing_department_id:
                    update_fields.append('department_id = ?')
                    update_values.append(department_id)
                if source_url:
                    update_fields.append('source_url = ?')
                    update_values.append(source_url)
                if update_fields:
                    update_values.extend([emp_id])
                    self._get_cursor().execute(
                        f"UPDATE employees SET {', '.join(update_fields)}, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                        tuple(update_values)
                    )
                    self._get_conn().commit()
                return self.get_employee_by_id(emp_id)

            self._get_cursor().execute("""
                INSERT INTO employees (
                    full_name, normalized_name, surname, firstname, patronymic,
                    hashtag, department_id, source_url, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            """, (
                full_name, normalized_name, surname, firstname, patronymic,
                hashtag, department_id, source_url
            ))
            self._get_conn().commit()
            return self.get_employee_by_hashtag(hashtag) if hashtag else self._get_cursor().execute(
                "SELECT id, full_name, surname, firstname, patronymic, hashtag, department_id FROM employees WHERE normalized_name = ? LIMIT 1",
                (normalized_name,)
            ).fetchone()
        except Exception as e:
            logger.error(f"DB Upsert Employee Error: {e}")
            return None

    def update_employee_hashtag(self, employee_id, hashtag):
        try:
            self._get_cursor().execute(
                "UPDATE employees SET hashtag = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                (hashtag, employee_id)
            )
            self._get_conn().commit()
            return True
        except Exception as e:
            logger.error(f"DB Update Employee Hashtag Error: {e}")
            return False

    def delete_employee(self, employee_id):
        try:
            self._get_cursor().execute("DELETE FROM employees WHERE id = ?", (employee_id,))
            self._get_conn().commit()
            return True
        except Exception as e:
            logger.error(f"DB Delete Employee Error: {e}")
            return False

    def delete_department(self, department_id):
        try:
            self._get_cursor().execute("DELETE FROM employees WHERE department_id = ?", (department_id,))
            self._get_cursor().execute("DELETE FROM departments WHERE id = ?", (department_id,))
            self._get_conn().commit()
            return True
        except Exception as e:
            logger.error(f"DB Delete Department Error: {e}")
            return False

    def delete_employees_not_in_list(self, normalized_names):
        try:
            self._get_cursor().execute(
                "DELETE FROM employees WHERE normalized_name NOT IN ({})".format(
                    ','.join('?' * len(normalized_names))
                ), tuple(normalized_names)
            )
            self._get_conn().commit()
            return True
        except Exception as e:
            logger.error(f"DB Delete Employees Not In List Error: {e}")
            return False

    def get_posts_by_employee(self, employee_id, start_date=None, end_date=None):
        try:
            query = "SELECT original_post_id, date, text, tags, likes, comments, shares FROM posts WHERE author_employee_id = ?"
            params = [employee_id]
            if start_date and end_date:
                query += " AND date >= ? AND date <= ?"
                params.extend([start_date, end_date])
            query += " ORDER BY date DESC"
            rows = self._get_cursor().execute(query, tuple(params)).fetchall()
            return [dict(original_post_id=row[0], date=row[1], text=row[2], tags=row[3], likes=row[4], comments=row[5], shares=row[6]) for row in rows]
        except Exception as e:
            logger.error(f"DB get_posts_by_employee Error: {e}")
            return []

    def get_top_employees_by_period(self, start_date, end_date, limit=20):
        try:
            rows = self._get_cursor().execute("""
                SELECT e.id, e.full_name, e.hashtag, d.name, d.hashtag,
                       COUNT(p.id) as post_count, COALESCE(SUM(p.likes),0) as total_likes
                FROM posts p
                JOIN employees e ON p.author_employee_id = e.id
                LEFT JOIN departments d ON e.department_id = d.id
                WHERE p.date >= ? AND p.date <= ?
                GROUP BY e.id ORDER BY post_count DESC, total_likes DESC LIMIT ?
            """, (start_date, end_date, limit)).fetchall()
            return [
                {'id': row[0], 'employee': row[1], 'full_name': row[1], 'hashtag': row[2], 'department_name': row[3], 'department_hashtag': row[4], 'post_count': row[5], 'total_likes': row[6]}
                for row in rows
            ]
        except Exception as e:
            logger.error(f"DB get_top_employees_by_period Error: {e}")
            return []

    def update_employee_post_count(self, employee_id, post_count):
        try:
            def _write():
                self._get_cursor().execute("""
                    UPDATE employees SET post_count = ? WHERE id = ?
                """, (post_count, employee_id))
                self._get_conn().commit()
                return True

            return self._run_write(_write, "update_employee_post_count")
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
                'total_posts': row[3]
            }
        except Exception as e:
            logger.error(f"[DB] Aggregation error: {e}")
            return {'total_likes': 0, 'total_comments': 0, 'total_shares': 0, 'total_posts': 0}

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
        """Устаревший простой поиск; для фильтров используйте search_posts_filtered."""
        from core.post_search import PostSearchParams
        rows = self.search_posts_filtered(PostSearchParams(query=query, limit=500))
        return [
            (
                r['original_post_id'], r.get('id'), r['date'], r['text'], r['tags'],
                r.get('media_types'), r.get('media_paths'), r.get('file_sizes'),
            )
            for r in rows
        ]

    def search_posts_filtered(self, params) -> list[dict]:
        """Расширенный поиск с фильтрами и сортировкой."""
        from core.post_search import PostSearchParams, SORT_OPTIONS

        if not isinstance(params, PostSearchParams):
            params = PostSearchParams(query=str(params or ''))

        try:
            clauses = []
            params_list: list = []
            join_fts = False
            q = (params.query or '').strip()

            if q:
                fts_q = q.replace('"', '""')
                if ' ' in fts_q and not fts_q.startswith('"'):
                    fts_q = f'"{fts_q}"'
                clauses.append(
                    "p.id IN (SELECT rowid FROM posts_fts WHERE posts_fts MATCH ?)"
                )
                params_list.append(fts_q)
                join_fts = True

            if params.date_from:
                clauses.append("p.date >= ?")
                params_list.append(params.date_from)
            if params.date_to:
                clauses.append("p.date <= ?")
                params_list.append(params.date_to + " 23:59" if len(params.date_to) <= 10 else params.date_to)

            if params.tag_hashtag:
                tag = (params.tag_hashtag or '').strip()
                if tag and not tag.startswith('#'):
                    tag = f'#{tag}'
                clauses.append(
                    "(p.tags LIKE ? OR p.teacher_hashtag LIKE ? OR p.department_hashtag LIKE ?)"
                )
                like = f"%{tag}%"
                params_list.extend([like, like, like])

            if params.department_id is not None:
                clauses.append(
                    "(p.author_department_id = ? OR e.department_id = ?)"
                )
                did = int(params.department_id)
                params_list.extend([did, did])

            if params.author_employee_id is not None:
                clauses.append("p.author_employee_id = ?")
                params_list.append(int(params.author_employee_id))

            if params.post_source == 'vk':
                clauses.append("COALESCE(p.post_source, 'vk') = 'vk'")
            elif params.post_source == 'manual':
                clauses.append("COALESCE(p.post_source, 'vk') = 'manual'")

            media_type = (params.media_type or '').strip().lower()
            if media_type == 'any':
                clauses.append(
                    "EXISTS (SELECT 1 FROM attachments ax WHERE ax.original_post_id = p.original_post_id)"
                )
            elif media_type == 'none':
                clauses.append(
                    "NOT EXISTS (SELECT 1 FROM attachments ax WHERE ax.original_post_id = p.original_post_id)"
                )
            elif media_type in ('photo', 'video', 'clip'):
                clauses.append(
                    "EXISTS (SELECT 1 FROM attachments ax WHERE ax.original_post_id = p.original_post_id AND ax.media_type = ?)"
                )
                params_list.append(media_type)

            where = (" WHERE " + " AND ".join(clauses)) if clauses else ""

            sort_key = params.sort if params.sort in SORT_OPTIONS else 'date_desc'
            order_map = {
                'date_desc': 'p.date DESC',
                'date_asc': 'p.date ASC',
                'likes_desc': 'p.likes DESC, p.date DESC',
                'comments_desc': 'p.comments DESC, p.date DESC',
                'shares_desc': 'p.shares DESC, p.date DESC',
                'popularity_desc': '(COALESCE(p.likes,0)+COALESCE(p.comments,0)+COALESCE(p.shares,0)) DESC, p.date DESC',
            }
            order_sql = order_map.get(sort_key, 'p.date DESC')

            limit = max(1, min(int(params.limit or 500), 2000))
            offset = max(0, int(params.offset or 0))
            params_list.extend([limit, offset])

            sql = f"""
                SELECT p.original_post_id, MAX(p.id), MAX(p.date), MAX(p.text), MAX(p.tags),
                       MAX(p.likes), MAX(p.comments), MAX(p.shares),
                       GROUP_CONCAT(DISTINCT a.media_type), GROUP_CONCAT(a.media_path), GROUP_CONCAT(a.file_size),
                       MAX(p.post_url), MAX(p.teacher_hashtag), MAX(p.department_hashtag),
                       MAX(e.full_name), MAX(d.name),
                       MAX(COALESCE(p.post_source, 'vk')), MAX(p.source_label), MAX(p.importance),
                       MAX(p.author_employee_id), MAX(p.author_department_id)
                FROM posts p
                LEFT JOIN attachments a ON p.original_post_id = a.original_post_id
                LEFT JOIN employees e ON p.author_employee_id = e.id
                LEFT JOIN departments d ON COALESCE(e.department_id, p.author_department_id) = d.id
                {where}
                GROUP BY p.original_post_id
                ORDER BY {order_sql}
                LIMIT ? OFFSET ?
            """
            rows = self._get_cursor().execute(sql, tuple(params_list)).fetchall()

            if not rows and q and join_fts:
                like = f"%{q}%"
                fallback_clauses = [
                    "(p.text LIKE ? OR p.tags LIKE ? OR COALESCE(p.source_label,'') LIKE ?)"
                ]
                fb_params = [like, like, like]
                if params.date_from:
                    fallback_clauses.append("p.date >= ?")
                    fb_params.append(params.date_from)
                if params.date_to:
                    fallback_clauses.append("p.date <= ?")
                    fb_params.append(params.date_to + " 23:59" if len(params.date_to) <= 10 else params.date_to)
                if params.post_source == 'vk':
                    fallback_clauses.append("COALESCE(p.post_source, 'vk') = 'vk'")
                elif params.post_source == 'manual':
                    fallback_clauses.append("COALESCE(p.post_source, 'vk') = 'manual'")
                fb_where = " WHERE " + " AND ".join(fallback_clauses)
                fb_params.extend([limit, offset])
                rows = self._get_cursor().execute(f"""
                    SELECT p.original_post_id, MAX(p.id), MAX(p.date), MAX(p.text), MAX(p.tags),
                           MAX(p.likes), MAX(p.comments), MAX(p.shares),
                           GROUP_CONCAT(DISTINCT a.media_type), GROUP_CONCAT(a.media_path), GROUP_CONCAT(a.file_size),
                           MAX(p.post_url), MAX(p.teacher_hashtag), MAX(p.department_hashtag),
                           MAX(e.full_name), MAX(d.name),
                           MAX(COALESCE(p.post_source, 'vk')), MAX(p.source_label), MAX(p.importance),
                           MAX(p.author_employee_id), MAX(p.author_department_id)
                    FROM posts p
                    LEFT JOIN attachments a ON p.original_post_id = a.original_post_id
                    LEFT JOIN employees e ON p.author_employee_id = e.id
                    LEFT JOIN departments d ON COALESCE(e.department_id, p.author_department_id) = d.id
                    {fb_where}
                    GROUP BY p.original_post_id
                    ORDER BY {order_sql}
                    LIMIT ? OFFSET ?
                """, tuple(fb_params)).fetchall()

            result = []
            for r in rows:
                result.append({
                    'original_post_id': r[0],
                    'id': r[1],
                    'date': r[2],
                    'text': r[3] or '',
                    'tags': r[4] or '',
                    'likes': r[5] or 0,
                    'comments': r[6] or 0,
                    'shares': r[7] or 0,
                    'media_types': r[8] or '',
                    'media_paths': r[9] or '',
                    'file_sizes': r[10] or '',
                    'post_url': r[11],
                    'teacher_hashtag': r[12],
                    'department_hashtag': r[13],
                    'author_name': r[14],
                    'department_name': r[15],
                    'post_source': r[16] or 'vk',
                    'source_label': r[17],
                    'importance': r[18] if r[18] is not None else 0,
                    'author_employee_id': r[19],
                    'author_department_id': r[20],
                })
            return result
        except Exception as e:
            logger.error("search_posts_filtered: %s", e, exc_info=True)
            return []

    def count_posts_filtered(self, params) -> int:
        """Число постов по тем же фильтрам, что и search_posts_filtered."""
        from core.post_search import PostSearchParams

        if not isinstance(params, PostSearchParams):
            params = PostSearchParams(query=str(params or ''))
        try:
            clauses, params_list, _q, _join_fts = self._build_search_clauses(params)
            where = (" WHERE " + " AND ".join(clauses)) if clauses else ""
            sql = f"""
                SELECT COUNT(DISTINCT p.original_post_id)
                FROM posts p
                LEFT JOIN employees e ON p.author_employee_id = e.id
                {where}
            """
            row = self._get_cursor().execute(sql, tuple(params_list)).fetchone()
            return int(row[0] or 0) if row else 0
        except Exception as e:
            logger.error("count_posts_filtered: %s", e)
            return 0

    def _build_search_clauses(self, params):
        """Общие условия WHERE для поиска."""
        from core.post_search import PostSearchParams

        if not isinstance(params, PostSearchParams):
            params = PostSearchParams(query=str(params or ''))
        clauses = []
        params_list: list = []
        join_fts = False
        q = (params.query or '').strip()
        if q:
            fts_q = q.replace('"', '""')
            if ' ' in fts_q and not fts_q.startswith('"'):
                fts_q = f'"{fts_q}"'
            clauses.append("p.id IN (SELECT rowid FROM posts_fts WHERE posts_fts MATCH ?)")
            params_list.append(fts_q)
            join_fts = True
        if params.date_from:
            clauses.append("p.date >= ?")
            params_list.append(params.date_from)
        if params.date_to:
            clauses.append("p.date <= ?")
            params_list.append(
                params.date_to + " 23:59" if len(params.date_to) <= 10 else params.date_to
            )
        if params.tag_hashtag:
            tag = (params.tag_hashtag or '').strip()
            if tag and not tag.startswith('#'):
                tag = f'#{tag}'
            like = f"%{tag}%"
            clauses.append(
                "(p.tags LIKE ? OR p.teacher_hashtag LIKE ? OR p.department_hashtag LIKE ?)"
            )
            params_list.extend([like, like, like])
        if params.department_id is not None:
            did = int(params.department_id)
            clauses.append("(p.author_department_id = ? OR e.department_id = ?)")
            params_list.extend([did, did])
        if params.author_employee_id is not None:
            clauses.append("p.author_employee_id = ?")
            params_list.append(int(params.author_employee_id))
        if params.post_source == 'vk':
            clauses.append("COALESCE(p.post_source, 'vk') = 'vk'")
        elif params.post_source == 'manual':
            clauses.append("COALESCE(p.post_source, 'vk') = 'manual'")
        media_type = (params.media_type or '').strip().lower()
        if media_type == 'any':
            clauses.append(
                "EXISTS (SELECT 1 FROM attachments ax WHERE ax.original_post_id = p.original_post_id)"
            )
        elif media_type == 'none':
            clauses.append(
                "NOT EXISTS (SELECT 1 FROM attachments ax WHERE ax.original_post_id = p.original_post_id)"
            )
        elif media_type in ('photo', 'video', 'clip'):
            clauses.append(
                "EXISTS (SELECT 1 FROM attachments ax WHERE ax.original_post_id = p.original_post_id AND ax.media_type = ?)"
            )
            params_list.append(media_type)
        return clauses, params_list, q, join_fts

    def delete_attachment_by_path(self, original_post_id: int, media_path: str) -> bool:
        try:
            def _write():
                cur = self._get_cursor()
                cur.execute(
                    "DELETE FROM attachments WHERE original_post_id = ? AND media_path = ?",
                    (int(original_post_id), media_path),
                )
                self._get_conn().commit()
                return cur.rowcount > 0
            return self._run_write(_write, "delete_attachment_by_path")
        except Exception as e:
            logger.error("delete_attachment_by_path: %s", e)
            return False

    def list_media_paths_for_post(self, original_post_id: int) -> list[str]:
        try:
            rows = self._get_cursor().execute(
                "SELECT media_path FROM attachments WHERE original_post_id = ?",
                (int(original_post_id),),
            ).fetchall()
            return [r[0] for r in rows if r and r[0]]
        except Exception:
            return []

    def find_posts_by_date_prefix(self, date_prefix: str, limit: int = 200) -> list[dict]:
        try:
            like = f"{date_prefix}%"
            rows = self._get_cursor().execute("""
                SELECT p.original_post_id, p.date, p.text, p.tags,
                       GROUP_CONCAT(a.media_path)
                FROM posts p
                LEFT JOIN attachments a ON p.original_post_id = a.original_post_id
                WHERE p.date LIKE ?
                GROUP BY p.original_post_id
                ORDER BY p.date DESC
                LIMIT ?
            """, (like, max(1, int(limit)))).fetchall()
            return [
                {
                    'original_post_id': r[0],
                    'date': r[1],
                    'text': r[2] or '',
                    'tags': r[3] or '',
                    'media_paths': r[4] or '',
                }
                for r in rows
            ]
        except Exception as e:
            logger.error("find_posts_by_date_prefix: %s", e)
            return []

    def get_post_storage_row(self, original_post_id: int):
        """Одна строка в формате get_posts_paginated для карточки хранилища."""
        try:
            return self._get_cursor().execute("""
                SELECT p.original_post_id, MAX(p.id), MAX(p.date), MAX(p.text), MAX(p.tags),
                       MAX(p.likes), MAX(p.comments), MAX(p.shares),
                       GROUP_CONCAT(a.media_type), GROUP_CONCAT(a.media_path), GROUP_CONCAT(a.file_size),
                       MAX(p.post_url), MAX(p.teacher_hashtag), MAX(p.department_hashtag),
                       MAX(e.full_name), MAX(e.hashtag), MAX(d.hashtag),
                       MAX(p.post_source), MAX(p.source_label), MAX(p.importance)
                FROM posts p
                LEFT JOIN attachments a ON p.original_post_id = a.original_post_id
                LEFT JOIN employees e ON p.author_employee_id = e.id
                LEFT JOIN departments d ON COALESCE(e.department_id, p.author_department_id) = d.id
                WHERE p.original_post_id = ?
                GROUP BY p.original_post_id
            """, (int(original_post_id),)).fetchone()
        except Exception:
            return None

    def get_department_posts_in_period(
        self, department_id: int, date_from: str, date_to: str, limit: int = 500
    ) -> list[dict]:
        try:
            rows = self._get_cursor().execute("""
                SELECT p.original_post_id, p.date, p.text, p.tags, p.likes, p.comments, p.shares
                FROM posts p
                LEFT JOIN employees e ON p.author_employee_id = e.id
                WHERE (p.author_department_id = ? OR e.department_id = ?)
                  AND p.date >= ? AND p.date <= ?
                ORDER BY p.date DESC
                LIMIT ?
            """, (
                int(department_id), int(department_id),
                date_from, date_to + " 23:59" if len(date_to) <= 10 else date_to,
                max(1, int(limit)),
            )).fetchall()
            return [
                {
                    'original_post_id': r[0], 'date': r[1], 'text': r[2], 'tags': r[3],
                    'likes': r[4], 'comments': r[5], 'shares': r[6],
                }
                for r in rows
            ]
        except Exception:
            return []

    def get_department_employees_activity(
        self, department_id: int, date_from: str, date_to: str
    ) -> list[dict]:
        try:
            d_end = date_to + " 23:59" if len(date_to) <= 10 else date_to
            rows = self._get_cursor().execute("""
                SELECT e.full_name, e.hashtag, COUNT(DISTINCT p.original_post_id)
                FROM employees e
                JOIN posts p ON p.author_employee_id = e.id
                WHERE e.department_id = ? AND p.date >= ? AND p.date <= ?
                GROUP BY e.id
                ORDER BY COUNT(DISTINCT p.original_post_id) DESC
            """, (int(department_id), date_from, d_end)).fetchall()
            return [
                {'full_name': r[0], 'hashtag': r[1], 'post_count': r[2]}
                for r in rows
            ]
        except Exception:
            return []

    def get_all_attachments(self) -> list[dict]:
        try:
            rows = self._get_cursor().execute(
                "SELECT original_post_id, media_type, media_key, media_path, file_size FROM attachments"
            ).fetchall()
            return [
                {
                    'original_post_id': r[0],
                    'media_type': r[1],
                    'media_key': r[2],
                    'media_path': r[3],
                    'file_size': r[4],
                }
                for r in rows
            ]
        except Exception as e:
            logger.error("get_all_attachments: %s", e)
            return []

    def count_posts_without_attachments(self) -> int:
        try:
            row = self._get_cursor().execute("""
                SELECT COUNT(*) FROM posts p
                WHERE NOT EXISTS (
                    SELECT 1 FROM attachments a WHERE a.original_post_id = p.original_post_id
                )
            """).fetchone()
            return int(row[0] or 0) if row else 0
        except Exception:
            return 0

    def get_dictionary_hashtags(self, only_active: bool = True) -> list[str]:
        """Уникальные хэштеги словаря для выбора в редакторе."""
        try:
            q = "SELECT DISTINCT hashtag FROM tag_dictionary"
            if only_active:
                q += " WHERE active = 1"
            q += " ORDER BY hashtag COLLATE NOCASE ASC"
            rows = self._get_cursor().execute(q).fetchall()
            return [r[0] for r in rows if r[0]]
        except Exception:
            return []

    def list_distinct_manual_source_labels(self) -> list[str]:
        """Подписи источника у ручных постов (для выпадающих списков)."""
        try:
            rows = self._get_cursor().execute("""
                SELECT DISTINCT TRIM(source_label)
                FROM posts
                WHERE COALESCE(post_source, 'vk') = 'manual'
                  AND TRIM(COALESCE(source_label, '')) != ''
                ORDER BY source_label COLLATE NOCASE ASC
            """).fetchall()
            return [r[0] for r in rows if r[0]]
        except Exception:
            return []

    def list_employees_for_filter(self) -> list[dict]:
        try:
            rows = self._get_cursor().execute("""
                SELECT e.id, e.full_name, e.hashtag, d.name
                FROM employees e
                LEFT JOIN departments d ON e.department_id = d.id
                ORDER BY e.full_name COLLATE NOCASE ASC
            """).fetchall()
            return [
                {'id': r[0], 'full_name': r[1], 'hashtag': r[2], 'department_name': r[3]}
                for r in rows
            ]
        except Exception:
            return []

    def get_all_posts(self, limit=500):
        try:
            result = self._get_cursor().execute("""
                SELECT p.original_post_id, MAX(p.id), MAX(p.date), MAX(p.text), MAX(p.tags),
                       MAX(p.likes), MAX(p.comments), MAX(p.shares),
                       GROUP_CONCAT(a.media_type), GROUP_CONCAT(a.media_path), GROUP_CONCAT(a.file_size),
                       MAX(p.post_url), MAX(p.teacher_hashtag), MAX(p.department_hashtag),
                       MAX(e.full_name), MAX(e.hashtag), MAX(d.hashtag)
                FROM posts p
                LEFT JOIN attachments a ON p.original_post_id = a.original_post_id
                LEFT JOIN employees e ON p.author_employee_id = e.id
                LEFT JOIN departments d ON COALESCE(e.department_id, p.author_department_id) = d.id
                GROUP BY p.original_post_id ORDER BY p.date DESC LIMIT ?
            """, (limit,)).fetchall()
            return result
        except Exception as e:
            logger.error(f"[DB] get_all_posts Error: {e}")
            return []

    def get_posts_count(self):
        try:
            row = self._get_cursor().execute("SELECT COUNT(*) FROM posts").fetchone()
            return int(row[0] or 0) if row else 0
        except Exception as e:
            logger.error("get_posts_count: %s", e)
            return 0

    def get_posts_paginated(self, limit=20, offset=0):
        try:
            limit = max(1, int(limit))
            offset = max(0, int(offset))
            return self._get_cursor().execute("""
                SELECT p.original_post_id, MAX(p.id), MAX(p.date), MAX(p.text), MAX(p.tags),
                       MAX(p.likes), MAX(p.comments), MAX(p.shares),
                       GROUP_CONCAT(a.media_type), GROUP_CONCAT(a.media_path), GROUP_CONCAT(a.file_size),
                       MAX(p.post_url), MAX(p.teacher_hashtag), MAX(p.department_hashtag),
                       MAX(e.full_name), MAX(e.hashtag), MAX(d.hashtag),
                       MAX(p.post_source), MAX(p.source_label), MAX(p.importance)
                FROM posts p
                LEFT JOIN attachments a ON p.original_post_id = a.original_post_id
                LEFT JOIN employees e ON p.author_employee_id = e.id
                LEFT JOIN departments d ON COALESCE(e.department_id, p.author_department_id) = d.id
                GROUP BY p.original_post_id
                ORDER BY p.date DESC
                LIMIT ? OFFSET ?
            """, (limit, offset)).fetchall()
        except Exception as e:
            logger.error("get_posts_paginated: %s", e)
            return []

    # === TAG DICTIONARY ===
    def seed_default_tag_dictionary(self, defaults: list[dict]) -> int:
        if not defaults:
            return 0
        try:
            def _write():
                cur = self._get_cursor()
                inserted = 0
                for item in defaults:
                    category = (item.get('category') or '').strip().lower()
                    phrase = (item.get('phrase') or '').strip()
                    hashtag = (item.get('hashtag') or '').strip()
                    weight = int(item.get('weight') or 100)
                    if not category or not phrase or not hashtag:
                        continue
                    cur.execute("""
                        INSERT OR IGNORE INTO tag_dictionary (category, phrase, hashtag, weight, active, updated_at)
                        VALUES (?, ?, ?, ?, 1, CURRENT_TIMESTAMP)
                    """, (category, phrase, hashtag, weight))
                    if cur.rowcount > 0:
                        inserted += 1
                self._get_conn().commit()
                return inserted

            return self._run_write(_write, "seed_default_tag_dictionary")
        except Exception as e:
            logger.error("seed_default_tag_dictionary: %s", e)
            return 0

    def prune_tag_dictionary(
        self,
        disallowed_phrases: frozenset[str] | set[str] | None = None,
        canonical_phrase_by_hashtag: dict[str, str] | None = None,
    ) -> int:
        """Удаляет неверные фразы и дубли с одним хэштегом (оставляет каноническую запись)."""
        from core.nlp_processor import (
            CANONICAL_PHRASE_BY_HASHTAG,
            DISALLOWED_DICTIONARY_PHRASES,
            normalize_hashtag,
            normalize_text,
        )

        disallowed = disallowed_phrases if disallowed_phrases is not None else DISALLOWED_DICTIONARY_PHRASES
        canonical = canonical_phrase_by_hashtag if canonical_phrase_by_hashtag is not None else CANONICAL_PHRASE_BY_HASHTAG
        bad_keys = {normalize_text(p) for p in disallowed}
        canon_by_tag = {
            normalize_hashtag(tag).lower().replace('ё', 'е'): normalize_text(phrase)
            for tag, phrase in canonical.items()
        }

        try:
            def _write():
                cur = self._get_cursor()
                removed = 0

                rows = cur.execute(
                    "SELECT id, phrase FROM tag_dictionary"
                ).fetchall()
                for row_id, phrase in rows:
                    if normalize_text(phrase) in bad_keys:
                        cur.execute("DELETE FROM tag_dictionary WHERE id = ?", (row_id,))
                        removed += 1

                rows = cur.execute(
                    "SELECT id, phrase, hashtag FROM tag_dictionary ORDER BY id"
                ).fetchall()
                by_tag: dict[str, list[tuple]] = {}
                for row_id, phrase, hashtag in rows:
                    key = normalize_hashtag(hashtag).lower().replace('ё', 'е')
                    by_tag.setdefault(key, []).append((row_id, phrase, hashtag))

                for tag_key, group in by_tag.items():
                    if len(group) <= 1:
                        continue
                    preferred = canon_by_tag.get(tag_key)
                    keep_id = None
                    if preferred:
                        for row_id, phrase, _ in group:
                            if normalize_text(phrase) == preferred:
                                keep_id = row_id
                                break
                    if keep_id is None:
                        keep_id = min(row[0] for row in group)
                    for row_id, _, _ in group:
                        if row_id != keep_id:
                            cur.execute("DELETE FROM tag_dictionary WHERE id = ?", (row_id,))
                            removed += 1

                self._get_conn().commit()
                return removed

            return self._run_write(_write, "prune_tag_dictionary")
        except Exception as e:
            logger.error("prune_tag_dictionary: %s", e)
            return 0

    def normalize_tag_dictionary_hashtags(self) -> int:
        """Убирает префиксы категорий из хэштегов словаря (#событийные_... → #...)."""
        prefixes = (
            'персональные_', 'групповые_', 'событийные_', 'праздники_',
            'personal_', 'group_', 'event_',
        )
        try:
            def _write():
                cur = self._get_cursor()
                rows = cur.execute("SELECT id, hashtag FROM tag_dictionary").fetchall()
                updated = 0
                for row_id, hashtag in rows:
                    if not hashtag:
                        continue
                    raw = hashtag.strip().lower().replace('ё', 'е')
                    if not raw.startswith('#'):
                        raw = f'#{raw}'
                    new_tag = raw
                    for prefix in prefixes:
                        if new_tag.startswith(f'#{prefix}'):
                            new_tag = '#' + new_tag[len(prefix) + 1:]
                            break
                    new_tag = new_tag.replace(' ', '_')
                    if new_tag != raw:
                        cur.execute(
                            "UPDATE tag_dictionary SET hashtag = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                            (new_tag, row_id),
                        )
                        updated += 1
                self._get_conn().commit()
                return updated

            return self._run_write(_write, "normalize_tag_dictionary_hashtags")
        except Exception as e:
            logger.error("normalize_tag_dictionary_hashtags: %s", e)
            return 0

    def get_tag_dictionary(self, category: str | None = None, only_active: bool = False):
        try:
            query = "SELECT id, category, phrase, hashtag, weight, active, parent_hashtag FROM tag_dictionary"
            params = []
            clauses = []
            if category:
                clauses.append("category = ?")
                params.append(category.strip().lower())
            if only_active:
                clauses.append("active = 1")
            if clauses:
                query += " WHERE " + " AND ".join(clauses)
            query += " ORDER BY category, weight DESC, phrase COLLATE NOCASE ASC"
            rows = self._get_cursor().execute(query, tuple(params)).fetchall()
            return [
                {
                    'id': row[0],
                    'category': row[1],
                    'phrase': row[2],
                    'hashtag': row[3],
                    'weight': row[4],
                    'active': bool(row[5]),
                    'parent_hashtag': row[6] if len(row) > 6 else None,
                }
                for row in rows
            ]
        except Exception as e:
            logger.error("get_tag_dictionary: %s", e)
            return []

    def add_tag_dictionary_entry(
        self,
        category: str,
        phrase: str,
        hashtag: str,
        weight: int = 100,
        active: bool = True,
        parent_hashtag: str | None = None,
    ):
        try:
            category = (category or '').strip().lower()
            phrase = (phrase or '').strip()
            hashtag = (hashtag or '').strip()
            if not category or not phrase or not hashtag:
                return None

            def _write():
                cur = self._get_cursor()
                parent = (parent_hashtag or '').strip() or None
                cur.execute("""
                    INSERT OR REPLACE INTO tag_dictionary (
                        id, category, phrase, hashtag, weight, active, parent_hashtag, updated_at
                    )
                    VALUES (
                        (SELECT id FROM tag_dictionary WHERE category = ? AND phrase = ? LIMIT 1),
                        ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP
                    )
                """, (
                    category, phrase, category, phrase, hashtag,
                    int(weight), 1 if active else 0, parent,
                ))
                self._get_conn().commit()
                row = cur.execute(
                    """SELECT id, category, phrase, hashtag, weight, active, parent_hashtag
                       FROM tag_dictionary WHERE category = ? AND phrase = ? LIMIT 1""",
                    (category, phrase),
                ).fetchone()
                return row

            row = self._run_write(_write, "add_tag_dictionary_entry")
            if not row:
                return None
            return {
                'id': row[0],
                'category': row[1],
                'phrase': row[2],
                'hashtag': row[3],
                'weight': row[4],
                'active': bool(row[5]),
                'parent_hashtag': row[6] if len(row) > 6 else None,
            }
        except Exception as e:
            logger.error("add_tag_dictionary_entry: %s", e)
            return None

    def update_tag_dictionary_entry(
        self,
        entry_id: int,
        category: str,
        phrase: str,
        hashtag: str,
        weight: int,
        active: bool,
        parent_hashtag: str | None = None,
    ):
        try:
            parent = (parent_hashtag or '').strip() or None
            def _write():
                self._get_cursor().execute("""
                    UPDATE tag_dictionary
                    SET category = ?, phrase = ?, hashtag = ?, weight = ?, active = ?,
                        parent_hashtag = ?, updated_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                """, (
                    (category or '').strip().lower(),
                    (phrase or '').strip(),
                    (hashtag or '').strip(),
                    int(weight),
                    1 if active else 0,
                    parent,
                    int(entry_id),
                ))
                self._get_conn().commit()
                return True

            return self._run_write(_write, "update_tag_dictionary_entry")
        except Exception as e:
            logger.error("update_tag_dictionary_entry: %s", e)
            return False

    def delete_tag_dictionary_entry(self, entry_id: int):
        try:
            def _write():
                self._get_cursor().execute("DELETE FROM tag_dictionary WHERE id = ?", (int(entry_id),))
                self._get_conn().commit()
                return True

            return self._run_write(_write, "delete_tag_dictionary_entry")
        except Exception as e:
            logger.error("delete_tag_dictionary_entry: %s", e)
            return False

    def get_posts_for_teachers_export(self, start_date, end_date):
        """Посты преподавателей за период для экспорта в Word."""
        try:
            rows = self._get_cursor().execute("""
                SELECT p.text, COALESCE(p.post_url, ''),
                       COALESCE(e.full_name, ''),
                       COALESCE(p.teacher_hashtag, e.hashtag, ''),
                       COALESCE(p.department_hashtag, d.hashtag, ''),
                       p.date, e.id
                FROM posts p
                JOIN employees e ON p.author_employee_id = e.id
                LEFT JOIN departments d ON COALESCE(e.department_id, p.author_department_id) = d.id
                WHERE p.date >= ? AND p.date <= ?
                ORDER BY e.full_name, p.date DESC
            """, (start_date, end_date)).fetchall()
            return [
                {
                    'text': row[0] or '',
                    'post_url': row[1] or '',
                    'author_name': row[2] or '',
                    'teacher_hashtag': row[3] or '',
                    'department_hashtag': row[4] or '',
                    'date': row[5] or '',
                    'employee_id': row[6],
                }
                for row in rows
            ]
        except Exception as e:
            logger.error(f"[DB] get_posts_for_teachers_export Error: {e}")
            return []

    def get_stats(self):
        try:
            c = self._get_cursor()
            total = int(c.execute('SELECT COUNT(*) FROM posts').fetchone()[0] or 0)
            manual = int(c.execute(
                "SELECT COUNT(*) FROM posts WHERE COALESCE(post_source, 'vk') = 'manual'"
            ).fetchone()[0] or 0)
            month_prefix = datetime.datetime.now().strftime("%Y-%m")
            month_count = int(c.execute(
                "SELECT COUNT(*) FROM posts WHERE date LIKE ?", (f"{month_prefix}%",)
            ).fetchone()[0] or 0)
            no_author = int(c.execute(
                "SELECT COUNT(*) FROM posts WHERE author_employee_id IS NULL "
                "AND (teacher_hashtag IS NULL OR TRIM(teacher_hashtag) = '')"
            ).fetchone()[0] or 0)
            no_tags = int(c.execute(
                "SELECT COUNT(*) FROM posts WHERE tags IS NULL OR TRIM(tags) = ''"
            ).fetchone()[0] or 0)
            no_files = self.count_posts_without_attachments()
            top_dept = c.execute("""
                SELECT d.name, COUNT(DISTINCT p.original_post_id) AS cnt
                FROM posts p
                JOIN employees e ON p.author_employee_id = e.id
                JOIN departments d ON e.department_id = d.id
                GROUP BY d.id
                ORDER BY cnt DESC
                LIMIT 1
            """).fetchone()
            photos = int(c.execute(
                "SELECT COUNT(*) FROM attachments WHERE media_type='photo'"
            ).fetchone()[0] or 0)
            videos = int(c.execute(
                "SELECT COUNT(*) FROM attachments WHERE media_type='video'"
            ).fetchone()[0] or 0)
            clips = int(c.execute(
                "SELECT COUNT(*) FROM attachments WHERE media_type='clip'"
            ).fetchone()[0] or 0)
            likes_row = c.execute(
                'SELECT COALESCE(SUM(likes),0), COALESCE(SUM(comments),0), COALESCE(SUM(shares),0) FROM posts'
            ).fetchone()
            return {
                'total': total,
                'vk': max(0, total - manual),
                'manual': manual,
                'month': month_count,
                'no_author': no_author,
                'no_tags': no_tags,
                'no_files': no_files,
                'top_department': top_dept[0] if top_dept else '—',
                'top_department_count': int(top_dept[1] or 0) if top_dept else 0,
                'photos': photos,
                'videos': videos,
                'clips': clips,
                'files': photos + videos + clips,
                'likes': int(likes_row[0] or 0) if likes_row else 0,
                'comments': int(likes_row[1] or 0) if likes_row else 0,
                'shares': int(likes_row[2] or 0) if likes_row else 0,
            }
        except Exception:
            return {
                'total': 0, 'vk': 0, 'manual': 0, 'month': 0,
                'no_author': 0, 'no_tags': 0, 'no_files': 0,
                'top_department': '—', 'top_department_count': 0,
                'photos': 0, 'videos': 0, 'clips': 0, 'files': 0,
                'likes': 0, 'comments': 0, 'shares': 0,
            }

    def close(self):
        try:
            if hasattr(self._local, 'conn') and self._local.conn:
                self._local.conn.close()
                self._local.conn = None
        except: 
            pass

    def __del__(self): 
        self.close()

    # === СТАТИСТИКА ===
    def update_post_stats(self, original_post_id, likes, comments, shares):
        try:
            pid = int(original_post_id)

            def _write():
                conn = self._get_conn()
                cur = conn.cursor()
                cur.execute(
                    "UPDATE posts SET likes=?, comments=?, shares=?, last_stats_update=CURRENT_TIMESTAMP WHERE original_post_id=?",
                    (likes, comments, shares, pid),
                )
                conn.commit()
                return cur.rowcount > 0

            return self._run_write(_write, f"update_post_stats({pid})")
        except Exception as e:
            logger.error("update_post_stats(%s): %s", original_post_id, e)
            return False

    def update_post_stats_batch(self, rows):
        if not rows:
            return True
        try:
            def _write():
                conn = self._get_conn()
                conn.execute("BEGIN IMMEDIATE")
                try:
                    cur = conn.cursor()
                    for pid, likes, comments, shares in rows:
                        cur.execute(
                            "UPDATE posts SET likes=?, comments=?, shares=?, last_stats_update=CURRENT_TIMESTAMP WHERE original_post_id=?",
                            (likes, comments, shares, int(pid)),
                        )
                    conn.commit()
                except Exception:
                    conn.rollback()
                    raise
                return True

            return self._run_write(_write, "update_post_stats_batch")
        except Exception as e:
            logger.error("update_post_stats_batch: %s", e)
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
                'date': res[3]
            } if res else None
        except Exception: 
            return None

    def update_post_tags(
        self,
        original_post_id,
        tags=None,
        teacher_hashtag=None,
        department_hashtag=None,
        author_employee_id=None,
        author_department_id=None,
    ):
        try:
            pid = int(original_post_id)

            def _write():
                self._get_cursor().execute("""
                    UPDATE posts SET
                        tags = ?,
                        teacher_hashtag = ?,
                        department_hashtag = ?,
                        author_employee_id = ?,
                        author_department_id = ?
                    WHERE original_post_id = ?
                """, (
                    tags, teacher_hashtag, department_hashtag,
                    author_employee_id, author_department_id, pid,
                ))
                self._get_conn().commit()
                return True

            return self._run_write(_write, f"update_post_tags({pid})")
        except Exception as e:
            logger.error("update_post_tags(%s): %s", original_post_id, e)
            return False

    def save_post_period_statistics(self, original_post_id, period_type, period_start, period_end, likes, comments, shares, rank):
        try:
            self._get_cursor().execute(
                "INSERT INTO post_statistics (original_post_id, period_type, period_start, period_end, likes, comments, shares, rank) VALUES (?,?,?,?,?,?,?,?)",
                (original_post_id, period_type, period_start, period_end, likes, comments, shares, rank))
            self._get_conn().commit()
            return True
        except Exception:  
            return False

    def get_top_posts_by_period(self, period_type, period_start, period_end, metric='likes', limit=10):
        try:
            metric_map = {'likes': 'likes', 'comments': 'comments', 'shares': 'shares'}
            col = metric_map.get(metric, 'likes')
            return self._get_cursor().execute(f"""
                SELECT ps.original_post_id, ps.{col}, p.text, p.date FROM post_statistics ps
                JOIN posts p ON ps.original_post_id = p.original_post_id
                WHERE ps.period_type=? AND ps.period_start=? AND ps.period_end=?
                GROUP BY ps.original_post_id ORDER BY ps.{col} DESC LIMIT ?
            """, (period_type, period_start, period_end, limit)).fetchall()
        except Exception: 
            return []

    def get_top_employees_by_period_from_posts(self, period_type, period_start, period_end, limit=50):
        try:
            return self._get_cursor().execute('''
                SELECT e.id, e.full_name, e.hashtag, d.name AS department_name, d.hashtag AS department_hashtag,
                       COUNT(p.original_post_id) AS post_count,
                       SUM(p.likes) AS total_likes
                FROM employees e
                LEFT JOIN posts p ON p.author_employee_id = e.id
                LEFT JOIN departments d ON e.department_id = d.id
                WHERE p.date >= ? AND p.date <= ?
                GROUP BY e.id
                ORDER BY post_count DESC
                LIMIT ?
            ''', (period_start, period_end, limit)).fetchall()
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

    def get_posts_with_author_by_date_range(self, start_date, end_date):
        try:
            return self._get_cursor().execute("""
                SELECT DISTINCT p.original_post_id, p.date, p.text, p.tags, p.post_url,
                    p.teacher_hashtag, p.department_hashtag, p.author_employee_id, p.author_department_id,
                    e.full_name AS author_name, e.hashtag AS author_hashtag, d.name AS department_name, d.hashtag AS dept_hashtag
                FROM posts p
                LEFT JOIN employees e ON p.author_employee_id = e.id
                LEFT JOIN departments d ON p.author_department_id = d.id
                WHERE p.date >= ? AND p.date <= ?
                ORDER BY p.date DESC
            """, (start_date, end_date)).fetchall()
        except Exception as e:
            logger.error(f"get_posts_with_author_by_date_range: {e}")
            return []

    def list_post_files_for_export(self, original_post_id: int) -> list[dict]:
        """Все вложения поста с исходными путями (для копирования на рабочий стол)."""
        try:
            rows = self._get_cursor().execute(
                """
                SELECT media_type, media_path, media_key, file_size
                FROM attachments
                WHERE original_post_id = ?
                ORDER BY id ASC
                """,
                (int(original_post_id),),
            ).fetchall()
            return [
                {
                    'media_type': r[0],
                    'media_path': r[1],
                    'media_key': r[2],
                    'file_size': r[3],
                }
                for r in rows
            ]
        except Exception as e:
            logger.error("list_post_files_for_export(%s): %s", original_post_id, e)
            return []

    def get_attachments_for_post(self, original_post_id, limit=5):
        try:
            cur = self._get_cursor()
            rows = cur.execute(
                "SELECT media_type, media_path FROM attachments WHERE original_post_id = ? LIMIT ?",
                (original_post_id, limit)
            ).fetchall()
            results = []
            import os, glob
            for r in rows:
                mtype, mpath = r[0], r[1]
                chosen = mpath
                # For video/clip try to find a thumbnail file saved by downloader
                if mtype in ('video', 'clip'):
                    # if the recorded media path is a video file on disk, look in same dir
                    if mpath and os.path.exists(mpath):
                        folder = os.path.dirname(mpath)
                        pattern = os.path.join(folder, f"post_{original_post_id}_{mtype}_*_thumb.jpg")
                        found = glob.glob(pattern)
                        if found:
                            chosen = found[0]
                    else:
                        # fallback: search project for any thumb matching post id
                        found = glob.glob(f"**/post_{original_post_id}_*thumb.jpg", recursive=True)
                        if found:
                            chosen = found[0]

                if chosen:
                    results.append({'media_type': mtype, 'media_path': chosen})

            return results
        except Exception as e:
            logger.error(f"get_attachments_for_post({original_post_id}): {e}")
            return []

    def save_employee_statistics(self, employee_name, period_type, period_start, period_end, mention_count, post_count, total_likes, rank):
        try:
            self._get_cursor().execute(
                "INSERT INTO employee_statistics (employee_name, period_type, period_start, period_end, mention_count, post_count, total_likes, rank) VALUES (?,?,?,?,?,?,?,?)",
                (employee_name, period_type, period_start, period_end, mention_count, post_count, total_likes, rank))
            self._get_conn().commit()
            return True
        except Exception: 
            return False

    def get_top_employee_statistics_by_period(self, period_type, period_start, period_end, metric='mention_count', limit=10):
        try:
            col = {'mention_count': 'mention_count', 'post_count': 'post_count', 'total_likes': 'total_likes'}.get(metric, 'mention_count')
            return self._get_cursor().execute(
                f"SELECT employee_name, {col}, post_count, mention_count FROM employee_statistics WHERE period_type=? AND period_start=? AND period_end=? ORDER BY {col} DESC LIMIT ?",
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

    def verify_post_consistency(self, original_post_id):
        try:
            return self._get_cursor().execute("SELECT COUNT(*) FROM posts WHERE original_post_id = ?", (original_post_id,)).fetchone()[0] > 0
        except Exception: 
            return False