# process/generate_v2.py - PHIÊN BẢN CẢI TIẾN TOÀN DIỆN

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
    """Generator cải tiến với UI đẹp hơn và logic JS chặt chẽ hơn"""
    
    def __init__(self, vertex_client: VertexClient, output_dir: str):
        self.client = vertex_client
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)
        
        # Load design system
        self.design_tokens = self._load_design_tokens()
        
    def _load_design_tokens(self) -> Dict:
        """Load design tokens để đảm bảo UI consistency"""
        return {
            "colors": {
                "primary": "#3b82f6",  # blue-500
                "secondary": "#8b5cf6",  # violet-500
                "success": "#10b981",  # green-500
                "danger": "#ef4444",  # red-500
                "warning": "#f59e0b",  # amber-500
                "dark": "#1e293b",  # slate-800
                "light": "#f1f5f9"  # slate-100
            },
            "spacing": {
                "container": "max-w-7xl mx-auto px-4 sm:px-6 lg:px-8",
                "section": "p-6 sm:p-8",
                "card": "rounded-xl shadow-lg"
            },
            "typography": {
                "heading": "font-bold tracking-tight",
                "body": "text-gray-700 leading-relaxed"
            }
        }

    def generate_complete_experiment(self, exp_data: Dict, template_path: str, prompt_path: str):
        """
        Sinh HTML với 2 BƯỚC:
        1. Tạo Blueprint (cấu trúc + logic)
        2. Render thành HTML/CSS/JS thực tế
        """
        lesson = exp_data.get('Bài học', 'Unknown')
        logger.info(f"🚀 Sinh HTML nâng cao cho: {lesson}")
        
        # BƯỚC 1: Tạo Blueprint
        blueprint = self._generate_blueprint(exp_data)
        if not blueprint:
            logger.error("❌ Không tạo được blueprint")
            return None
        
        # BƯỚC 2: Render từ Blueprint
        html, css, js = self._render_from_blueprint(blueprint, exp_data)
        
        # Validate
        from process.validate import CodeValidator
        
        is_valid_html, msg = CodeValidator.validate_html(html)
        if not is_valid_html:
            logger.error(f"❌ HTML không hợp lệ: {msg}")
            return None
        
        is_valid_js, msg = CodeValidator.validate_js(js)
        if not is_valid_js:
            logger.warning(f"⚠️ JS có warning: {msg}")
            js = self._auto_fix_js(js)
        
        # Inject vào template
        with open(template_path, 'r', encoding='utf-8') as f:
            template = f.read()
        
        output = template \
            .replace("{{CHAPTER_TITLE}}", str(exp_data.get("Chương", ""))) \
            .replace("{{LESSON_TITLE}}", str(lesson)) \
            .replace("{{CONTENT_SUMMARY}}", str(exp_data.get("Nội dung trong bài học", ""))[:200]) \
            .replace("{{HTML_CONTENT}}", html) \
            .replace("{{CSS_CONTENT}}", css) \
            .replace("{{JS_CONTENT}}", js)
        
        # Lưu file
        safe_name = re.sub(r'[^\w\-]', '_', lesson)
        filename = os.path.join(self.output_dir, f"{safe_name}.html")
        
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(output)
        
        logger.info(f"✅ Đã tạo: {filename}")
        return filename

    def _generate_blueprint(self, exp_data: Dict) -> Dict:
        """
        BƯỚC 1: Tạo Blueprint (JSON schema) cho thí nghiệm
        Blueprint định nghĩa cấu trúc, các thành phần, và logic
        """
        mo_ta = exp_data.get('Mô tả thí nghiệm thực hiện', '')
        
        prompt = f"""Bạn là Solution Architect cho thí nghiệm hóa học tương tác.

**THÔNG TIN THÍ NGHIỆM:**
Bài học: {exp_data.get('Bài học')}
Chương: {exp_data.get('Chương')}

Mô tả chi tiết:
{mo_ta[:1500]}

**NHIỆM VỤ:**
Tạo Blueprint (JSON) định nghĩa:
1. Các thành phần UI (containers, canvas, controls)
2. State management structure
3. Core logic functions
4. Animation sequences
5. User interactions

**FORMAT BLUEPRINT:**
```json
{{
  "layout": {{
    "type": "grid|flex|single-canvas",
    "sections": [
      {{"id": "main-canvas", "type": "canvas", "size": "800x600"}},
      {{"id": "control-panel", "type": "controls", "position": "bottom"}},
      {{"id": "info-display", "type": "info-panel", "position": "right"}}
    ]
  }},
  "state": {{
    "global": ["running: false", "temperature: 25", "pressure: 1"],
    "entities": ["particles: []", "molecules: []"]
  }},
  "functions": {{
    "initialization": ["initCanvas", "setupParticles"],
    "physics": ["updateParticles", "checkCollisions", "applyForces"],
    "rendering": ["drawBackground", "drawParticles", "drawUI"],
    "interactions": ["handleStart", "handleReset", "handleSliderChange"]
  }},
  "animations": {{
    "type": "requestAnimationFrame",
    "fps_target": 60,
    "sequences": [
      {{"name": "particleMovement", "duration": "continuous"}},
      {{"name": "colorTransition", "duration": "2s"}}
    ]
  }},
  "design": {{
    "theme": "modern-gradient|glassmorphism|neumorphism",
    "primary_color": "#3b82f6",
    "accent_color": "#8b5cf6",
    "effects": ["glow", "shadow-xl", "backdrop-blur"]
  }}
}}
```

**YÊU CẦU:**
- Layout phải responsive và đẹp mắt
- State management rõ ràng, tách biệt
- Functions được nhóm theo chức năng
- Design hiện đại với effects hấp dẫn

Chỉ trả về JSON Blueprint, không giải thích."""

        response = self.client.send_data_to_AI(
            prompt,
            max_output_tokens=30000,
            temperature=0.1
        )
        
        if not response:
            return None
        
        # Parse JSON
        try:
            json_match = re.search(r'```json\s*(\{.*?\})\s*```', response, re.DOTALL)
            if json_match:
                blueprint = json.loads(json_match.group(1))
            else:
                start = response.find('{')
                end = response.rfind('}')
                blueprint = json.loads(response[start:end+1])
            
            logger.info(f"✅ Blueprint created: {len(str(blueprint))} chars")
            return blueprint
        except Exception as e:
            logger.error(f"❌ Blueprint parse error: {e}")
            return None

    def _ai_refine_output(
      self,
      html: str,
      css: str,
      js: str,
      exp_data: Dict
  ) -> Tuple[str, str, str]:
      """
      AI Post-processing stage:
      - Fix UI / animation
      - Fix JS logic
      - Inject knowledge panel & theory integration
      """

      subject = exp_data.get("Môn học", "HÓA").upper()
      lesson = exp_data.get("Bài học", "")
      chapter = exp_data.get("Chương", "")
      description = exp_data.get("Mô tả thí nghiệm thực hiện", "")[:1000]

      # Chọn prompt theo môn
      prompt_template = self._get_refine_prompt_by_subject(subject)

      prompt = prompt_template.format(
          LESSON=lesson,
          CHAPTER=chapter,
          DESCRIPTION=description,
          HTML=html,
          CSS=css,
          JS=js
      )

      logger.info(f"🧠 AI refining output for subject: {subject}")

      response = self.client.send_data_to_AI(
          prompt,
          temperature=0.15,
          max_output_tokens=20000
      )

      if not response:
          logger.warning("⚠️ AI refine failed → fallback original output")
          return html, css, js

      # Parse JSON result
      try:
          json_match = re.search(r'\{[\s\S]*\}', response)
          data = json.loads(json_match.group())

          refined_html = self._clean_code(data.get("html", html), "html")
          refined_css = self._clean_code(data.get("css", css), "css")
          refined_js = self._clean_code(data.get("js", js), "js")

          # Validate again
          from process.validate import CodeValidator

          if not CodeValidator.validate_html(refined_html)[0]:
              raise ValueError("HTML invalid after refine")
          if not CodeValidator.validate_css(refined_css)[0]:
              raise ValueError("CSS invalid after refine")
          if not CodeValidator.validate_js(refined_js)[0]:
              raise ValueError("JS invalid after refine")

          logger.info("✅ AI refine success")
          return refined_html, refined_css, refined_js

      except Exception as e:
          logger.error(f"❌ AI refine parse/validate error: {e}")
          return html, css, js
    def _get_refine_prompt_by_subject(self, subject: str) -> str:
      subject = subject.upper()

      if subject == "LÝ":
          return PROMPT_REFINE_PHYSICS
      if subject == "SINH":
          return PROMPT_REFINE_BIOLOGY
      if subject == "TOÁN":
          return PROMPT_REFINE_MATH

      # Default: Hóa
      return PROMPT_REFINE_CHEMISTRY


    def _render_from_blueprint(self, blueprint: Dict, exp_data: Dict) -> Tuple[str, str, str]:
        """
        BƯỚC 2: Render HTML/CSS/JS từ Blueprint
        """
        prompt = f"""Bạn là Senior Frontend Developer chuyên về data visualization.

**BLUEPRINT ĐÃ ĐƯỢC APPROVED:**
```json
{json.dumps(blueprint, indent=2, ensure_ascii=False)}
```

**THÔNG TIN BỔ SUNG:**
Bài học: {exp_data.get('Bài học')}
Mô tả: {exp_data.get('Mô tả thí nghiệm thực hiện', '')[:800]}

**NHIỆM VỤ:**
Implement blueprint thành code HTML/CSS/JS production-ready.

**OUTPUT FORMAT:**
```json
{{
  "html": "...",
  "css": "...",
  "js": "..."
}}
```

**YÊU CẦU IMPLEMENTATION:**

1. **HTML - UI Components:**
   - Dựa trên blueprint.layout, tạo cấu trúc DOM
   - Mỗi section phải có container riêng với id
   - Dùng Tailwind: {self.design_tokens['spacing']['container']}
   - Canvas phải có size chính xác từ blueprint
   - Controls: buttons đẹp với icon (dùng Unicode: ▶️ ⏸ 🔄)
   - Info panel: grid layout cho metrics
   
   VÍ DỤ STRUCTURE:
   ```html
   <div class="max-w-7xl mx-auto space-y-8">
     <div class="bg-gradient-to-br from-blue-50 to-indigo-50 p-8 rounded-2xl shadow-2xl">
       <canvas id="mainCanvas" class="w-full rounded-xl shadow-inner"></canvas>
     </div>
     <div class="grid grid-cols-3 gap-4">
       <button class="group relative px-8 py-4 bg-gradient-to-r from-green-500 to-emerald-500 
                      hover:from-green-600 hover:to-emerald-600 text-white font-bold rounded-xl 
                      shadow-lg hover:shadow-xl transform hover:-translate-y-1 transition-all">
         <span class="flex items-center gap-2">▶️ Bắt đầu</span>
       </button>
     </div>
   </div>
   ```

2. **CSS - Modern Styling:**
   - Gradient backgrounds cho depth
   - Animations mượt mà (ease-in-out, cubic-bezier)
   - Glow effects cho interactive elements
   - Glassmorphism cho panels (backdrop-filter)
   
   VÍ DỤ:
   ```css
   @keyframes pulse-glow {{
     0%, 100% {{ box-shadow: 0 0 20px rgba(59, 130, 246, 0.5); }}
     50% {{ box-shadow: 0 0 40px rgba(59, 130, 246, 0.8); }}
   }}
   
   .active-particle {{
     animation: pulse-glow 2s ease-in-out infinite;
   }}
   
   .glass-panel {{
     background: rgba(255, 255, 255, 0.1);
     backdrop-filter: blur(10px);
     border: 1px solid rgba(255, 255, 255, 0.2);
   }}
   ```

3. **JS - Robust Logic:**
   ```javascript
   // === CONFIGURATION ===
   const CONFIG = {{
     canvas: {{ width: 800, height: 600 }},
     physics: {{ gravity: 0.5, friction: 0.98 }},
     colors: {{ primary: '#3b82f6', accent: '#8b5cf6' }}
   }};
   
   // === STATE MANAGEMENT ===
   const state = {{
     // Từ blueprint.state
     running: false,
     temperature: 25,
     particles: [],
     
     // UI state
     selectedTool: null,
     hoveredElement: null
   }};
   
   // === ENTITY CLASSES ===
   class Particle {{
     constructor(x, y, vx, vy) {{
       this.x = x; this.y = y;
       this.vx = vx; this.vy = vy;
       this.radius = 5;
       this.color = CONFIG.colors.primary;
     }}
     
     update(dt) {{
       this.vy += CONFIG.physics.gravity * dt;
       this.x += this.vx * dt;
       this.y += this.vy * dt;
       
       // Collision với walls
       if (this.x < this.radius || this.x > CONFIG.canvas.width - this.radius) {{
         this.vx *= -CONFIG.physics.friction;
       }}
       if (this.y > CONFIG.canvas.height - this.radius) {{
         this.y = CONFIG.canvas.height - this.radius;
         this.vy *= -CONFIG.physics.friction;
       }}
     }}
     
     draw(ctx) {{
       ctx.fillStyle = this.color;
       ctx.beginPath();
       ctx.arc(this.x, this.y, this.radius, 0, Math.PI * 2);
       ctx.fill();
     }}
   }}
   
   // === RENDERING ===
   function render(ctx) {{
     // Clear với gradient
     const gradient = ctx.createLinearGradient(0, 0, 0, CONFIG.canvas.height);
     gradient.addColorStop(0, '#1e3a8a');
     gradient.addColorStop(1, '#3b82f6');
     ctx.fillStyle = gradient;
     ctx.fillRect(0, 0, CONFIG.canvas.width, CONFIG.canvas.height);
     
     // Draw entities
     state.particles.forEach(p => p.draw(ctx));
     
     // Draw UI overlays
     drawMetrics(ctx);
   }}
   
   function drawMetrics(ctx) {{
     ctx.fillStyle = 'rgba(255, 255, 255, 0.9)';
     ctx.font = 'bold 16px sans-serif';
     ctx.fillText(`Particles: ${{state.particles.length}}`, 10, 30);
     ctx.fillText(`Temp: ${{state.temperature}}°C`, 10, 55);
   }}
   
   // === PHYSICS UPDATE ===
   let lastTime = 0;
   function update(currentTime) {{
     const dt = (currentTime - lastTime) / 1000;
     lastTime = currentTime;
     
     if (state.running) {{
       state.particles.forEach(p => p.update(dt));
     }}
     
     render(ctx);
     requestAnimationFrame(update);
   }}
   
   // === EVENT HANDLERS ===
   function handleStart() {{
     state.running = true;
     this.textContent = '⏸ Tạm dừng';
     this.classList.replace('from-green-500', 'from-yellow-500');
   }}
   
   function handleReset() {{
     state.running = false;
     state.particles = [];
     initParticles();
   }}
   
   // === INITIALIZATION ===
   function initParticles() {{
     for (let i = 0; i < 20; i++) {{
       state.particles.push(new Particle(
         Math.random() * CONFIG.canvas.width,
         Math.random() * CONFIG.canvas.height,
         (Math.random() - 0.5) * 200,
         (Math.random() - 0.5) * 200
       ));
     }}
   }}
   
   function init() {{
     const canvas = document.getElementById('mainCanvas');
     const ctx = canvas.getContext('2d');
     
     canvas.width = CONFIG.canvas.width;
     canvas.height = CONFIG.canvas.height;
     
     // Setup events
     document.getElementById('btnStart').onclick = handleStart;
     document.getElementById('btnReset').onclick = handleReset;
     
     initParticles();
     requestAnimationFrame(update);
   }}
   
   init();
   ```

**CHECKLIST:**
- [ ] HTML không có thẻ html/head/body
- [ ] Tailwind classes đầy đủ, không inline styles
- [ ] CSS chỉ có animations/custom effects
- [ ] JS có class cho entities
- [ ] State management rõ ràng
- [ ] RequestAnimationFrame với delta time
- [ ] Event handlers clean
- [ ] Không dùng localStorage

Chỉ trả về JSON với 3 keys: html, css, js."""

        response = self.client.send_data_to_AI(
            prompt,
            max_output_tokens=30000,
            temperature=0.1
        )
        
        if not response:
            logger.error("❌ Không render được từ blueprint")
            return "", "", ""
        
        return self._parse_response(response)

    def _parse_response(self, response: str) -> Tuple[str, str, str]:
        """Parse JSON response"""
        try:
            json_match = re.search(r'```json\s*(\{.*?\})\s*```', response, re.DOTALL)
            if json_match:
                data = json.loads(json_match.group(1))
            else:
                start = response.find('{')
                end = response.rfind('}')
                data = json.loads(response[start:end+1])
            
            html = self._clean_code(data.get('html', ''), 'html')
            css = self._clean_code(data.get('css', ''), 'css')
            js = self._clean_code(data.get('js', ''), 'js')
            
            return html, css, js
        except Exception as e:
            logger.error(f"❌ Parse error: {e}")
            return "", "", ""

    def _clean_code(self, code: str, lang: str) -> str:
        """Clean code blocks"""
        pattern = rf"```{lang}?\s*\n?(.*?)\n?```"
        match = re.search(pattern, code, re.DOTALL)
        return match.group(1).strip() if match else code.strip()

    def _auto_fix_js(self, js_code: str) -> str:
        """Auto-fix common JS issues"""
        js_code = re.sub(r'localStorage\.[a-zA-Z]+\([^)]*\)', '/* removed */', js_code)
        js_code = re.sub(r'sessionStorage\.[a-zA-Z]+\([^)]*\)', '/* removed */', js_code)
        
        if 'init()' not in js_code and 'function init(' in js_code:
            js_code += '\n\ninit();'
        
        return js_code

    def process_experiment(self, exp_data: Dict, template_path: str, prompt_path: str):
        """Wrapper for compatibility"""
        return self.generate_complete_experiment(exp_data, template_path, prompt_path)