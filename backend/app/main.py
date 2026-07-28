from fastapi import FastAPI, HTTPException, Depends, Request, Header,UploadFile, File
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn
import os
import json
import uuid
from datetime import datetime
from pathlib import Path

from app.database import init_db, get_db
from app.auth import (
    get_current_user, login_user, register_user, 
    get_user_tokens, delete_token, delete_all_tokens,
    get_user_by_token, create_session
)
from app.models import ProjectSchema
from app.compiler.builder import ProjectBuilder
from app.utils.file_utils import FileUtils

# ============================================================
#  PYDANTIC МОДЕЛИ
# ============================================================

class RegisterData(BaseModel):
    username: str
    email: str
    password: str

class LoginData(BaseModel):
    username: str
    password: str

# ============================================================
#  APP
# ============================================================

app = FastAPI(title="Flux Studio API", version="1.0")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Путь к фронтенду
frontend_path = Path(__file__).parent.parent.parent / "frontend"
if frontend_path.exists():
    app.mount("/styles", StaticFiles(directory=str(frontend_path / "styles")), name="styles")
    app.mount("/scripts", StaticFiles(directory=str(frontend_path / "scripts")), name="scripts")
    app.mount("/static", StaticFiles(directory=str(frontend_path)), name="static")

# Инициализация
file_utils = FileUtils()
builder = ProjectBuilder()

# ============================================================
#  ИНИЦИАЛИЗАЦИЯ БД
# ============================================================

@app.on_event("startup")
async def startup():
    init_db()
    print("✅ Database initialized")

# ============================================================
#  СТРАНИЦЫ
# ============================================================

@app.get("/", response_class=HTMLResponse)
async def home():
    html_path = frontend_path / "index.html"
    if html_path.exists():
        return html_path.read_text(encoding='utf-8')
    return HTMLResponse("<h1>Flux Studio</h1><p>Frontend not found</p>")

@app.get("/register", response_class=HTMLResponse)
async def register_page():
    html_path = frontend_path / "register.html"
    if html_path.exists():
        return html_path.read_text(encoding='utf-8')
    return HTMLResponse("<h1>Register</h1><p>Page not found</p>")

@app.get("/login", response_class=HTMLResponse)
async def login_page():
    html_path = frontend_path / "login.html"
    if html_path.exists():
        return html_path.read_text(encoding='utf-8')
    return HTMLResponse("<h1>Login</h1><p>Page not found</p>")

@app.get("/settings", response_class=HTMLResponse)
async def settings_page():
    html_path = frontend_path / "settings.html"
    if html_path.exists():
        return html_path.read_text(encoding='utf-8')
    return HTMLResponse("<h1>Settings</h1><p>Page not found</p>")

@app.get("/create", response_class=HTMLResponse)
async def create_project_page():
    html_path = frontend_path / "create_project.html"
    if html_path.exists():
        return html_path.read_text(encoding='utf-8')
    return HTMLResponse("<h1>Create Project</h1><p>Page not found</p>")

@app.get("/load", response_class=HTMLResponse)
async def load_project_page():
    html_path = frontend_path / "load_project.html"
    if html_path.exists():
        return html_path.read_text(encoding='utf-8')
    return HTMLResponse("<h1>Load Project</h1><p>Page not found</p>")

@app.get("/admin", response_class=HTMLResponse)
async def admin_panel_page():
    html_path = frontend_path / "admin_panel.html"
    if html_path.exists():
        return html_path.read_text(encoding='utf-8')
    return HTMLResponse("<h1>Admin Panel</h1><p>Page not found</p>")

@app.get("/editor", response_class=HTMLResponse)
async def editor_page():
    html_path = frontend_path / "editor.html"
    if html_path.exists():
        return html_path.read_text(encoding='utf-8')
    return HTMLResponse("<h1>Editor</h1><p>Page not found</p>")

