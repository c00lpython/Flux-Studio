import json
import shutil
from pathlib import Path
from typing import Optional, Dict, Any, List

class FileUtils:
    def __init__(self):
        self.projects_dir = Path("storage/projects")
        self.projects_dir.mkdir(parents=True, exist_ok=True)
    
    def save_project(self, project_id: str, project_data: Dict[str, Any]) -> Path:
        """Сохраняет проект в JSON файл"""
        project_file = self.projects_dir / f"{project_id}.json"
        with open(project_file, 'w', encoding='utf-8') as f:
            json.dump(project_data, f, ensure_ascii=False, indent=2)
        return project_file
    
    def load_project(self, project_id: str) -> Optional[Dict[str, Any]]:
        """Загружает проект из JSON файла"""
        project_file = self.projects_dir / f"{project_id}.json"
        if not project_file.exists():
            return None
        try:
            with open(project_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"❌ Error loading project {project_id}: {e}")
            return None
    
    def delete_project(self, project_id: str) -> bool:
        """Удаляет проект"""
        project_file = self.projects_dir / f"{project_id}.json"
        if project_file.exists():
            project_file.unlink()
            return True
        return False
    
    def list_projects(self) -> List[str]:
        """Возвращает список ID всех проектов"""
        return [f.stem for f in self.projects_dir.glob("*.json")]
    
    def get_project_meta(self, project_id: str) -> Optional[Dict[str, Any]]:
        """Возвращает только мета-данные проекта (без элементов)"""
        project = self.load_project(project_id)
        if project:
            return {
                "id": project_id,
                "name": project.get("projectName", ""),
                "meta": project.get("project", {}).get("meta", {}),
                "created_at": project.get("created_at", ""),
                "updated_at": project.get("updated_at", "")
            }
        return None