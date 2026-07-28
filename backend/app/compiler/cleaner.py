import re

class CodeCleaner:
    @staticmethod
    def clean_html(html_content: str) -> str:
        """Очистить HTML"""
        html_content = re.sub(r'\s+', ' ', html_content)
        html_content = re.sub(r'\s+=\s*""', '', html_content)
        return html_content.strip()
    
    @staticmethod
    def clean_css(css_content: str) -> str:
        """Очистить CSS"""
        css_content = re.sub(r'[^{]+\{\s*\}', '', css_content)
        css_content = re.sub(r'\s+', ' ', css_content)
        return css_content.strip()