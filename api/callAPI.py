import os
from dotenv import load_dotenv
from google.oauth2 import service_account
from google import genai  # Thư viện mới
import sys
import traceback
import logging

logger = logging.getLogger(__name__)

# ============ QUAN TRỌNG: Xử lý đường dẫn cho PyInstaller ============
if getattr(sys, 'frozen', False):
    base_path = sys._MEIPASS
else:
    base_path = os.path.dirname(__file__)

dotenv_path = os.path.join(base_path, '.env')

if os.path.exists(dotenv_path):
    load_dotenv(dotenv_path)
    logger.info(f"Loaded .env from: {dotenv_path}")
else:
    logger.warning(f".env not found at {dotenv_path}")
    logger.info(f"Base path: {base_path}")
    if os.path.exists(base_path):
        logger.info(f"Files in base_path: {os.listdir(base_path)}")


class VertexClient:
    """Client để tương tác với Vertex AI - PHIÊN BẢN GEMINI 3 PRO"""
    
    def __init__(self, project_id, creds, model="gemini-3-pro-preview", region="global"):
        """
        Khởi tạo client với Google GenAI SDK mới
        
        Args:
            project_id: Google Cloud Project ID
            creds: Service Account Credentials
            model: Tên model (mặc định: gemini-3-pro-preview)
            region: Region (mặc định: global)
        """
        try:
            self.client = genai.Client(
                vertexai=True,
                project=project_id,
                location=region,
                credentials=creds
            )
            self.model_name = model
            logger.info(f"✅ Initialized VertexClient with model: {model}")
        except Exception as e:
            logger.error(f"❌ Failed to initialize client: {e}")
            raise
    
    def _safe_extract_text(self, response):
        """
        Xử lý response an toàn từ GenAI SDK
        
        Args:
            response: Response object từ generate_content
            
        Returns:
            str: Text content hoặc error message
        """
        try:
            # GenAI SDK trả về response.text trực tiếp
            if hasattr(response, 'text') and response.text:
                text = response.text.strip()
                logger.info(f"📄 Extracted {len(text)} chars from response")
                return text
            
            # Fallback: kiểm tra candidates
            if hasattr(response, 'candidates') and response.candidates:
                candidate = response.candidates[0]
                
                # Kiểm tra finish_reason
                if hasattr(candidate, 'finish_reason'):
                    reason = str(candidate.finish_reason)
                    
                    if 'SAFETY' in reason:
                        logger.error("❌ Response blocked by SAFETY filter!")
                        return "Response blocked by safety filter"
                    elif 'MAX_TOKENS' in reason or 'LENGTH' in reason:
                        logger.warning("⚠️ Response truncated due to MAX_TOKENS!")
                        # Vẫn cố lấy text nếu có
                        if hasattr(candidate, 'content') and hasattr(candidate.content, 'parts'):
                            text_parts = [p.text for p in candidate.content.parts if hasattr(p, 'text')]
                            if text_parts:
                                return '\n'.join(text_parts)
                    
                    logger.warning(f"Response finished with reason: {reason}")
            
            logger.error("❌ Không thể lấy được nội dung từ AI response")
            return "Không thể lấy được nội dung từ AI response"
            
        except Exception as e:
            logger.error(f"Lỗi xử lý response: {str(e)}")
            logger.error(f"Traceback: {traceback.format_exc()}")
            return f"Lỗi xử lý response: {str(e)}"

    def send_data_to_AI(self, prompt, file_paths=None, temperature=0.3, top_p=0.8, max_output_tokens=30000):
        """
        Gửi prompt và files đến AI để sinh nội dung
        
        Args:
            prompt: Prompt text
            file_paths: Danh sách đường dẫn files (PDF, images, etc.)
            temperature: Temperature (0.0-1.0)
            top_p: Top-p sampling (0.0-1.0)
            max_output_tokens: Số tokens tối đa cho output
            
        Returns:
            str: Response text từ AI
        """
        try:
            # Chuẩn bị nội dung
            contents = []
            
            # Thêm files nếu có (GenAI SDK hỗ trợ multimodal)
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
                        
                        # GenAI SDK format
                        contents.append({
                            "type": "inline_data",
                            "mime_type": mime_type,
                            "data": file_bytes
                        })
                        
                        logger.info(f"📎 Loaded file: {os.path.basename(file_path)}")
                    except Exception as e:
                        logger.error(f"❌ Error loading file {file_path}: {e}")
            
            # Thêm prompt text
            contents.append(prompt)
            
            logger.info(f"🤖 Calling AI with: temp={temperature}, top_p={top_p}, max_tokens={max_output_tokens}")
            
            # Gọi API với GenAI SDK
            response = self.client.models.generate_content(
                model=self.model_name,
                contents=contents,
                config={
                    "temperature": temperature,
                    "top_p": top_p,
                    "max_output_tokens": max_output_tokens
                }
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
        
    def send_data_to_check(self, prompt, temperature=0.3, top_p=0.8, max_output_tokens=30000):
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
        logger.info(f"🔍 Calling AI for check: temp={temperature}, top_p={top_p}")
        
        try:
            response = self.client.models.generate_content(
                model=self.model_name,
                contents=prompt,
                config={
                    "temperature": temperature,
                    "top_p": top_p,
                    "max_output_tokens": max_output_tokens
                }
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