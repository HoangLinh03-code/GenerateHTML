# process/generate.py (REFACTORED)

import json
import os
import re
import logging
from typing import Dict
from api.callAPI import VertexClient

logger = logging.getLogger(__name__)

class ExperimentGenerator:
    def __init__(self, vertex_client: VertexClient, output_dir: str):
        self.client = vertex_client
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)
        
        # Load examples một lần duy nhất
        self.html_example = self._load_example("resources/examples/example.html")
        self.js_example = self._load_example("resources/examples/example.js")

    def _load_example(self, path: str) -> str:
        """Load file ví dụ"""
        try:
            with open(path, 'r', encoding='utf-8') as f:
                return f.read()
        except:
            logger.warning(f"Không tìm thấy example: {path}")
            return ""

    def _clean_code_block(self, text: str, lang: str) -> str:
        """Loại bỏ markdown code block và thẻ HTML bọc ngoài"""
        # Loại bỏ ```language
        pattern = rf"```{lang}?\s*\n?(.*?)\n?```"
        match = re.search(pattern, text, re.DOTALL)
        code = match.group(1).strip() if match else text.strip()
        
        # Loại bỏ thẻ html/head/body nếu có
        if lang == "html":
            for tag in ['<html', '<head', '<body']:
                if tag in code.lower():
                    # Lấy nội dung trong <body>
                    body_match = re.search(r'<body[^>]*>(.*?)</body>', code, re.DOTALL | re.IGNORECASE)
                    if body_match:
                        return body_match.group(1).strip()
        
        return code

    def generate_complete_experiment(self, exp_data: Dict, template_path: str, prompt_path: str):
        """
        Sinh HTML hoàn chỉnh TRONG 1 LẦN GỌI DUY NHẤT
        Không tách thành nhiều bước nữa → giảm token waste
        """
        lesson = exp_data.get('Bài học', 'Unknown')
        logger.info(f"🚀 Sinh HTML cho: {lesson}")
        
        # Đọc template
        with open(template_path, 'r', encoding='utf-8') as f:
            template = f.read()
        
        # Tạo prompt SIÊU TỐI ƯU
        prompt = self._build_optimized_prompt(exp_data)
        
        # Gọi AI 1 lần duy nhất với max_tokens cao
        response = self.client.send_data_to_AI(
            prompt, 
            max_output_tokens=40000,  # Đủ lớn cho toàn bộ HTML+CSS+JS
            temperature=0.1  # Giảm temperature để code ổn định hơn
        )
        
        if not response:
            logger.error("❌ AI không trả về response")
            return None
        
        # Parse response
        html_content, css_content, js_content = self._parse_complete_response(response)
        
        # Validate trước khi lưu
        from process.validate import CodeValidator
        
        is_valid_html, msg = CodeValidator.validate_html(html_content)
        if not is_valid_html:
            logger.error(f"❌ HTML không hợp lệ: {msg}")
            return None
        
        is_valid_js, msg = CodeValidator.validate_js(js_content)
        if not is_valid_js:
            logger.error(f"❌ JS không hợp lệ: {msg}")
            # Thử fix tự động
            js_content = self._auto_fix_js(js_content)
        
        # Inject vào template
        output = template \
            .replace("{{CHAPTER_TITLE}}", str(exp_data.get("Chương", ""))) \
            .replace("{{LESSON_TITLE}}", str(lesson)) \
            .replace("{{CONTENT_SUMMARY}}", str(exp_data.get("Nội dung trong bài học", ""))[:200]) \
            .replace("{{HTML_CONTENT}}", html_content) \
            .replace("{{CSS_CONTENT}}", css_content) \
            .replace("{{JS_CONTENT}}", js_content)
        
        # Lưu file
        safe_name = re.sub(r'[^\w\-]', '_', lesson)
        filename = os.path.join(self.output_dir, f"{safe_name}.html")
        
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(output)
        
        logger.info(f"✅ Đã tạo: {filename}")
        return filename

    def _build_optimized_prompt(self, exp_data: Dict) -> str:
        """
        Tạo prompt SIÊU TỐI ƯU - Ngắn gọn, rõ ràng, có ví dụ
        """
        mo_ta = exp_data.get('Mô tả thí nghiệm thực hiện', '')
        
        # Trích xuất các bước từ mô tả
        steps = re.findall(r'- Bước \d+:.*?(?=- Bước \d+:|$)', mo_ta, re.DOTALL)
        steps_summary = "\n".join([s.strip()[:200] for s in steps[:6]])  # Chỉ lấy 6 bước đầu
        
        prompt = f"""Bạn là chuyên gia tạo thí nghiệm HTML tương tác.

**THÔNG TIN:**
• Bài: {exp_data.get('Bài học')}
• Chương: {exp_data.get('Chương')}

**CÁC BƯỚC THÍ NGHIỆM:**
{steps_summary}

**YÊU CẦU QUAN TRỌNG:**
1. TRẢ VỀ JSON DUY NHẤT theo format:
```json
{{
  "html": "<div>...</div>",
  "css": "body {{ margin: 0; }}",
  "js": "const state = {{}}; function init() {{ ... }}"
}}
```

2. HTML:
   - KHÔNG ĐƯỢC CÓ <html>, <head>, <body>
   - CHỈ CÓ các thẻ <div>, <button>, <canvas>, <svg>...
   - Dùng Tailwind classes (bg-blue-500, p-4, rounded-lg...)
   - Mỗi phần tử PHẢI có id hoặc class rõ ràng

3. CSS:
   - CHỈ viết CSS tùy chỉnh (animations, transitions)
   - Không duplicate Tailwind classes

4. JS:
   - Viết GỌN, LOGIC RÕ RÀNG
   - Khai báo: const state = {{...}}
   - Hàm init() ở cuối, tự động gọi
   - Dùng requestAnimationFrame cho animation
   - KHÔNG DÙNG localStorage/sessionStorage

**VÍ DỤ THAM KHẢO:**
```json
{{
  "html": "<div id='canvas-container' class='relative w-full h-96 bg-gray-900'><canvas id='myCanvas' width='800' height='400'></canvas></div><div class='mt-4 flex gap-2'><button id='btnStart' class='px-4 py-2 bg-green-500 text-white rounded'>Start</button></div>",
  
  "css": "@keyframes glow {{ 0% {{ box-shadow: 0 0 5px blue; }} 100% {{ box-shadow: 0 0 20px blue; }} }}",
  
  "js": "const canvas = document.getElementById('myCanvas'); const ctx = canvas.getContext('2d'); const state = {{ running: false }}; function drawCircle() {{ ctx.clearRect(0,0,800,400); ctx.fillStyle='red'; ctx.arc(100,100,50,0,Math.PI*2); ctx.fill(); }} function init() {{ document.getElementById('btnStart').onclick = () => {{ state.running = true; drawCircle(); }}; }} init();"
}}
```

BẮT ĐẦU TẠO JSON CHO THÍ NGHIỆM TRÊN:"""

        return prompt

    def _parse_complete_response(self, response: str) -> tuple[str, str, str]:
        """Parse JSON response từ AI"""
        try:
            # Tìm JSON block
            match = re.search(r'```json\s*(\{.*?\})\s*```', response, re.DOTALL)
            if match:
                json_str = match.group(1)
            else:
                # Tìm { } đầu tiên
                start = response.find('{')
                end = response.rfind('}')
                if start != -1 and end != -1:
                    json_str = response[start:end+1]
                else:
                    raise ValueError("Không tìm thấy JSON")
            
            data = json.loads(json_str)
            
            html = data.get('html', '')
            css = data.get('css', '')
            js = data.get('js', '')
            
            # Clean code blocks
            html = self._clean_code_block(html, 'html')
            css = self._clean_code_block(css, 'css')
            js = self._clean_code_block(js, 'javascript')
            
            return html, css, js
            
        except Exception as e:
            logger.error(f"❌ Parse error: {e}")
            # Fallback: thử tách theo markers
            return self._fallback_parse(response)

    def _fallback_parse(self, response: str) -> tuple[str, str, str]:
        """Phương án dự phòng nếu JSON parse thất bại"""
        html = self._extract_between(response, '"html":', '"css":')
        css = self._extract_between(response, '"css":', '"js":')
        js = self._extract_between(response, '"js":', '}')
        
        return html, css, js

    def _extract_between(self, text: str, start_marker: str, end_marker: str) -> str:
        """Trích xuất text giữa 2 markers"""
        try:
            start_idx = text.find(start_marker)
            if start_idx == -1:
                return ""
            start_idx += len(start_marker)
            
            end_idx = text.find(end_marker, start_idx)
            if end_idx == -1:
                end_idx = len(text)
            
            content = text[start_idx:end_idx].strip()
            # Loại bỏ dấu ngoặc kép và dấu phẩy
            content = content.strip(' ",')
            return content
        except:
            return ""

    def _auto_fix_js(self, js_code: str) -> str:
        """Tự động fix một số lỗi JS phổ biến"""
        # Loại bỏ localStorage/sessionStorage
        js_code = re.sub(r'localStorage\.[a-zA-Z]+\([^)]*\)', '/* localStorage removed */', js_code)
        js_code = re.sub(r'sessionStorage\.[a-zA-Z]+\([^)]*\)', '/* sessionStorage removed */', js_code)
        
        # Thêm init() call nếu thiếu
        if 'init()' not in js_code and 'function init(' in js_code:
            js_code += '\n\ninit();'
        
        return js_code

    def process_experiment(self, exp_data: Dict, template_path: str, prompt_path: str):
        """Wrapper cho backward compatibility"""
        return self.generate_complete_experiment(exp_data, template_path, prompt_path)