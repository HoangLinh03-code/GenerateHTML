import vertexai, os
from vertexai.generative_models import GenerativeModel, Part, GenerationConfig
from dotenv import load_dotenv
from google.oauth2 import service_account
import sys
import traceback
import logging

logger = logging.getLogger(__name__)

# ============ QUAN TRỌNG: Xử lý đường dẫn cho PyInstaller ============
if getattr(sys, 'frozen', False):
    # Chạy từ file .exe (PyInstaller)
    base_path = sys._MEIPASS  # Thư mục tạm của PyInstaller
else:
    # Chạy từ Python script thường
    base_path = os.path.dirname(__file__)

# Đường dẫn đến file .env
dotenv_path = os.path.join(base_path, '.env')

# Load .env với explicit path
if os.path.exists(dotenv_path):
    load_dotenv(dotenv_path)
    logger.info(f"Loaded .env from: {dotenv_path}")
else:
    logger.warning(f".env not found at {dotenv_path}")
    logger.info(f"Base path: {base_path}")
    if os.path.exists(base_path):
        logger.info(f"Files in base_path: {os.listdir(base_path)}")


class VertexClient:
    """Client để tương tác với Vertex AI - PHIÊN BẢN CẢI TIẾN"""
    
    def __init__(self, project_id, creds, model, region="us-central1"):
        vertexai.init(
            project=project_id,
            location=region,
            credentials=creds
        )
        self.model = GenerativeModel(model)
        logger.info(f"✅ Initialized VertexClient with model: {model}")
    
    def _safe_extract_text(self, response):
        """Xử lý response an toàn, tránh lỗi multiple content parts"""
        try:
            # Thử lấy text trực tiếp trước
            if hasattr(response, 'text') and response.text:
                return response.text.strip()
            
            # Nếu không có text, thử lấy từ candidates
            if hasattr(response, 'candidates') and response.candidates:
                candidate = response.candidates[0]
                if hasattr(candidate, 'content') and candidate.content:
                    if hasattr(candidate.content, 'parts') and candidate.content.parts:
                        # Ghép tất cả text parts lại
                        text_parts = []
                        for part in candidate.content.parts:
                            if hasattr(part, 'text') and part.text:
                                text_parts.append(part.text.strip())
                        if text_parts:
                            full_text = '\n'.join(text_parts)
                            logger.info(f"📄 Extracted {len(full_text)} chars from {len(text_parts)} parts")
                            return full_text
            
            # Nếu vẫn không có text, thử lấy từ finish_reason
            if hasattr(response, 'candidates') and response.candidates:
                candidate = response.candidates[0]
                if hasattr(candidate, 'finish_reason'):
                    reason = str(candidate.finish_reason)
                    logger.warning(f"Response finished with reason: {reason}")
                    
                    # Nếu bị SAFETY hoặc MAX_TOKENS, log chi tiết
                    if 'SAFETY' in reason:
                        logger.error("❌ Response blocked by SAFETY filter!")
                    elif 'MAX_TOKENS' in reason or 'LENGTH' in reason:
                        logger.warning("⚠️ Response truncated due to MAX_TOKENS limit!")
                    
                    return f"Response finished with reason: {reason}"
            
            logger.error("❌ Không thể lấy được nội dung từ AI response")
            return "Không thể lấy được nội dung từ AI response"
            
        except Exception as e:
            logger.error(f"Lỗi xử lý response: {str(e)}")
            logger.error(f"Traceback: {traceback.format_exc()}")
            return f"Lỗi xử lý response: {str(e)}"

    def send_data_to_AI(self, prompt, file_paths=None, temperature=0.7, top_p=0.8, max_output_tokens=8192):
        """
        Gửi prompt và files đến AI để sinh nội dung
        
        Args:
            prompt: Prompt text
            file_paths: Danh sách đường dẫn files (PDF, images, etc.)
            temperature: Temperature (0.0-1.0)
            top_p: Top-p sampling (0.0-1.0)
            max_output_tokens: Số tokens tối đa cho output (QUAN TRỌNG cho HTML dài)
            
        Returns:
            str: Response text từ AI
        """
        parts = []
        
        # Thêm files nếu có
        if file_paths:
            for file_path in file_paths:
                try:
                    with open(file_path, "rb") as f:
                        file_bytes = f.read()
                    
                    # Xác định mime type
                    mime_type = "application/pdf"
                    if file_path.lower().endswith(('.png', '.jpg', '.jpeg')):
                        mime_type = "image/jpeg"
                    elif file_path.lower().endswith('.txt'):
                        mime_type = "text/plain"
                    
                    parts.append(
                        Part.from_data(data=file_bytes, mime_type=mime_type)
                    )
                    logger.info(f"📎 Loaded file: {os.path.basename(file_path)}")
                except Exception as e:
                    logger.error(f"❌ Error loading file {file_path}: {e}")
        
        # Thêm prompt text
        parts.append(Part.from_text(prompt))
        
        # Generation config với max_output_tokens cao
        generation_config = GenerationConfig(
            temperature=temperature,
            top_p=top_p,
            max_output_tokens=max_output_tokens,  # QUAN TRỌNG: Đủ lớn cho HTML dài
            candidate_count=1
        )
        
        logger.info(f"🤖 Calling AI with: temp={temperature}, top_p={top_p}, max_tokens={max_output_tokens}")
        
        try:
            response = self.model.generate_content(
                parts, 
                generation_config=generation_config,
                stream=False
            )
            
            # Extract text
            result = self._safe_extract_text(response)
            
            if result:
                logger.info(f"✅ AI responded with {len(result)} chars")
            else:
                logger.error("❌ AI response is empty!")
            
            return result
            
        except Exception as e:
            logger.error(f"❌ Error calling AI: {str(e)}")
            logger.error(f"Traceback: {traceback.format_exc()}")
            return None
        
    def send_data_to_check(self, prompt, temperature=0.5, top_p=0.8, max_output_tokens=8192):
        """
        Gửi prompt để kiểm tra/validate
        
        Args:
            prompt: Prompt text
            temperature: Temperature (0.0-1.0)
            top_p: Top-p sampling (0.0-1.0)
            max_output_tokens: Số tokens tối đa cho output
            
        Returns:
            str: Response text từ AI
        """
        parts = [Part.from_text(prompt)]

        generation_config = GenerationConfig(
            temperature=temperature,
            top_p=top_p,
            max_output_tokens=max_output_tokens,
            candidate_count=1
        )

        logger.info(f"🔍 Calling AI for check: temp={temperature}, top_p={top_p}")
        
        try:
            response = self.model.generate_content(
                parts, 
                generation_config=generation_config,
                stream=False
            )
            
            result = self._safe_extract_text(response)
            
            if result:
                logger.info(f"✅ Check response: {len(result)} chars")
            
            return result
            
        except Exception as e:
            logger.error(f"❌ Error calling AI for check: {str(e)}")
            return None


