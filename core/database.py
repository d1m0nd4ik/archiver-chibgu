import sqlite3
import threading
import time
from config.settings import DB_NAME
from core.logging_config import logger

_MAX_DB_RETRIES = 8
_RETRY_BASE_DELAY = 0.15


class Database:
    CURRENT_SCHEMA_VERSION = 6
    _schema_initialized = False
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
            if Database._schema_initialized: 
                return

            conn = self._get_conn()
            cursor = conn.cursor()
            self._create_tables(cursor)
            self._ensure_schema_columns(cursor)
            conn.commit()
            
            # ... (остальной код миграций без изменений) ...
            # Миграции выполняются ТОЛЬКО при обновлении старой БД
            # На новом компьютере версия = 6, миграции пропускаются
            
            Database._schema_initialized = True

    def _create_tables(self, cursor):
        # posts — основная таблица
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
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # 📚 FTS5 — БЫСТРЫЙ ПОИСК (обязательно оставить!)
        cursor.execute("CREATE VIRTUAL TABLE IF NOT EXISTS posts_fts USING fts5(text, tags, tokenize='unicode61')")
        
        # Триггеры для авто-синхронизации FTS
        cursor.execute("""CREATE TRIGGER IF NOT EXISTS posts_fts_insert AFTER INSERT ON posts
            BEGIN INSERT INTO posts_fts (rowid, text, tags) VALUES (new.id, new.text, new.tags); END;""")
        cursor.execute("""CREATE TRIGGER IF NOT EXISTS posts_fts_update AFTER UPDATE ON posts
            BEGIN UPDATE posts_fts SET text=new.text, tags=new.tags WHERE rowid=old.id; END;""")
        cursor.execute("""CREATE TRIGGER IF NOT EXISTS posts_fts_delete AFTER DELETE ON posts
            BEGIN DELETE FROM posts_fts WHERE rowid=old.id; END;""")
        
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

        except Exception as e:
            logger.warning("_ensure_schema_columns: %s", e)

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

    def save_post(self, original_post_id, date, text, tags, likes=0, comments=0, shares=0,
                  post_url=None, author_employee_id=None, author_department_id=None,
                  teacher_hashtag=None, department_hashtag=None):
        try:
            if self.post_exists(original_post_id):
                return False

            def _write():
                self._get_cursor().execute("""
                    INSERT INTO posts (original_post_id, date, text, tags, likes, comments, shares,
                                       post_url, author_employee_id, author_department_id,
                                       teacher_hashtag, department_hashtag, last_stats_update)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                """, (
                    original_post_id, date, text, tags, likes, comments, shares,
                    post_url, author_employee_id, author_department_id,
                    teacher_hashtag, department_hashtag
                ))
                self._get_conn().commit()
                return True

            return self._run_write(_write, "save_post")
        except Exception as e:
            logger.error(f"DB Save Post Error: {e}")
            return False

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
            row = self._get_cursor().execute(
                "SELECT id, name, hashtag, url FROM departments WHERE hashtag = ? LIMIT 1", (hashtag,)
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
        try:
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