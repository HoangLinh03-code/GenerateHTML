# pipeline.py

import pandas as pd
import json
import os
from pathlib import Path
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class ExcelToJsonPipeline:
    """
    Pipeline để xử lý file Excel thành các file JSON
    Mỗi sheet trong Excel sẽ tạo ra 1 file JSON riêng
    """
    
    def __init__(self, excel_file, output_dir="json_output"):
        """
        Khởi tạo pipeline
        
        Args:
            excel_file (str): Đường dẫn đến file Excel
            output_dir (str): Thư mục lưu các file JSON output
        """
        self.excel_file = excel_file
        self.output_dir = output_dir
        self.all_tables = {}
        self.sheet_names = []
        
        # Tạo thư mục output nếu chưa tồn tại
        os.makedirs(self.output_dir, exist_ok=True)
    
    def load_excel(self):
        """
        Đọc file Excel và lấy tất cả sheet names
        
        Returns:
            bool: True nếu thành công, False nếu thất bại
        """
        try:
            logger.info(f"Đang đọc file Excel: {self.excel_file}")
            data = pd.ExcelFile(self.excel_file)
            self.sheet_names = data.sheet_names
            logger.info(f"Tìm thấy {len(self.sheet_names)} sheets: {self.sheet_names}")
            
            # Đọc tất cả các sheet
            for sheet in self.sheet_names:
                df = pd.read_excel(self.excel_file, sheet_name=sheet)
                self.all_tables[sheet] = df
                logger.info(f"  ✓ Đã đọc sheet '{sheet}': {len(df)} dòng, {len(df.columns)} cột")
            
            return True
            
        except FileNotFoundError:
            logger.error(f"Không tìm thấy file: {self.excel_file}")
            return False
        except Exception as e:
            logger.error(f"Lỗi khi đọc file Excel: {str(e)}")
            return False
    
    def process_sheet(self, sheet_name):
        """
        Xử lý một sheet thành cấu trúc JSON theo format yêu cầu
        Nhóm dữ liệu theo source_folder và chapter_folder
        
        Args:
            sheet_name (str): Tên sheet cần xử lý
            
        Returns:
            dict: Dữ liệu đã được nhóm theo chapter
        """
        try:
            df = self.all_tables[sheet_name]
            logger.info(f"Đang xử lý sheet: {sheet_name}")
            
            # Kiểm tra các cột bắt buộc
            required_columns = ['source_folder', 'chapter_folder']
            missing_columns = [col for col in required_columns if col not in df.columns]
            
            if missing_columns:
                logger.warning(f"Sheet '{sheet_name}' thiếu các cột: {missing_columns}")
                # Nếu không có cột cần thiết, trả về toàn bộ data dạng list
                result = {"Data": df.to_dict('records')}
                return result
            
            # Nhóm theo source_folder và chapter_folder
            grouped = df.groupby(['source_folder', 'chapter_folder'])
            
            result = {}
            for (source, chapter), group in grouped:
                # Convert group thành list of dictionaries
                chapter_data = group.to_dict('records')
                
                # Sử dụng chapter_folder làm key
                result[chapter] = chapter_data
                
                logger.info(f"  ✓ Nhóm '{chapter}': {len(chapter_data)} bài học")
            
            return result
            
        except Exception as e:
            logger.error(f"Lỗi khi xử lý sheet '{sheet_name}': {str(e)}")
            return {}
    
    def save_to_json(self, data, sheet_name):
        """
        Lưu dữ liệu thành file JSON
        
        Args:
            data (dict): Dữ liệu cần lưu
            sheet_name (str): Tên sheet (sẽ dùng làm tên file)
            
        Returns:
            str: Đường dẫn file JSON đã tạo, None nếu thất bại
        """
        try:
            # Tạo tên file an toàn (loại bỏ ký tự đặc biệt)
            safe_name = "".join(c for c in sheet_name if c.isalnum() or c in (' ', '-', '_')).rstrip()
            output_file = os.path.join(self.output_dir, f"{safe_name}.json")
            
            # Lưu file JSON với encoding UTF-8
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=4)
            
            logger.info(f"✅ Đã lưu: {output_file}")
            return output_file
            
        except Exception as e:
            logger.error(f"Lỗi khi lưu JSON cho sheet '{sheet_name}': {str(e)}")
            return None
    
    def process_all(self):
        """
        Xử lý tất cả các sheet trong Excel và tạo file JSON tương ứng
        
        Returns:
            dict: Dictionary chứa thông tin về các file đã tạo
                  {sheet_name: output_file_path}
        """
        if not self.all_tables:
            logger.warning("Chưa load dữ liệu Excel. Đang thực hiện load...")
            if not self.load_excel():
                return {}
        
        results = {}
        total_sheets = len(self.sheet_names)
        
        logger.info(f"\n{'='*50}")
        logger.info(f"Bắt đầu xử lý {total_sheets} sheets")
        logger.info(f"{'='*50}\n")
        
        for idx, sheet_name in enumerate(self.sheet_names, 1):
            logger.info(f"[{idx}/{total_sheets}] Đang xử lý sheet: {sheet_name}")
            
            # Xử lý sheet
            data = self.process_sheet(sheet_name)
            
            if data:
                # Lưu thành JSON
                output_file = self.save_to_json(data, sheet_name)
                if output_file:
                    results[sheet_name] = output_file
            else:
                logger.warning(f"⚠️  Sheet '{sheet_name}' không có dữ liệu để xử lý")
            
            logger.info("")  # Dòng trống để dễ đọc
        
        logger.info(f"\n{'='*50}")
        logger.info(f"Hoàn thành! Đã tạo {len(results)}/{total_sheets} file JSON")
        logger.info(f"{'='*50}\n")
        
        return results
    
    def get_sheet_info(self, sheet_name):
        """
        Lấy thông tin chi tiết về một sheet
        
        Args:
            sheet_name (str): Tên sheet
            
        Returns:
            dict: Thông tin về sheet (số dòng, cột, chapters, lessons)
        """
        if sheet_name not in self.all_tables:
            return None
        
        df = self.all_tables[sheet_name]
        
        info = {
            'sheet_name': sheet_name,
            'total_rows': len(df),
            'total_columns': len(df.columns),
            'columns': df.columns.tolist()
        }
        
        # Thêm thông tin về chapters nếu có
        if 'chapter_folder' in df.columns:
            info['total_chapters'] = df['chapter_folder'].nunique()
            info['chapters'] = df['chapter_folder'].unique().tolist()
        
        # Thêm thông tin về lessons nếu có
        if 'Bài học' in df.columns:
            info['total_lessons'] = len(df)
            
        return info
    
    def get_all_sheets_info(self):
        """
        Lấy thông tin về tất cả các sheet
        
        Returns:
            list: Danh sách thông tin của các sheet
        """
        return [self.get_sheet_info(sheet) for sheet in self.sheet_names]


