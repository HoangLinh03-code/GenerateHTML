# process.py

import os
import argparse
from api.callAPI import VertexClient, get_vertex_ai_credentials
from dotenv import load_dotenv
import logging
import time

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

def read_file(file_path):
    """Helper to read file content."""
    with open(file_path, 'r', encoding='utf-8') as f:
        return f.read()

def write_file(file_path, content):
    """Helper to write file content."""
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)

def main():
    parser = argparse.ArgumentParser(description="Process and refine generated HTML files using Vertex AI.")
    parser.add_argument('--input_html', type=str, required=True, help='Path to the initial HTML file to refine.')
    parser.add_argument('--output_html', type=str, help='Path to save the refined HTML file (default: input_html with _refined suffix).')
    parser.add_argument('--prompt_file', type=str, default='prompt_refine.txt', help='Path to the refinement prompt file.')
    parser.add_argument('--max_tokens', type=int, default=8192, help='Max output tokens for the AI call.')
    
    args = parser.parse_args()

    if not args.output_html:
        # Default output name: input file name with _refined before .html
        base, ext = os.path.splitext(args.input_html)
        args.output_html = f"{base}_refined{ext}"

    credentials = get_vertex_ai_credentials()
    if not credentials:
        logger.error("❌ Cannot create Vertex AI credentials. Check your .env file.")
        return

    PROJECT_ID = os.getenv("PROJECT_ID")
    if not PROJECT_ID:
        logger.error("❌ PROJECT_ID not found in .env")
        return

    vertex_client = VertexClient(PROJECT_ID, credentials, "gemini-2.5-pro")

    try:
        initial_html_content = read_file(args.input_html)
        logger.info(f"✅ Loaded initial HTML: {args.input_html}")
    except FileNotFoundError:
        logger.error(f"❌ {args.input_html} not found.")
        return
    except Exception as e:
        logger.error(f"❌ Error reading {args.input_html}: {e}")
        return

    try:
        refinement_prompt = read_file(args.prompt_file)
        logger.info(f"✅ Loaded refinement prompt: {args.prompt_file}")
    except FileNotFoundError:
        logger.error(f"❌ {args.prompt_file} not found.")
        return
    except Exception as e:
        logger.error(f"❌ Error reading {args.prompt_file}: {e}")
        return

    # Construct the full prompt for refinement
    full_prompt = f"""
Bạn là một chuyên gia phát triển web giáo dục. Nhiệm vụ của bạn là nhận một file HTML mô phỏng thí nghiệm hóa học và cải thiện nó theo các yêu cầu sau:

**YÊU CẦU CẢI THIỆN:**
1.  **Sửa lỗi:** Xác định và sửa bất kỳ lỗi HTML, CSS hoặc JavaScript nào (ví dụ: thiếu thẻ đóng, lỗi cú pháp JS, lỗi layout responsive).
2.  **Tăng tính trực quan:** Cải thiện giao diện người dùng (UI) để hấp dẫn và dễ sử dụng hơn. Điều chỉnh màu sắc, bố cục, hoạt ảnh nếu cần.
3.  **Bổ sung thông tin:** Dựa trên nội dung bài học và chương từ file JSON gốc (thông tin này có thể được bạn thêm vào prompt nếu cần, hoặc giả định là bạn biết nội dung từ tên file hoặc biến môi trường), thêm các phần giải thích, tóm tắt, hoặc kiến thức liên quan vào HTML (ví dụ: phương trình hóa học, định nghĩa, công thức tính toán).
4.  **Tăng tính tương tác (nếu có thể):** Thêm các yếu tố tương tác nhỏ như tooltip, thông báo, hoặc hiệu ứng khi người dùng thao tác nếu phù hợp với nội dung mô tả thí nghiệm.
5.  **Tối ưu hóa:** Đảm bảo code HTML, CSS, JS được viết gọn gàng, hiệu quả và dễ đọc.

**HTML CẦN CẢI THIỆN:**

**LƯU Ý:**
- Trả về MÃ HTML HOÀN CHỈNH (<!DOCTYPE html> ... </html>), KHÔNG CÓ GÌ KHÁC (không lời dẫn, không giải thích, không dấu ```html).
- Giữ nguyên cấu trúc và chức năng cốt lõi của mô phỏng.
- Chỉ trả về mã HTML cuối cùng đã được cải thiện.
"""

    logger.info(f"Sending refinement request for {args.input_html}...")
    refined_html_content = vertex_client.send_data_to_AI(full_prompt, max_output_tokens=args.max_tokens)

    if not refined_html_content:
        logger.error("❌ Failed to get refined HTML content from AI.")
        return

    # Post-process: Remove any potential markdown code block wrappers if AI adds them despite the prompt
    if refined_html_content.startswith("```html\n") and refined_html_content.endswith("\n```"):
        refined_html_content = refined_html_content[8:-4] # Remove ```html\n and \n```
    elif refined_html_content.startswith("```") and refined_html_content.endswith("```"):
        # If it starts with ``` but not specifically ```html, try to find the first <html> tag and last </html> tag
        start_idx = refined_html_content.find("<!DOCTYPE html>")
        if start_idx == -1:
            start_idx = refined_html_content.find("<html>")
        end_idx = refined_html_content.rfind("</html>")
        if start_idx != -1 and end_idx != -1:
            refined_html_content = refined_html_content[start_idx:end_idx+7] # +7 for "</html>"

    if not refined_html_content:
        logger.error("❌ Refined HTML content is empty after post-processing.")
        return

    try:
        write_file(args.output_html, refined_html_content)
        logger.info(f"✅ Refined HTML saved: {args.output_html}")
    except Exception as e:
        logger.error(f"❌ Error writing refined HTML to {args.output_html}: {e}")


if __name__ == "__main__":
    main()