def get_vertex_ai_credentials():
    """Tạo credentials từ service account info trong .env"""
    try:
        # Kiểm tra các biến môi trường cần thiết
        required_vars = [
            "TYPE", "PROJECT_ID", "PRIVATE_KEY_ID", "PRIVATE_KEY",
            "CLIENT_EMAIL", "AUTH_URI", "TOKEN_URI"
        ]
        
        missing_vars = [var for var in required_vars if not os.getenv(var)]
        if missing_vars:
            logger.error(f"❌ Missing environment variables: {', '.join(missing_vars)}")
            return None
        
        # Tạo service account data
        service_account_data = {
            "type": os.getenv("TYPE"),
            "project_id": os.getenv("PROJECT_ID"),
            "private_key_id": os.getenv("PRIVATE_KEY_ID"),
            "private_key": os.getenv("PRIVATE_KEY").replace('\\n', '\n'), 
            "client_email": os.getenv("CLIENT_EMAIL"),
            "client_id": os.getenv("CLIENT_ID", ""),
            "auth_uri": os.getenv("AUTH_URI"),
            "token_uri": os.getenv("TOKEN_URI"),
            "auth_provider_x509_cert_url": os.getenv("AUTH_PROVIDER_X509_CERT_URL"),
            "client_x509_cert_url": os.getenv("CLIENT_X509_CERT_URL"),
            "universe_domain": os.getenv("UNIVERSE_DOMAIN", "googleapis.com")
        }
        
        # Tạo credentials
        credentials = service_account.Credentials.from_service_account_info(
            service_account_data,
            scopes=["https://www.googleapis.com/auth/cloud-platform"]
        )
        
        logger.info("✅ Successfully created credentials from service account")
        return credentials
        
    except Exception as e:
        logger.error(f"❌ Lỗi khi tạo credentials: {e}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        return None