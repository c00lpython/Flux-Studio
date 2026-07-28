from pydantic import BaseModel, Field
from typing import Dict, Optional, Any, List
from datetime import datetime

# ============================================
# META
# ============================================

class MemberModel(BaseModel):
    code: Optional[str] = ""
    link: Optional[str] = ""

class MetaModel(BaseModel):
    description: str = ""
    projecttype: str = ""
    framework: str = ""
    colorscheme: str = ""
    fontfamily: str = ""
    lastupdated: str = ""
    members: MemberModel = Field(default_factory=MemberModel)

# ============================================
# ELEMENTS
# ============================================

class ElementModel(BaseModel):
    Type: str = "Text"
    content: str = ""
    # Все CSS свойства
    color: Optional[str] = ""
    font_size: Optional[str] = ""
    font_weight: Optional[str] = ""
    font_family: Optional[str] = ""
    background_color: Optional[str] = ""
    padding: Optional[str] = ""
    margin: Optional[str] = ""
    border: Optional[str] = ""
    border_radius: Optional[str] = ""
    width: Optional[str] = ""
    height: Optional[str] = ""
    position: Optional[str] = ""
    left: Optional[str] = ""
    top: Optional[str] = ""
    display: Optional[str] = ""
    text_align: Optional[str] = ""
    # Специфичные для элементов
    src: Optional[str] = ""  # для image
    alt: Optional[str] = ""  # для image
    href: Optional[str] = ""  # для link
    onclick: Optional[str] = ""  # для button
    placeholder: Optional[str] = ""  # для input
    input_type: Optional[str] = ""  # для input
    rows: Optional[int] = 3  # для textarea
    items: Optional[str] = ""  # для list
    class_name: Optional[str] = ""  # CSS класс
    id: Optional[str] = ""  # HTML id

    def to_css(self) -> str:
        """Преобразует свойства в CSS строку"""
        css_map = {
            'color': 'color',
            'font_size': 'font-size',
            'font_weight': 'font-weight',
            'font_family': 'font-family',
            'background_color': 'background-color',
            'padding': 'padding',
            'margin': 'margin',
            'border': 'border',
            'border_radius': 'border-radius',
            'width': 'width',
            'height': 'height',
            'position': 'position',
            'left': 'left',
            'top': 'top',
            'display': 'display',
            'text_align': 'text-align'
        }
        css_parts = []
        for field, css_prop in css_map.items():
            value = getattr(self, field, None)
            if value:
                css_parts.append(f"{css_prop}:{value}")
        return ";".join(css_parts)

    def to_dict(self) -> dict:
        """Преобразует в словарь для JSON"""
        data = self.dict(exclude_none=True)
        return {k: v for k, v in data.items() if v and v != ""}

# ============================================
# PAGES
# ============================================

class PageModel(BaseModel):
    title: str = "Untitled Page"
    elements: Dict[str, ElementModel] = Field(default_factory=dict)

# ============================================
# ANIMATION KEYFRAMES
# ============================================

class KeyframeModel(BaseModel):
    loop: bool = True
    triggerid: str = ""
    time: str = ""  # "PROPERTY:VALUE:FUNCTION,PROPERTY2:VALUE2"

class AnimationModel(BaseModel):
    keyframes: Dict[str, KeyframeModel] = Field(default_factory=dict)

# ============================================
# FULL PROJECT
# ============================================

class ProjectModel(BaseModel):
    meta: MetaModel = Field(default_factory=MetaModel)
    pages: Dict[str, PageModel] = Field(default_factory=dict)
    animationkeyframes: Dict[str, KeyframeModel] = Field(default_factory=dict)

# ============================================
# PROJECT SCHEMA (для API)
# ============================================

class ProjectSchema(BaseModel):
    id: Optional[str] = None
    projectName: str = "MyProject"
    project: ProjectModel = Field(default_factory=ProjectModel)
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

    @classmethod
    def create_default(cls, name: str = "MyProject"):
        """Создает проект с дефолтной структурой"""
        return cls(
            projectName=name,
            project=ProjectModel(
                meta=MetaModel(
                    description="",
                    projecttype="web",
                    framework="vanilla",
                    colorscheme="dark",
                    fontfamily="inter",
                    lastupdated=datetime.now().isoformat(),
                    members=MemberModel(code="", link="")
                ),
                pages={
                    "index": PageModel(
                        title="Главная",
                        elements={
                            "text_1": ElementModel(
                                Type="Text",
                                content="Hello! This is a test page!",
                                color="#333333",
                                font_size="18px",
                                font_family="Arial, sans-serif"
                            )
                        }
                    )
                },
                animationkeyframes={}
            )
        )