def main():
    """
    Hàm main để test pipeline từ command line
    """
    import argparse
    
    parser = argparse.ArgumentParser(description="Xử lý file Excel thành các file JSON")
    parser.add_argument('excel_file', type=str, help='Đường dẫn đến file Excel')
    parser.add_argument('--output_dir', type=str, default='json_output', 
                       help='Thư mục lưu file JSON (mặc định: json_output)')
    parser.add_argument('--sheet', type=str, help='Chỉ xử lý một sheet cụ thể')
    
    args = parser.parse_args()
    
    # Khởi tạo pipeline
    pipeline = ExcelToJsonPipeline(args.excel_file, args.output_dir)
    
    # Load Excel
    if not pipeline.load_excel():
        logger.error("Không thể load file Excel. Thoát!")
        return
    
    # Xử lý
    if args.sheet:
        # Xử lý một sheet cụ thể
        if args.sheet in pipeline.sheet_names:
            data = pipeline.process_sheet(args.sheet)
            pipeline.save_to_json(data, args.sheet)
        else:
            logger.error(f"Không tìm thấy sheet '{args.sheet}'")
            logger.info(f"Các sheet có sẵn: {pipeline.sheet_names}")
    else:
        # Xử lý tất cả
        results = pipeline.process_all()
        
        # In summary
        print("\n" + "="*50)
        print("SUMMARY")
        print("="*50)
        for sheet, output_file in results.items():
            print(f"✓ {sheet} → {output_file}")


if __name__ == "__main__":
    main()