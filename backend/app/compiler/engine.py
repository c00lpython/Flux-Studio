import json
from pathlib import Path

class CompilerEngine:
    def __init__(self):
        self.templates = self._load_templates()
    
    def _load_templates(self):
        """Загрузить шаблоны из compilelib.json"""
        lib_path = Path(__file__).parent.parent / "lib" / "compilelib.json"
        try:
            with open(lib_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            return {
                "heading": "<h{class_level} class=\"{class_name}\" id=\"{id}\" style=\"{style}\">{content}</h{class_level}>",
                "text": "<p class=\"{class_name}\" id=\"{id}\" style=\"{style}\">{content}</p>",
                "button": "<button class=\"{class_name}\" id=\"{id}\" style=\"{style}\" onclick=\"{onclick}\">{content}</button>",
                "image": "<img class=\"{class_name}\" id=\"{id}\" style=\"{style}\" src=\"{src}\" alt=\"{alt}\">",
                "container": "<div class=\"{class_name}\" id=\"{id}\" style=\"{style}\">{content}</div>",
                "link": "<a class=\"{class_name}\" id=\"{id}\" style=\"{style}\" href=\"{href}\">{content}</a>",
                "input": "<input class=\"{class_name}\" id=\"{id}\" style=\"{style}\" type=\"{input_type}\" placeholder=\"{placeholder}\" value=\"{value}\">",
                "textarea": "<textarea class=\"{class_name}\" id=\"{id}\" style=\"{style}\" rows=\"{rows}\">{content}</textarea>",
                "list": "<ul class=\"{class_name}\" id=\"{id}\" style=\"{style}\">{items}</ul>"
            }
    
    def compile_element(self, element_type: str, element_data: dict) -> str:
        """Скомпилировать элемент в HTML"""
        template = self.templates.get(element_type)
        if not template:
            raise ValueError(f"Unknown element type: {element_type}")
        
        format_data = {}
        for key, value in element_data.items():
            format_data[key] = value or ""
        
        if element_type == "heading":
            level = element_data.get("class_level", "1")
            format_data["class_level"] = level
        
        try:
            return template.format(**format_data)
        except KeyError as e:
            missing_key = str(e).strip("'")
            format_data[missing_key] = ""
            return template.format(**format_data)