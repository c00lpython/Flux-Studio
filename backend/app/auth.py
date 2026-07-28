from fastapi import HTTPException, Header, Depends
from datetime import datetime, timedelta
from app.database import get_db, verify_password, hash_password, generate_token
import secrets

def create_session(user_id: int) -> dict:
    """Создать новую сессию (токен)"""
    conn = get_db()
    cursor = conn.cursor()
    
    token = generate_token()
    expires_at = (datetime.now() + timedelta(days=30)).isoformat()
    now = datetime.now().isoformat()
    
    cursor.execute('''
        INSERT INTO tokens (user_id, token, expires_at, created_at)
        VALUES (?, ?, ?, ?)
    ''', (user_id, token, expires_at, now))
    
    conn.commit()
    conn.close()
    
    return {
        "token": token,
        "expires_at": expires_at
    }

def get_user_by_token(token: str):
    conn = get_db()
    cursor = conn.cursor()
    
    token_record = cursor.execute('''
        SELECT id, user_id, expires_at FROM tokens WHERE token = ?
    ''', (token,)).fetchone()
    
    if not token_record:
        conn.close()
        raise HTTPException(401, "Invalid token")
    
    if datetime.fromisoformat(token_record["expires_at"]) < datetime.now():
        cursor.execute("DELETE FROM tokens WHERE id = ?", (token_record["id"],))
        conn.commit()
        conn.close()
        raise HTTPException(401, "Token expired")
    
    user = cursor.execute('''
        SELECT id, username, email, role, is_active, avatar FROM users WHERE id = ?
    ''', (token_record["user_id"],)).fetchone()
    
    conn.close()
    
    if not user or not user["is_active"]:
        raise HTTPException(403, "User inactive")
    
    return dict(user)

def get_user_tokens(user_id: int):
    conn = get_db()
    cursor = conn.cursor()
    
    tokens = cursor.execute('''
        SELECT id, token, expires_at, created_at 
        FROM tokens 
        WHERE user_id = ? AND expires_at > ?
        ORDER BY created_at DESC
    ''', (user_id, datetime.now().isoformat())).fetchall()
    
    conn.close()
    return [dict(token) for token in tokens]

def delete_token(token_id: int, user_id: int):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        "DELETE FROM tokens WHERE id = ? AND user_id = ?",
        (token_id, user_id)
    )
    conn.commit()
    conn.close()
    return True

def delete_all_tokens(user_id: int):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM tokens WHERE user_id = ?", (user_id,))
    conn.commit()
    conn.close()
    return True

async def get_current_user(authorization: str = Header(...)):
    if not authorization.startswith("Bearer "):
        raise HTTPException(401, "Invalid authorization header")
    
    token = authorization.replace("Bearer ", "")
    return get_user_by_token(token)

def register_user(username: str, email: str, password: str):
    conn = get_db()
    cursor = conn.cursor()
    
    existing = cursor.execute(
        "SELECT id FROM users WHERE username = ? OR email = ?", 
        (username, email)
    ).fetchone()
    
    if existing:
        conn.close()
        raise HTTPException(400, "Username or email already exists")
    
    salt, password_hash = hash_password(password)
    now = datetime.now().isoformat()
    
    cursor.execute('''
        INSERT INTO users (username, email, password_hash, salt, avatar, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    ''', (username, email, password_hash, salt, '', now, now))
    
    user_id = cursor.lastrowid
    conn.commit()
    conn.close()
    
    conn = get_db()
    cursor = conn.cursor()
    for action in ['read', 'write', 'delete']:
        cursor.execute('''
            INSERT INTO permissions (user_id, resource_type, action, allowed)
            VALUES (?, ?, ?, ?)
        ''', (user_id, 'project', action, 1))
    conn.commit()
    conn.close()
    
    session = create_session(user_id)
    
    return {
        "id": user_id,
        "username": username,
        "email": email,
        "token": session["token"],
        "expires_at": session["expires_at"]
    }

def login_user(username: str, password: str):
    conn = get_db()
    cursor = conn.cursor()
    
    user = cursor.execute('''
        SELECT id, username, email, password_hash, salt, role, avatar 
        FROM users WHERE username = ?
    ''', (username,)).fetchone()
    
    if not user:
        conn.close()
        raise HTTPException(401, "Invalid username or password")
    
    if not verify_password(password, user["salt"], user["password_hash"]):
        conn.close()
        raise HTTPException(401, "Invalid username or password")
    
    conn.close()
    
    session = create_session(user["id"])
    
    return {
        "user_id": user["id"],
        "username": user["username"],
        "email": user["email"],
        "role": user["role"],
        "avatar": user["avatar"] or "",
        "token": session["token"],
        "expires_at": session["expires_at"]
    }