@app.get("/project/{project_id}", response_class=HTMLResponse)
async def project_editor(project_id: str):
    project_data = file_utils.load_project(project_id)
    if not project_data:
        return HTMLResponse(f"""
        <!DOCTYPE html>
        <html>
        <head><title>Project Not Found</title></head>
        <body style="background:#1e1e1e;color:#fff;font-family:Arial;display:flex;justify-content:center;align-items:center;height:100vh;flex-direction:column;">
            <h1>❌ Project Not Found</h1>
            <p>Project with ID "{project_id}" does not exist.</p>
            <a href="/" style="color:#007acc;">Go Home</a>
        </body>
        </html>
        """, status_code=404)
    
    html_path = frontend_path / "editor.html"
    if html_path.exists():
        html_content = html_path.read_text(encoding='utf-8')
        return html_content.replace('</body>', f'<script>window.projectId = "{project_id}";</script></body>')
    return HTMLResponse(f"<h1>Project {project_id}</h1><p>Editor not found</p>")

# ============================================================
#  AUTH РОУТЫ
# ============================================================

@app.post("/api/auth/register")
async def register(data: RegisterData):
    """Регистрация + сразу выдаём токен"""
    try:
        user = register_user(data.username, data.email, data.password)
        return {
            "success": True,
            "user": {
                "id": user["id"],
                "username": user["username"],
                "email": user["email"]
            },
            "token": user["token"],
            "expires_at": user["expires_at"]
        }
    except HTTPException as e:
        raise e
    except Exception as e:
        print(f"❌ Registration error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/auth/login")
async def login(data: LoginData):
    """Вход + выдаём новый токен"""
    try:
        result = login_user(data.username, data.password)
        return {
            "success": True,
            "user_id": result["user_id"],
            "username": result["username"],
            "role": result["role"],
            "token": result["token"],
            "expires_at": result["expires_at"]
        }
    except HTTPException as e:
        raise e
    except Exception as e:
        print(f"❌ Login error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/auth/me")
async def get_me(user: dict = Depends(get_current_user)):
    return {"success": True, "user": user}

@app.get("/api/auth/tokens")
async def get_tokens(user: dict = Depends(get_current_user)):
    """Получить все активные токены пользователя"""
    tokens = get_user_tokens(user["id"])
    return {
        "success": True,
        "count": len(tokens),
        "tokens": tokens
    }

@app.delete("/api/auth/tokens/{token_id}")
async def delete_token_route(token_id: int, user: dict = Depends(get_current_user)):
    """Удалить конкретный токен"""
    delete_token(token_id, user["id"])
    return {"success": True, "message": "Token deleted"}

@app.post("/api/auth/logout")
async def logout(authorization: str = Header(...)):
    """Выход (удаляем текущий токен)"""
    token = authorization.replace("Bearer ", "")
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM tokens WHERE token = ?", (token,))
    conn.commit()
    conn.close()
    return {"success": True, "message": "Logged out"}

@app.post("/api/auth/logout/all")
async def logout_all(user: dict = Depends(get_current_user)):
    """Выйти из ВСЕХ устройств"""
    delete_all_tokens(user["id"])
    return {"success": True, "message": "Logged out from all devices"}

# ============================================================
#  API ПРОЕКТОВ
# ============================================================

@app.get("/api/projects")
async def get_projects_list(user: dict = Depends(get_current_user)):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT id, project_name, created_at, updated_at FROM projects WHERE user_id = ?",
        (user["id"],)
    )
    projects = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return projects

