import sqlite3
import json
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, Any
import hashlib
import secrets

DB_PATH = Path(__file__).parent.parent / "storage" / "database.db"

def get_db():
    """Получить соединение с БД"""
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn

def init_db():
    """Инициализировать все таблицы"""
    conn = get_db()
    cursor = conn.cursor()
    
    # ============================================================
    #  ТАБЛИЦА 1: ПОЛЬЗОВАТЕЛИ (с avatar)
    # ============================================================
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            salt TEXT NOT NULL,
            role TEXT DEFAULT 'user',
            is_active BOOLEAN DEFAULT 1,
            avatar TEXT DEFAULT '',
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
    ''')
    
    # Проверяем, есть ли колонка avatar (для миграции)
    cursor.execute("PRAGMA table_info(users)")
    columns = [col[1] for col in cursor.fetchall()]
    if 'avatar' not in columns:
        cursor.execute("ALTER TABLE users ADD COLUMN avatar TEXT DEFAULT ''")
    
    # ============================================================
    #  ТАБЛИЦА 2: ТОКЕНЫ
    # ============================================================
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS tokens (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            token TEXT UNIQUE NOT NULL,
            expires_at TEXT NOT NULL,
            created_at TEXT NOT NULL,
            FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
        )
    ''')
    
    # ============================================================
    #  ТАБЛИЦА 3: ПРАВА ДОСТУПА
    # ============================================================
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS permissions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            resource_type TEXT NOT NULL,
            resource_id INTEGER,
            action TEXT NOT NULL,
            allowed BOOLEAN DEFAULT 1,
            FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
        )
    ''')
    
    # ============================================================
    #  ТАБЛИЦА 4: ПРОЕКТЫ
    # ============================================================
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS projects (
            id TEXT PRIMARY KEY,
            user_id INTEGER NOT NULL,
            project_name TEXT NOT NULL,
            project_data TEXT NOT NULL,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
        )
    ''')
    
    # ============================================================
    #  ТАБЛИЦА 5: РЕСУРСЫ (Оффлайн БД)
    # ============================================================
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS resources (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            content TEXT NOT NULL,
            type TEXT NOT NULL,
            version TEXT,
            hash TEXT,
            created_at TEXT NOT NULL
        )
    ''')
    
    # ============================================================
    #  ДЕФОЛТНЫЕ ДАННЫЕ
    # ============================================================
    
    # Создаём root пользователя
    root = cursor.execute("SELECT id FROM users WHERE username = 'root'").fetchone()
    if not root:
        salt = secrets.token_hex(16)
        password_hash = hashlib.pbkdf2_hmac('sha256', 'admin123'.encode(), salt.encode(), 100000).hex()
        now = datetime.now().isoformat()
        cursor.execute('''
            INSERT INTO users (username, email, password_hash, salt, role, avatar, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', ('root', 'root@flux.studio', password_hash, salt, 'root', '', now, now))
        
        root_id = cursor.lastrowid
        
        for resource_type in ['project', 'template', 'asset', 'user', 'settings']:
            for action in ['read', 'write', 'delete']:
                cursor.execute('''
                    INSERT INTO permissions (user_id, resource_type, action, allowed)
                    VALUES (?, ?, ?, ?)
                ''', (root_id, resource_type, action, 1))
    
    # Дефолтные шаблоны
    templates = [
        ('blank', '📄', 'Blank Template', '<div>Hello World</div>'),
        ('website', '🌐', 'Website', '<header>My Site</header><main>Content</main>'),
        ('dashboard', '📊', 'Dashboard', '<div class="dashboard">Stats</div>'),
    ]
    
    for template_id, emoji, name, content in templates:
        exists = cursor.execute("SELECT id FROM resources WHERE name = ?", (name,)).fetchone()
        if not exists:
            cursor.execute('''
                INSERT INTO resources (name, content, type, version, created_at)
                VALUES (?, ?, ?, ?, ?)
            ''', (name, content, 'template', '1.0', datetime.now().isoformat()))
    
    conn.commit()
    conn.close()
    print("✅ SQLite database initialized!")

def hash_password(password: str, salt: str = None) -> tuple:
    if salt is None:
        salt = secrets.token_hex(16)
    hash_obj = hashlib.pbkdf2_hmac('sha256', password.encode(), salt.encode(), 100000)
    return salt, hash_obj.hex()

def verify_password(password: str, salt: str, hash_value: str) -> bool:
    _, new_hash = hash_password(password, salt)
    return new_hash == hash_value

def generate_token() -> str:
    return secrets.token_urlsafe(64)

def update_user_avatar(user_id: int, avatar_path: str):
    """Обновить аватар пользователя"""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE users SET avatar = ?, updated_at = ? WHERE id = ?",
        (avatar_path, datetime.now().isoformat(), user_id)
    )
    conn.commit()
    conn.close()
    return True

def get_user_by_id(user_id: int):
    """Получить пользователя по ID"""
    conn = get_db()
    cursor = conn.cursor()
    user = cursor.execute(
        "SELECT id, username, email, role, avatar, created_at FROM users WHERE id = ?",
        (user_id,)
    ).fetchone()
    conn.close()
    return dict(user) if user else None