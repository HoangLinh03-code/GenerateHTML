# process/generate_fixed.py - FIXED VERSION

import json
import os
import re
import logging
from typing import Dict, Tuple
from api.callAPI import VertexClient
from process.prompt import (
    PROMPT_REFINE_CHEMISTRY,
    PROMPT_REFINE_PHYSICS,
    PROMPT_REFINE_BIOLOGY,
    PROMPT_REFINE_MATH
)

logger = logging.getLogger(__name__)

class EnhancedExperimentGenerator:
    """Generator với template layout tối ưu - không bị dính bó"""
    
    def __init__(self, vertex_client: VertexClient, output_dir: str):
        self.client = vertex_client
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)
        
    def generate_complete_experiment(self, exp_data: Dict, template_path: str, prompt_path: str):
        """
        Sinh HTML với blueprint approach
        """
        lesson = exp_data.get('Bài học', 'Unknown')
        subject = exp_data.get('Môn học', 'Unknown').upper()
        
        logger.info(f"🚀 Generating: {lesson} ({subject})")
        
        # Load prompt template
        with open(prompt_path, 'r', encoding='utf-8') as f:
            base_prompt = f.read()
        
        # Tạo prompt hoàn chỉnh
        full_prompt = self._build_generation_prompt(exp_data, base_prompt)
        
        # Call AI
        response = self.client.send_data_to_AI(
            full_prompt,
            max_output_tokens=30000,
            temperature=0.2
        )
        
        if not response:
            logger.error("❌ AI response failed")
            return None
        
        # Parse response
        html, css, js = self._parse_response(response)
        
        if not html or not js:
            logger.error("❌ Invalid response format")
            return None
        
        # Validate
        from process.validate import CodeValidator
        
        is_valid_html, msg = CodeValidator.validate_html(html)
        if not is_valid_html:
            logger.warning(f"⚠️ HTML validation: {msg}")
            html = self._fix_html_structure(html)
        
        is_valid_js, msg = CodeValidator.validate_js(js)
        if not is_valid_js:
            logger.warning(f"⚠️ JS validation: {msg}")
            js = self._auto_fix_js(js)
        
        # AI refinement (optional)
        if self._should_refine(exp_data):
            html, css, js = self._ai_refine_output(html, css, js, exp_data)
        
        # Inject vào template
        output = self._inject_into_template(
            template_path,
            exp_data,
            html,
            css,
            js
        )
        
        # Save
        safe_name = re.sub(r'[^\w\-]', '_', lesson)
        filename = os.path.join(self.output_dir, f"{safe_name}.html")
        
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(output)
        
        logger.info(f"✅ Generated: {filename}")
        return filename

    def _build_generation_prompt(self, exp_data: Dict, base_prompt: str) -> str:
        """Xây dựng prompt với context đầy đủ"""
        
        subject = exp_data.get('Môn học', '').upper()
        lesson = exp_data.get('Bài học', '')
        chapter = exp_data.get('Chương', '')
        description = exp_data.get('Mô tả thí nghiệm thực hiện', '')[:1500]
        content = exp_data.get('Nội dung trong bài học', '')[:500]
        
        # Chọn theme và icons theo môn học
        subject_config = self._get_subject_config(subject)
        
        prompt = f"""
{base_prompt}

===========================================
THÔNG TIN BÀI HỌC
===========================================

**Môn học:** {subject}
**Chương:** {chapter}
**Bài học:** {lesson}

**Nội dung tóm tắt:**
{content}

**Mô tả thí nghiệm chi tiết:**
{description}

===========================================
YÊU CẦU CỤ THỂ CHO BÀI NÀY
===========================================

1. **Theme & Colors:** {subject_config['theme']}
   - Primary: {subject_config['primary_color']}
   - Secondary: {subject_config['secondary_color']}
   - Accent: {subject_config['accent_color']}

2. **Icons phù hợp:** {' '.join(subject_config['icons'])}

3. **Layout Requirements:**
   - Phải có full-width responsive layout
   - Canvas/simulation area chiếm 60-70% màn hình
   - Controls/info panel riêng biệt, rõ ràng
   - Không bị overlap hoặc dính bó các phần tử

4. **Structure Example:**
```html
<div class="w-full max-w-7xl mx-auto space-y-6">
  <!-- Main simulation area -->
  <div class="bg-white rounded-2xl shadow-2xl p-6">
    <canvas id="mainCanvas" class="w-full"></canvas>
  </div>
  
  <!-- Controls panel -->
  <div class="bg-white rounded-xl shadow-lg p-4">
    <div class="flex flex-wrap gap-4 justify-center">
      <button>...</button>
    </div>
  </div>
  
  <!-- Info panels (if needed) -->
  <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
    <div class="bg-gradient-to-br from-blue-50 to-indigo-50 rounded-xl p-4">
      <h3>Thông số</h3>
      <div id="metrics">...</div>
    </div>
    <div id="theory-content" class="bg-gradient-to-br from-purple-50 to-pink-50 rounded-xl p-4">
      <!-- Knowledge content -->
    </div>
  </div>
</div>
```

5. **JavaScript Requirements:**
   - Phải có CONFIG object rõ ràng
   - State management với các trạng thái: idle, running, paused, complete
   - requestAnimationFrame với deltaTime
   - Event handlers clean, không inline
   - Init function tự động chạy

6. **Interactions:**
   - Buttons phải có hover effects
   - Canvas cập nhật smooth (60fps)
   - Visual feedback cho mọi action
   - Progress indicators nếu cần

===========================================
OUTPUT FORMAT (QUAN TRỌNG)
===========================================

Trả về JSON duy nhất với format:

```json
{{
  "html": "<!-- Full HTML structure, NO <html>/<head>/<body> tags -->",
  "css": "/* Custom CSS only, NO basic styling */",
  "js": "// Complete working JavaScript with init() call"
}}
```

**CRITICAL RULES:**
- HTML: Chỉ có <div>, <canvas>, <button>, <input>, <select>, <p>, <span>
- CSS: Chỉ @keyframes và custom effects (colors/spacing dùng Tailwind)
- JS: Phải có init() và tự gọi init() ở cuối
- NO localStorage/sessionStorage
- NO jQuery hoặc external libs
- Canvas size phải được set trong JS init

Hãy tạo một bài học tương tác chất lượng cao, đẹp mắt và hoạt động mượt mà!
"""
        
        return prompt

    def _get_subject_config(self, subject: str) -> Dict:
        """Cấu hình theme theo môn học"""
        configs = {
            'TOÁN': {
                'theme': 'Modern Blue/Cyan Gradient',
                'primary_color': '#3b82f6',
                'secondary_color': '#06b6d4',
                'accent_color': '#0284c7',
                'icons': ['📐', '📊', '📈', '➕', '➖', '✖️', '➗', '∞', '√']
            },
            'HÓA': {
                'theme': 'Vibrant Purple/Pink Gradient',
                'primary_color': '#a855f7',
                'secondary_color': '#ec4899',
                'accent_color': '#d946ef',
                'icons': ['🧪', '⚗️', '🔬', '🌡️', '💧', '🔥', '❄️', '⚛️', '💊']
            },
            'LÝ': {
                'theme': 'Electric Indigo/Blue',
                'primary_color': '#6366f1',
                'secondary_color': '#3b82f6',
                'accent_color': '#0ea5e9',
                'icons': ['⚡', '🧲', '💡', '🔊', '🌊', '⚙️', '🎯', '🚀', '🔋']
            },
            'SINH': {
                'theme': 'Natural Green/Emerald',
                'primary_color': '#10b981',
                'secondary_color': '#14b8a6',
                'accent_color': '#059669',
                'icons': ['🧬', '🦠', '🔬', '🌱', '🌿', '🫀', '🫁', '🦋', '🥚']
            }
        }
        
        return configs.get(subject, configs['HÓA'])

    def _should_refine(self, exp_data: Dict) -> bool:
        """Quyết định có nên refine không"""
        # Refine nếu mô tả phức tạp hoặc môn lý/hóa
        description = exp_data.get('Mô tả thí nghiệm thực hiện', '')
        subject = exp_data.get('Môn học', '').upper()
        
        return len(description) > 500 or subject in ['HÓA', 'LÝ']

    def _ai_refine_output(self, html: str, css: str, js: str, exp_data: Dict) -> Tuple[str, str, str]:
        """AI post-processing để enhance output"""
        
        subject = exp_data.get("Môn học", "HÓA").upper()
        
        # Chọn prompt refinement
        if subject == "LÝ":
            prompt_template = PROMPT_REFINE_PHYSICS
        elif subject == "SINH":
            prompt_template = PROMPT_REFINE_BIOLOGY
        elif subject == "TOÁN":
            prompt_template = PROMPT_REFINE_MATH
        else:
            prompt_template = PROMPT_REFINE_CHEMISTRY
        
        # Escape any remaining braces in code để tránh format() error
        html_escaped = html.replace('{', '{{').replace('}', '}}')
        css_escaped = css.replace('{', '{{').replace('}', '}}')
        js_escaped = js.replace('{', '{{').replace('}', '}}')
        
        try:
            prompt = prompt_template.format(
                LESSON=exp_data.get("Bài học", ""),
                CHAPTER=exp_data.get("Chương", ""),
                DESCRIPTION=exp_data.get("Mô tả thí nghiệm thực hiện", "")[:1000],
                HTML=html_escaped,
                CSS=css_escaped,
                JS=js_escaped
            )
        except KeyError as e:
            logger.error(f"❌ Prompt format error: {e}")
            logger.warning("⚠️ Skipping refinement due to format error")
            return html, css, js
        
        logger.info(f"🧠 AI refining for {subject}...")
        
        response = self.client.send_data_to_AI(
            prompt,
            temperature=0.15,
            max_output_tokens=25000
        )
        
        if not response:
            logger.warning("⚠️ Refine failed, using original")
            return html, css, js
        
        # Parse
        try:
            refined_html, refined_css, refined_js = self._parse_response(response)
            
            # Validate
            from process.validate import CodeValidator
            
            if not CodeValidator.validate_html(refined_html)[0]:
                raise ValueError("Refined HTML invalid")
            
            logger.info("✅ Refinement successful")
            return refined_html, refined_css, refined_js
            
        except Exception as e:
            logger.error(f"❌ Refine parse error: {e}")
            return html, css, js

    def _parse_response(self, response: str) -> Tuple[str, str, str]:
        """Parse JSON response từ AI"""
        try:
            # Tìm JSON block
            json_match = re.search(r'```json\s*(\{.*?\})\s*```', response, re.DOTALL | re.IGNORECASE)
            if json_match:
                data = json.loads(json_match.group(1))
            else:
                # Fallback: tìm {} object
                start = response.find('{')
                end = response.rfind('}')
                if start != -1 and end != -1:
                    data = json.loads(response[start:end+1])
                else:
                    raise ValueError("No JSON found in response")
            
            html = self._clean_code(data.get('html', ''), 'html')
            css = self._clean_code(data.get('css', ''), 'css')
            js = self._clean_code(data.get('js', ''), 'js')
            
            return html, css, js
            
        except Exception as e:
            logger.error(f"❌ Parse error: {e}")
            return "", "", ""

    def _clean_code(self, code: str, lang: str) -> str:
        """Clean code blocks"""
        if not code:
            return ""
        
        # Remove markdown code blocks
        pattern = rf"```{lang}?\s*\n?(.*?)\n?```"
        match = re.search(pattern, code, re.DOTALL | re.IGNORECASE)
        if match:
            code = match.group(1)
        
        return code.strip()

    def _fix_html_structure(self, html: str) -> str:
        """Auto-fix HTML structure issues"""
        # Đảm bảo có root container
        if not html.strip().startswith('<div'):
            html = f'<div class="w-full">\n{html}\n</div>'
        
        return html

    def _auto_fix_js(self, js_code: str) -> str:
        """Auto-fix common JS issues"""
        # Remove localStorage/sessionStorage
        js_code = re.sub(
            r'(localStorage|sessionStorage)\.[a-zA-Z]+\([^)]*\)',
            '/* removed storage call */',
            js_code
        )
        
        # Ensure init() is called
        if 'function init(' in js_code or 'const init = ' in js_code:
            if not re.search(r'\ninit\(\);?\s*$', js_code):
                js_code += '\n\n// Auto-added init call\ninit();'
        
        return js_code

    def _inject_into_template(
        self,
        template_path: str,
        exp_data: Dict,
        html: str,
        css: str,
        js: str
    ) -> str:
        """Inject code vào template"""
        
        with open(template_path, 'r', encoding='utf-8') as f:
            template = f.read()
        
        # Replace placeholders
        output = template \
            .replace("{{LESSON_TITLE}}", str(exp_data.get("Bài học", "Thí nghiệm"))) \
            .replace("{{CHAPTER_TITLE}}", str(exp_data.get("Chương", ""))) \
            .replace("{{HTML_CONTENT}}", html) \
            .replace("{{CSS_CONTENT}}", css) \
            .replace("{{JS_CONTENT}}", js)
        
        return output

    def process_experiment(self, exp_data: Dict, template_path: str, prompt_path: str):
        """Wrapper method để tương thích với code cũ"""
        return self.generate_complete_experiment(exp_data, template_path, prompt_path)