@app.post("/api/projects")
async def create_project(data: dict, user: dict = Depends(get_current_user)):
    try:
        project_name = data.get("name", "MyProject")
        project_id = str(uuid.uuid4())
        now = datetime.now().isoformat()
        
        project_data = {
            "id": project_id,
            "projectName": project_name,
            "project": {
                "meta": {
                    "description": data.get("description", ""),
                    "projecttype": data.get("type", "web"),
                    "framework": data.get("framework", "vanilla"),
                    "colorscheme": data.get("colorScheme", "dark"),
                    "fontfamily": data.get("fontFamily", "inter"),
                    "lastupdated": now
                },
                "pages": {
                    "index": {
                        "title": "Главная",
                        "elements": {}
                    }
                },
                "animationkeyframes": {}
            },
            "created_at": now,
            "updated_at": now
        }
        
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO projects (id, user_id, project_name, project_data, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (project_id, user["id"], project_name, json.dumps(project_data), now, now))
        conn.commit()
        conn.close()
        
        file_utils.save_project(project_id, project_data)
        
        return {
            "success": True,
            "id": project_id,
            "message": f"Project '{project_name}' created successfully"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/project/{project_id}")
async def get_project(project_id: str, user: dict = Depends(get_current_user)):
    conn = get_db()
    cursor = conn.cursor()
    project = cursor.execute('''
        SELECT project_data FROM projects WHERE id = ? AND user_id = ?
    ''', (project_id, user["id"])).fetchone()
    conn.close()
    
    if project:
        return json.loads(project["project_data"])
    
    project_data = file_utils.load_project(project_id)
    if project_data:
        return project_data
    
    raise HTTPException(status_code=404, detail="Project not found")

@app.post("/api/project/{project_id}")
async def save_project_data(project_id: str, data: dict, user: dict = Depends(get_current_user)):
    try:
        conn = get_db()
        cursor = conn.cursor()
        existing = cursor.execute(
            "SELECT id FROM projects WHERE id = ? AND user_id = ?",
            (project_id, user["id"])
        ).fetchone()
        
        now = datetime.now().isoformat()
        data["updated_at"] = now
        
        if existing:
            cursor.execute('''
                UPDATE projects 
                SET project_data = ?, updated_at = ?
                WHERE id = ? AND user_id = ?
            ''', (json.dumps(data), now, project_id, user["id"]))
        else:
            cursor.execute('''
                INSERT INTO projects (id, user_id, project_name, project_data, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (project_id, user["id"], data.get("projectName", "MyProject"), json.dumps(data), now, now))
        
        conn.commit()
        conn.close()
        
        file_utils.save_project(project_id, data)
        
        return {
            "success": True,
            "id": project_id,
            "message": "Project saved successfully",
            "updated_at": now
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/api/project/{project_id}")
async def delete_project(project_id: str, user: dict = Depends(get_current_user)):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        "DELETE FROM projects WHERE id = ? AND user_id = ?",
        (project_id, user["id"])
    )
    conn.commit()
    conn.close()
    
    file_utils.delete_project(project_id)
    
    return {"success": True, "message": "Project deleted"}
# ============================================================
#  UPDATELOG РОУТ
# ============================================================

@app.get("/api/updates")
async def get_updates():
    """Получить список обновлений из файла"""
    updates_path = Path(__file__).parent.parent / "storage" / "updatelog.json"
    if updates_path.exists():
        try:
            with open(updates_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            return []
    return []

# ============================================================
#  AVATAR ЗАГРУЗКА
# ============================================================

@app.post("/api/user/avatar")
async def upload_avatar(
    file: UploadFile = File(...),
    user: dict = Depends(get_current_user)
):
    """Загрузить аватар пользователя"""
    try:
        # Проверяем тип файла
        if not file.content_type.startswith('image/'):
            raise HTTPException(400, "File must be an image")
        
        # Создаём папку для аватаров
        avatar_dir = Path(__file__).parent.parent / "storage" / "avatars"
        avatar_dir.mkdir(parents=True, exist_ok=True)
        
        # Сохраняем файл
        ext = file.filename.split('.')[-1]
        filename = f"{user['id']}_{datetime.now().strftime('%Y%m%d%H%M%S')}.{ext}"
        file_path = avatar_dir / filename
        
        content = await file.read()
        with open(file_path, 'wb') as f:
            f.write(content)
        
        # Обновляем БД
        avatar_path = f"/storage/avatars/{filename}"
        update_user_avatar(user["id"], avatar_path)
        
        return {
            "success": True,
            "avatar": avatar_path,
            "message": "Avatar uploaded successfully"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/user")
async def get_user_info(user: dict = Depends(get_current_user)):
    """Получить информацию о пользователе"""
    return {
        "success": True,
        "user": {
            "id": user["id"],
            "username": user["username"],
            "email": user.get("email", ""),
            "avatar": user.get("avatar", ""),
            "role": user.get("role", "user")
        }
    }
@app.get("/api/status")
async def get_status():
    """Получить статус сервера"""
    return {
        "status": "idle",  # idle, loading, success, error
        "progress": 0,
        "message": "Server is ready",
        "timestamp": datetime.now().isoformat()
    }
# ============================================================
#  ЗАПУСК
# ============================================================

if __name__ == "__main__":
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)