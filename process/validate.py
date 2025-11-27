# process/validator.py
import re
import logging
from bs4 import BeautifulSoup
import esprima  # Cài: pip install esprima

logger = logging.getLogger(__name__)

class CodeValidator:
    """Validate HTML/CSS/JS trước khi lưu file"""
    
    @staticmethod
    def validate_html(html_code: str) -> tuple[bool, str]:
        """Kiểm tra HTML có hợp lệ không"""
        try:
            soup = BeautifulSoup(html_code, 'html.parser')
            
            # Kiểm tra không có thẻ html/head/body bọc ngoài
            if soup.find('html') or soup.find('head') or soup.find('body'):
                return False, "HTML không được chứa thẻ <html>, <head>, <body>"
            
            # Kiểm tra có ít nhất 1 div
            if not soup.find('div'):
                return False, "HTML phải chứa ít nhất 1 thẻ <div>"
                
            return True, "OK"
        except Exception as e:
            return False, f"HTML parse error: {str(e)}"
    
    @staticmethod
    def validate_js(js_code: str) -> tuple[bool, str]:
        """Kiểm tra JS syntax"""
        try:
            esprima.parseScript(js_code)
            
            # Kiểm tra không dùng localStorage/sessionStorage
            if 'localStorage' in js_code or 'sessionStorage' in js_code:
                return False, "JS không được dùng localStorage/sessionStorage"
                
            return True, "OK"
        except Exception as e:
            return False, f"JS syntax error: {str(e)}"
    
    @staticmethod
    def validate_css(css_code: str) -> tuple[bool, str]:
        """Kiểm tra CSS cơ bản"""
        try:
            # Kiểm tra dấu {} cân bằng
            if css_code.count('{') != css_code.count('}'):
                return False, "CSS có dấu {} không cân bằng"
            return True, "OK"
        except Exception as e:
            return False, f"CSS error: {str(e)}"