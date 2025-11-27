# main.py

import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
import json
import os
import glob
import threading
import logging
import queue
from dotenv import load_dotenv

# Import các module từ thư mục con
from api.callAPI import VertexClient, get_vertex_ai_credentials
from process.generate import ExperimentGenerator
from process.pipeline import ExcelToJsonPipeline

load_dotenv()

# Thiết lập Log hiển thị lên GUI
class QueueHandler(logging.Handler):
    def __init__(self, log_queue):
        super().__init__()
        self.log_queue = log_queue
    def emit(self, record):
        self.log_queue.put(self.format(record))

class HTMLGeneratorGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("HTML Generator - Pro Edition (With Blueprint)")
        self.root.geometry("1150x800")
        
        # Biến cấu hình
        self.excel_path = tk.StringVar()
        self.json_dir = tk.StringVar(value="json_output")
        self.output_dir = tk.StringVar(value="generated_output")
        
        # Biến chọn Resource
        self.selected_prompt = tk.StringVar()
        self.selected_template = tk.StringVar()
        
        self.log_queue = queue.Queue()
        self.json_data = {} # Lưu dữ liệu bài học đã load
        self.vertex_client = None
        
        self._setup_ui()
        self._setup_logging()
        self._init_vertex()
        
        # Tự động quét tài nguyên khi mở app
        self.root.after(500, self._scan_resources)
        self.root.after(100, self._process_log_queue)

    def _setup_ui(self):
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Notebook (Tabs)
        self.notebook = ttk.Notebook(main_frame)
        self.notebook.pack(fill=tk.BOTH, expand=True, pady=5)
        
        # TAB 1: Dữ liệu
        self.tab_data = ttk.Frame(self.notebook, padding=10)
        self.notebook.add(self.tab_data, text="1. Dữ liệu & Cấu hình")
        self._build_data_tab()
        
        # TAB 2: Sinh HTML
        self.tab_gen = ttk.Frame(self.notebook, padding=10)
        self.notebook.add(self.tab_gen, text="2. Sinh HTML (AI)")
        self._build_gen_tab()
        
        # Log Panel
        log_frame = ttk.LabelFrame(main_frame, text="Nhật ký xử lý")
        log_frame.pack(fill=tk.BOTH, expand=True, pady=5)
        self.log_text = scrolledtext.ScrolledText(log_frame, height=12, state='disabled', font=("Consolas", 9))
        self.log_text.pack(fill=tk.BOTH, expand=True)
        self.progress = ttk.Progressbar(main_frame, mode='indeterminate')
        self.progress.pack(fill=tk.X, pady=2)

    def _build_data_tab(self):
        # Chọn file Excel
        grp_excel = ttk.LabelFrame(self.tab_data, text="Bước 1: Chuyển đổi Excel -> JSON")
        grp_excel.pack(fill=tk.X, pady=10)
        
        f = ttk.Frame(grp_excel)
        f.pack(fill=tk.X, padx=5, pady=5)
        ttk.Entry(f, textvariable=self.excel_path, width=60).pack(side=tk.LEFT, padx=5)
        ttk.Button(f, text="Chọn Excel", command=lambda: self.excel_path.set(filedialog.askopenfilename(filetypes=[("Excel", "*.xlsx")]))).pack(side=tk.LEFT)
        
        ttk.Button(grp_excel, text="🚀 Chuyển đổi ngay", command=self._convert_excel).pack(pady=10)
        
        # Cấu hình đường dẫn
        grp_dir = ttk.LabelFrame(self.tab_data, text="Cấu hình thư mục")
        grp_dir.pack(fill=tk.X, pady=10)
        self._add_path_row(grp_dir, "Thư mục JSON:", self.json_dir)
        self._add_path_row(grp_dir, "Thư mục Output:", self.output_dir)

    def _add_path_row(self, parent, label, var):
        f = ttk.Frame(parent); f.pack(fill=tk.X, padx=5, pady=2)
        ttk.Label(f, text=label, width=15).pack(side=tk.LEFT)
        ttk.Entry(f, textvariable=var).pack(side=tk.LEFT, fill=tk.X, expand=True)
        ttk.Button(f, text="...", width=3, command=lambda: var.set(filedialog.askdirectory())).pack(side=tk.LEFT)

    def _build_gen_tab(self):
        # Khu vực chọn Resources
        res_frame = ttk.LabelFrame(self.tab_gen, text="🎯 Chọn Tài nguyên (Trong thư mục 'resources')")
        res_frame.pack(fill=tk.X, pady=5)
        
        # Dropdown Template
        f1 = ttk.Frame(res_frame); f1.pack(fill=tk.X, padx=5, pady=2)
        ttk.Label(f1, text="Template HTML:", width=15).pack(side=tk.LEFT)
        self.combo_template = ttk.Combobox(f1, textvariable=self.selected_template, state="readonly", width=60)
        self.combo_template.pack(side=tk.LEFT, padx=5)
        
        # Dropdown Prompt
        f2 = ttk.Frame(res_frame); f2.pack(fill=tk.X, padx=5, pady=2)
        ttk.Label(f2, text="Prompt Config:", width=15).pack(side=tk.LEFT)
        self.combo_prompt = ttk.Combobox(f2, textvariable=self.selected_prompt, state="readonly", width=60)
        self.combo_prompt.pack(side=tk.LEFT, padx=5)
        
        ttk.Button(res_frame, text="🔄 Làm mới danh sách", command=self._scan_resources).pack(pady=5)

        # Khu vực chọn bài học
        mid_frame = ttk.Frame(self.tab_gen); mid_frame.pack(fill=tk.X, pady=5)
        ttk.Button(mid_frame, text="📂 Quét các file JSON", command=self._scan_json).pack(side=tk.LEFT)
        
        # Bảng danh sách bài học
        self.tree = ttk.Treeview(self.tab_gen, columns=("ch","ls","st"), show='headings', height=10)
        self.tree.heading("ch", text="Chương"); self.tree.column("ch", width=150)
        self.tree.heading("ls", text="Bài học"); self.tree.column("ls", width=400)
        self.tree.heading("st", text="Trạng thái"); self.tree.column("st", width=120)
        self.tree.pack(fill=tk.BOTH, expand=True, pady=5)
        
        # Nút hành động
        bot_frame = ttk.Frame(self.tab_gen); bot_frame.pack(fill=tk.X, pady=10)
        ttk.Button(bot_frame, text="▶️ BẮT ĐẦU SINH HTML", command=self._start_generation, style="Accent.TButton").pack(side=tk.LEFT, padx=10)
        ttk.Button(bot_frame, text="🌐 Mở thư mục kết quả", command=lambda: os.startfile(self.output_dir.get())).pack(side=tk.LEFT)

    # === LOGIC ===
    def _scan_resources(self):
        """Quét file trong resources/prompts và resources/templates"""
        # Đảm bảo thư mục tồn tại
        os.makedirs("resources/templates", exist_ok=True)
        os.makedirs("resources/prompts", exist_ok=True)
        
        # Quét Templates
        templates = glob.glob("resources/templates/*.html")
        self.combo_template['values'] = templates if templates else ["Chưa có file .html trong resources/templates"]
        if templates: self.combo_template.current(0)

        # Quét Prompts
        prompts = glob.glob("resources/prompts/*.txt")
        self.combo_prompt['values'] = prompts if prompts else ["Chưa có file .txt trong resources/prompts"]
        if prompts: self.combo_prompt.current(0)
            
        logging.info("✅ Đã cập nhật danh sách Template và Prompt.")

    def _convert_excel(self):
        if not self.excel_path.get(): return messagebox.showwarning("Lỗi", "Chưa chọn file Excel")
        def run():
            self.progress.start()
            try:
                pipeline = ExcelToJsonPipeline(self.excel_path.get(), self.json_dir.get())
                if pipeline.load_excel():
                    pipeline.process_all()
                    self.root.after(0, self._scan_json)
            except Exception as e: logging.error(f"Lỗi Convert: {e}")
            finally: self.progress.stop()
        threading.Thread(target=run, daemon=True).start()

    def _scan_json(self):
        self.tree.delete(*self.tree.get_children())
        self.json_data = {}
        json_dir = self.json_dir.get()
        if not os.path.exists(json_dir): return
        
        count = 0
        for f in os.listdir(json_dir):
            if f.endswith('.json'):
                try:
                    with open(os.path.join(json_dir, f), 'r', encoding='utf-8') as file:
                        data = json.load(file)
                        # Xử lý format Dict hoặc List
                        lessons = []
                        if isinstance(data, dict):
                            for ch_lessons in data.values(): lessons.extend(ch_lessons)
                        elif isinstance(data, list):
                            lessons = data
                            
                        for l in lessons:
                            lid = self.tree.insert("", tk.END, values=(l.get('Chương', 'N/A'), l.get('Bài học'), "Ready"))
                            self.json_data[lid] = l
                            count += 1
                except: pass
        logging.info(f"Đã load {count} bài học.")

    def _start_generation(self):
        selected = self.tree.selection()
        if not selected: return messagebox.showwarning("Cảnh báo", "Vui lòng chọn bài học!")
        
        tmpl = self.selected_template.get()
        prmt = self.selected_prompt.get()
        
        if not os.path.exists(tmpl): return messagebox.showerror("Lỗi", "Template không tồn tại!")
        if not os.path.exists(prmt): return messagebox.showerror("Lỗi", "Prompt Config không tồn tại!")

        if not self.vertex_client: return messagebox.showerror("Lỗi", "Chưa kết nối Vertex AI!")

        def run():
            self.progress.start()
            gen = ExperimentGenerator(self.vertex_client, self.output_dir.get())
            total = len(selected)
            for i, item in enumerate(selected):
                data = self.json_data[item]
                logging.info(f"▶️ [{i+1}/{total}] Xử lý: {data.get('Bài học')}")
                self.tree.set(item, "st", "⏳ Working...")
                
                # Gọi hàm sinh code
                res = gen.process_experiment(data, tmpl, prmt)
                
                self.tree.set(item, "st", "✅ Done" if res else "❌ Failed")
            self.progress.stop()
            messagebox.showinfo("Hoàn tất", f"Đã xử lý xong {total} bài.")
            
        threading.Thread(target=run, daemon=True).start()

    def _setup_logging(self):
        h = QueueHandler(self.log_queue)
        h.setFormatter(logging.Formatter('%(asctime)s - %(message)s', '%H:%M:%S'))
        logging.getLogger().addHandler(h); logging.getLogger().setLevel(logging.INFO)

    def _process_log_queue(self):
        while not self.log_queue.empty():
            self.log_text.configure(state='normal')
            self.log_text.insert(tk.END, self.log_queue.get() + "\n")
            self.log_text.see(tk.END)
            self.log_text.configure(state='disabled')
        self.root.after(100, self._process_log_queue)

    def _init_vertex(self):
        try:
            c = get_vertex_ai_credentials()
            if c: 
                self.vertex_client = VertexClient(os.getenv("PROJECT_ID"), c, "gemini-2.5-pro")
                logging.info("✅ Vertex AI Connected.")
            else: logging.error("❌ Vertex AI Creds Error.")
        except: pass

if __name__ == "__main__":
    root = tk.Tk()
    ttk.Style().theme_use('clam') # Giao diện hiện đại hơn default
    app = HTMLGeneratorGUI(root)
    root.mainloop()