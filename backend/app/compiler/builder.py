import os
import zipfile
import json
from pathlib import Path
from datetime import datetime
import shutil

from app.compiler.engine import CompilerEngine
from app.compiler.cleaner import CodeCleaner

class ProjectBuilder:
    def __init__(self):
        self.compiler = CompilerEngine()
        self.cleaner = CodeCleaner()
    
    def build_project(self, project_data: dict, project_id: str) -> str:
        """Собрать проект в ZIP"""
        temp_dir = Path(f"storage/temp/{project_id}")
        temp_dir.mkdir(parents=True, exist_ok=True)
        
        try:
            pages = project_data.get("pages", {})
            for page_name, page_data in pages.items():
                html_content = self._build_page(page_data)
                page_file = temp_dir / f"{page_name}.html"
                page_file.write_text(html_content, encoding='utf-8')
            
            css_content = self._generate_css(project_data)
            css_file = temp_dir / "styles.css"
            css_file.write_text(css_content, encoding='utf-8')
            
            js_content = self._generate_js(project_data)
            js_file = temp_dir / "scripts.js"
            js_file.write_text(js_content, encoding='utf-8')
            
            # index.html
            index_content = self._generate_index(pages)
            index_file = temp_dir / "index.html"
            index_file.write_text(index_content, encoding='utf-8')
            
            # Создать ZIP
            zip_path = f"storage/exports/{project_id}.zip"
            Path("storage/exports").mkdir(parents=True, exist_ok=True)
            
            with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                for file_path in temp_dir.glob("*"):
                    zipf.write(file_path, file_path.name)
            
            return zip_path
            
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)
    
    def _build_page(self, page_data: dict) -> str:
        elements_html = []
        elements = page_data.get("elements", {})
        
        for elem_id, elem_data in elements.items():
            elem_type = elem_data.get("type", "container")
            html = self.compiler.compile_element(elem_type, elem_data)
            elements_html.append(html)
        
        page_title = page_data.get("title", "Page")
        content = "\n".join(elements_html)
        
        return f"""<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{page_title}</title>
    <link rel="stylesheet" href="styles.css">
</head>
<body>
    {content}
    <script src="scripts.js"></script>
</body>
</html>"""
    
    def _generate_css(self, project_data: dict) -> str:
        css_parts = []
        for page_name, page_data in project_data.get("pages", {}).items():
            for elem_id, elem_data in page_data.get("elements", {}).items():
                style = elem_data.get("style", "")
                class_name = elem_data.get("class_name", "")
                if class_name:
                    css_parts.append(f".{class_name} {{ {style} }}")
                if elem_data.get("id"):
                    css_parts.append(f"#{elem_data.get('id')} {{ {style} }}")
        return self.cleaner.clean_css("\n".join(css_parts))
    
    def _generate_js(self, project_data: dict) -> str:
        js_parts = []
        for page_name, page_data in project_data.get("pages", {}).items():
            for elem_id, elem_data in page_data.get("elements", {}).items():
                onclick = elem_data.get("onclick", "")
                if onclick:
                    js_parts.append(f"// Element: {elem_id}")
                    js_parts.append(onclick)
        return "\n".join(js_parts)
    
    def _generate_index(self, pages: dict) -> str:
        links = []
        for page_name in pages.keys():
            links.append(f'<li><a href="{page_name}.html">{page_name}</a></li>')
        
        return f"""<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Flux Studio Project</title>
    <style>
        body {{ font-family: Arial, sans-serif; padding: 40px; background: #1a1a2e; color: white; }}
        h1 {{ text-align: center; }}
        ul {{ list-style: none; padding: 0; display: flex; justify-content: center; gap: 20px; }}
        a {{ color: #e94560; text-decoration: none; font-size: 18px; padding: 10px 20px; border: 1px solid #e94560; border-radius: 5px; transition: all 0.3s; }}
        a:hover {{ background: #e94560; color: white; }}
    </style>
</head>
<body>
    <h1>🚀 Flux Studio Project</h1>
    <p style="text-align: center;">Выберите страницу для просмотра:</p>
    <ul>
        {''.join(links)}
    </ul>
</body>
</html>"""