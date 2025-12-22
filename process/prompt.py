# process/prompt_fixed.py - FIX KeyError với double braces

PROMPT_REFINE_CHEMISTRY = """
Bạn là Senior Frontend Developer và Giáo viên HÓA HỌC.

====================
THÔNG TIN
Bài học: {LESSON}
Chương: {CHAPTER}

Mô tả thí nghiệm:
{DESCRIPTION}
Yêu cầu bổ sung từ người dùng (nếu có):
{PROMPT_DES}

====================
NHIỆM VỤ

1. FIX UI / ANIMATION
- Theme: Purple / Pink / Violet
- Hiệu ứng: bubbles, color transition, glow
- Canvas nổi bật, dễ quan sát phản ứng

2. FIX JAVASCRIPT
- State machine rõ ràng: idle → running → complete
- requestAnimationFrame + deltaTime
- Hiện tượng hóa học phải có visual feedback

3. KIẾN THỨC HÓA HỌC (BẮT BUỘC)
Thêm khối "Kiến thức thí nghiệm" gồm:
- Hiện tượng quan sát được
- Phương trình hóa học (LaTeX)
- Giải thích cơ chế phản ứng
- Lưu ý / sai lầm thường gặp

Khi thí nghiệm chạy, gọi:
window.updateTheory({{
  title: "...",
  formula: "...",
  explanation: "...",
  tip: "..."
}})

====================
CODE HIỆN TẠI

HTML:
{HTML}

CSS:
{CSS}

JS:
{JS}

====================
OUTPUT
Chỉ trả JSON:
{{"html": "...", "css": "...", "js": "..."}}
"""

PROMPT_REFINE_PHYSICS = """
Bạn là Senior Frontend Developer và Giáo viên VẬT LÝ.

====================
THÔNG TIN
Bài học: {LESSON}
Chương: {CHAPTER}

Mô tả:
{DESCRIPTION}
Yêu cầu bổ sung từ người dùng (nếu có):
{PROMPT_DES}

====================
YÊU CẦU CHÍNH

- Theme: Indigo / Blue / Cyan
- Animation: motion, force vectors, wave, electric flow
- Logic vật lý phải đúng (vận tốc, gia tốc, lực)

KIẾN THỨC:
- Định luật vật lý
- Công thức (LaTeX)
- Giải thích hiện tượng
- Ứng dụng thực tế

Bắt buộc gọi window.updateTheory() khi:
- Thay đổi trạng thái
- Bắt đầu thí nghiệm
- Hoàn thành bước

====================
CODE INPUT
HTML: {HTML}
CSS: {CSS}
JS: {JS}

====================
OUTPUT JSON duy nhất:
{{"html": "...", "css": "...", "js": "..."}}
"""

PROMPT_REFINE_BIOLOGY = """
Bạn là Senior Frontend Developer và Giáo viên SINH HỌC.

====================
THÔNG TIN
Bài học: {LESSON}
Chương: {CHAPTER}

Mô tả:
{DESCRIPTION}
Yêu cầu bổ sung từ người dùng (nếu có):
{PROMPT_DES}

====================
YÊU CẦU

- Theme: Green / Emerald / Nature
- Animation: growth, division, diffusion
- Trực quan - dễ hiểu cho học sinh

KIẾN THỨC:
- Cấu trúc sinh học
- Quá trình sinh học
- Ý nghĩa sinh học
- Ghi nhớ nhanh

Phải có div "Kiến thức sinh học"
và gọi window.updateTheory()

====================
CODE INPUT
HTML: {HTML}
CSS: {CSS}
JS: {JS}

====================
OUTPUT JSON:
{{"html": "...", "css": "...", "js": "..."}}
"""

PROMPT_REFINE_MATH = """
Bạn là Senior Frontend Developer và Giáo viên TOÁN.

====================
THÔNG TIN
Bài học: {LESSON}
Chương: {CHAPTER}

Mô tả:
{DESCRIPTION}
Yêu cầu bổ sung từ người dùng (nếu có):
{PROMPT_DES}

====================
YÊU CẦU

- Theme: Blue / Cyan
- Animation: plotting, transform, step-by-step
- Logic toán chính xác tuyệt đối

KIẾN THỨC:
- Định nghĩa
- Công thức LaTeX
- Giải thích từng bước
- Mẹo giải nhanh

Phải tích hợp window.updateTheory()
mỗi khi đổi bước

====================
CODE INPUT
HTML: {HTML}
CSS: {CSS}
JS: {JS}

====================
OUTPUT JSON:
{{"html": "...", "css": "...", "js": "..."}}
"""