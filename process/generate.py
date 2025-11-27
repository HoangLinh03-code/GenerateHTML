# process/generate.py

import json
import os
import re
import logging
import ast
from typing import Dict
from api.callAPI import VertexClient
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class ExperimentGenerator:
    def __init__(self, vertex_client: VertexClient, output_dir: str):
        self.client = vertex_client
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)
        self.global_constraints = "" 

    def _read_file(self, file_path: str) -> str:
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return f.read()
        except FileNotFoundError:
            logger.warning(f"⚠️ File not found: {file_path}")
            return ""

    def _load_constraints(self, prompt_path: str):
        content = self._read_file(prompt_path)
        if not content:
            self.global_constraints = "Yêu cầu: HTML5, Tailwind CSS, JS ES6+, Comment tiếng Việt."
            return
        lines = [line for line in content.split('\n') if '$' not in line]
        self.global_constraints = "\n".join(lines)
        logger.info(f"📝 Đã load Constraints từ: {os.path.basename(prompt_path)}")

    def _clean_json_string(self, json_str: str) -> str:
        json_str = re.sub(r"//.*", "", json_str)
        json_str = re.sub(r"/\*.*?\*/", "", json_str, flags=re.DOTALL)
        json_str = re.sub(r",\s*([\]}])", r"\1", json_str)
        return json_str.strip()

    def _balance_json(self, json_str: str) -> str:
        json_str = json_str.strip()
        if json_str.count('"') % 2 != 0: json_str += '"'
        json_str = json_str.rstrip(',')
        if json_str.endswith(':'): json_str += ' null'
        elif re.search(r'"[^"]+"$', json_str):
            last_colon = json_str.rfind(':')
            last_comma_or_brace = max(json_str.rfind(','), json_str.rfind('{'), json_str.rfind('['))
            if last_comma_or_brace > last_colon: json_str += ': null'
        
        open_braces = json_str.count('{'); close_braces = json_str.count('}')
        open_brackets = json_str.count('['); close_brackets = json_str.count(']')
        json_str += ']' * (open_brackets - close_brackets)
        json_str += '}' * (open_braces - close_braces)
        return json_str

    def _extract_json(self, text: str) -> dict:
        match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', text, re.DOTALL)
        if match: json_str = match.group(1)
        else:
            start_idx = text.find('{')
            if start_idx != -1:
                end_idx = text.rfind('```')
                json_str = text[start_idx:end_idx] if end_idx > start_idx else text[start_idx:]
            else: return {}

        clean_str = self._clean_json_string(json_str)
        try: return json.loads(clean_str)
        except: pass
        
        repaired_str = self._balance_json(clean_str)
        try: return json.loads(repaired_str)
        except: pass
        
        try:
            py_str = repaired_str.replace("null", "None").replace("true", "True").replace("false", "False")
            return ast.literal_eval(py_str)
        except Exception: return {}

    def _strip_outer_html(self, html_code: str) -> str:
        """Loại bỏ thẻ html, head, body bao ngoài nếu AI lỡ sinh ra"""
        # Tìm nội dung trong <body>...</body>
        body_match = re.search(r'<body[^>]*>(.*?)</body>', html_code, re.DOTALL | re.IGNORECASE)
        if body_match:
            return body_match.group(1).strip()
        
        # Nếu không có body nhưng có <html>, lấy nội dung trong html
        html_match = re.search(r'<html[^>]*>(.*?)</html>', html_code, re.DOTALL | re.IGNORECASE)
        if html_match:
            # Nếu trong html không có body, trả về nguyên cục đó (trừ thẻ html)
            return html_match.group(1).strip()
            
        return html_code

    def _extract_code(self, text: str, lang: str) -> str:
        pattern = rf"```{lang}?\n(.*?)\n```"
        match = re.search(pattern, text, re.DOTALL)
        code = match.group(1).strip() if match else text.strip()
        
        # Xử lý đặc biệt cho HTML: Lột bỏ vỏ bọc nếu có
        if lang == "html":
            code = self._strip_outer_html(code)
            
        return code

    # --- WORKFLOW ---

    def generate_blueprint(self, exp_data: Dict) -> Dict:
        prompt = f"""
        Bạn là Kiến trúc sư phần mềm.
        Nhiệm vụ: Tạo JSON Blueprint cho thí nghiệm: {exp_data.get('Bài học')}.
        Mô tả: {exp_data.get('Mô tả thí nghiệm thực hiện')}

        QUAN TRỌNG:
        1. Tiết kiệm Token tối đa.
        2. KHÔNG bao gồm 'description', 'version'.
        3. KHÔNG comment trong JSON.

        OUTPUT FORMAT (JSON Only):
        {{
            "dom_ids": {{ "canvas": "main-canvas", "startBtn": "btn-start" }},
            "state_vars": [ {{ "name": "isRunning", "default": false }} ],
            "functions": ["init", "update", "render"]
        }}
        """
        resp = self.client.send_data_to_AI(prompt, max_output_tokens=4096)
        return self._extract_json(resp)

    def generate_html_css(self, exp_data: Dict, blueprint: Dict) -> tuple[str, str]:
        bp_str = json.dumps(blueprint, indent=2, ensure_ascii=False)
        html_prompt = f"""
        {self.global_constraints}
        BLUEPRINT: {bp_str}
        MÔ TẢ: {exp_data.get('Mô tả thí nghiệm thực hiện')}
        
        Nhiệm vụ: Viết HTML cho #simulation-area.
        YÊU CẦU QUAN TRỌNG:
        - CHỈ TRẢ VỀ CÁC THẺ DIV/BUTTON... BÊN TRONG, KHÔNG VIẾT THẺ <html>, <head>, <body>.
        - Dùng Tailwind CSS.
        """
        html_resp = self.client.send_data_to_AI(html_prompt, max_output_tokens=4096)
        
        css_prompt = f"""
        {self.global_constraints}
        BLUEPRINT: {bp_str}
        Nhiệm vụ: Viết CSS tùy chỉnh (ngắn gọn).
        """
        css_resp = self.client.send_data_to_AI(css_prompt, max_output_tokens=2048)
        
        return self._extract_code(html_resp, "html"), self._extract_code(css_resp, "css")

    def generate_js_logic(self, exp_data: Dict, blueprint: Dict) -> str:
        bp_str = json.dumps(blueprint, indent=2, ensure_ascii=False)
        prompt = f"""
        {self.global_constraints}
        BLUEPRINT: {bp_str}
        MÔ TẢ: {exp_data.get('Mô tả thí nghiệm thực hiện')}
        
        Nhiệm vụ: Viết CORE LOGIC JS.
        Yêu cầu:
        - Viết code GỌN GÀNG, TỐI ƯU HÓA TOKEN (bỏ comment thừa).
        - Khai báo State và hàm updatePhysics.
        """
        resp = self.client.send_data_to_AI(prompt, max_output_tokens=8192)
        return self._extract_code(resp, "javascript")

    def generate_js_ui(self, exp_data: Dict, blueprint: Dict, js_logic: str) -> str:
        bp_str = json.dumps(blueprint, indent=2, ensure_ascii=False)
        prompt = f"""
        {self.global_constraints}
        LOGIC ĐÃ CÓ:
        {js_logic}
        BLUEPRINT: {bp_str}
        
        Nhiệm vụ: Viết UI & EVENTS JS.
        Yêu cầu:
        - QUAN TRỌNG: CODE PHẢI NGẮN GỌN ĐỂ KHÔNG BỊ CẮT CỤT (TRUNCATED).
        - Dùng arrow function khi có thể.
        - Init DOM, Render, Events.
        - Đảm bảo hàm init() được gọi ở cuối.
        """
        resp = self.client.send_data_to_AI(prompt, max_output_tokens=8192)
        return self._extract_code(resp, "javascript")

    def process_experiment(self, exp_data: Dict, template_path: str, prompt_path: str):
        lesson = exp_data.get('Bài học', 'Unknown')
        logger.info(f"🚀 Xử lý: {lesson}")
        self._load_constraints(prompt_path)
        
        try:
            blueprint = self.generate_blueprint(exp_data)
            if not blueprint: return None
            
            html, css = self.generate_html_css(exp_data, blueprint)
            js_logic = self.generate_js_logic(exp_data, blueprint)
            js_ui = self.generate_js_ui(exp_data, blueprint, js_logic)
            
            # Assembly
            full_js = f"/* {os.path.basename(prompt_path)} */\n{js_logic}\n{js_ui}"
            
            template = self._read_file(template_path)
            output = template
            replacements = {
                "{{CHAPTER_TITLE}}": str(exp_data.get("Chương", "")),
                "{{LESSON_TITLE}}": str(lesson),
                "{{CONTENT_SUMMARY}}": str(exp_data.get("Nội dung trong bài học", ""))[:200],
                "{{HTML_CONTENT}}": html,
                "{{CSS_CONTENT}}": css,
                "{{JS_CONTENT}}": full_js
            }
            for k, v in replacements.items():
                output = output.replace(k, v)
            
            safe_name = re.sub(r'[^\w\-]', '_', lesson)
            filename = os.path.join(self.output_dir, f"{safe_name}.html")
            with open(filename, 'w', encoding='utf-8') as f: f.write(output)
            
            logger.info(f"✅ Xong: {filename}")
            return filename
        except Exception as e:
            logger.error(f"❌ Lỗi: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return None