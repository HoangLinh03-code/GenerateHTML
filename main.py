# main_v2.py - GUI CẢI TIẾN

import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
import json
import os
import glob
import threading
import logging
import queue
from dotenv import load_dotenv

# Import module cũ
from api.callAPI import VertexClient, get_vertex_ai_credentials
from process.pipeline import ExcelToJsonPipeline

# Import generator mới
from process.generate import EnhancedExperimentGenerator

load_dotenv()

class QueueHandler(logging.Handler):
    def __init__(self, log_queue):
        super().__init__()
        self.log_queue = log_queue
    def emit(self, record):
        self.log_queue.put(self.format(record))

class EnhancedHTMLGeneratorGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("🧪 Advanced HTML Generator - Pro Edition v2.0")
        self.root.geometry("1200x850")
        
        # Biến cấu hình
        self.excel_path = tk.StringVar()
        self.json_dir = tk.StringVar(value="json_output")
        self.output_dir = tk.StringVar(value="generated_output")
        
        # Biến chọn Resource - QUAN TRỌNG: Cho phép chọn từ bất kỳ đâu
        self.selected_prompt = tk.StringVar()
        self.selected_template = tk.StringVar()
        
        # Checkbox cho phép chọn file bên ngoài
        self.allow_external_files = tk.BooleanVar(value=True)
        
        self.log_queue = queue.Queue()
        self.json_data = {}
        self.vertex_client = None
        
        self._setup_ui()
        self._setup_logging()
        self._init_vertex()
        
        # Tự động quét resources
        self.root.after(500, self._scan_resources)
        self.root.after(100, self._process_log_queue)

    def _setup_ui(self):
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Style configuration
        style = ttk.Style()
        style.configure("Accent.TButton", font=("Segoe UI", 10, "bold"))
        
        # Notebook
        self.notebook = ttk.Notebook(main_frame)
        self.notebook.pack(fill=tk.BOTH, expand=True, pady=5)
        
        # TAB 1: Dữ liệu
        self.tab_data = ttk.Frame(self.notebook, padding=10)
        self.notebook.add(self.tab_data, text="📊 1. Dữ liệu & Cấu hình")
        self._build_data_tab()
        
        # TAB 2: Sinh HTML
        self.tab_gen = ttk.Frame(self.notebook, padding=10)
        self.notebook.add(self.tab_gen, text="🎨 2. Sinh HTML (AI Enhanced)")
        self._build_gen_tab()
        
        # TAB 3: Settings
        self.tab_settings = ttk.Frame(self.notebook, padding=10)
        self.notebook.add(self.tab_settings, text="⚙️ 3. Cài đặt nâng cao")
        self._build_settings_tab()
        
        # Log Panel
        log_frame = ttk.LabelFrame(main_frame, text="📋 Nhật ký xử lý")
        log_frame.pack(fill=tk.BOTH, expand=True, pady=5)
        
        self.log_text = scrolledtext.ScrolledText(
            log_frame, 
            height=10, 
            state='disabled', 
            font=("Consolas", 9),
            bg="#1e1e1e",
            fg="#d4d4d4"
        )
        self.log_text.pack(fill=tk.BOTH, expand=True)
        
        self.progress = ttk.Progressbar(main_frame, mode='indeterminate')
        self.progress.pack(fill=tk.X, pady=2)

    def _build_data_tab(self):
        # Excel conversion
        grp_excel = ttk.LabelFrame(self.tab_data, text="📄 Bước 1: Chuyển đổi Excel → JSON")
        grp_excel.pack(fill=tk.X, pady=10, padx=5)
        
        f = ttk.Frame(grp_excel)
        f.pack(fill=tk.X, padx=10, pady=10)
        
        ttk.Label(f, text="File Excel:", width=12).pack(side=tk.LEFT)
        ttk.Entry(f, textvariable=self.excel_path, width=70).pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)
        ttk.Button(f, text="📂 Chọn", command=self._select_excel).pack(side=tk.LEFT, padx=2)
        
        btn_frame = ttk.Frame(grp_excel)
        btn_frame.pack(pady=10)
        ttk.Button(
            btn_frame, 
            text="🚀 Chuyển đổi ngay", 
            command=self._convert_excel,
            style="Accent.TButton"
        ).pack()
        
        # Directories
        grp_dir = ttk.LabelFrame(self.tab_data, text="📁 Cấu hình thư mục")
        grp_dir.pack(fill=tk.X, pady=10, padx=5)
        
        self._add_path_row(grp_dir, "Thư mục JSON:", self.json_dir)
        self._add_path_row(grp_dir, "Thư mục Output:", self.output_dir)

    def _build_gen_tab(self):
        # Resource Selection Frame
        res_frame = ttk.LabelFrame(self.tab_gen, text="🎯 Chọn Tài nguyên (Template & Prompt)")
        res_frame.pack(fill=tk.X, pady=5, padx=5)
        
        # Checkbox cho phép chọn file bên ngoài
        chk_frame = ttk.Frame(res_frame)
        chk_frame.pack(fill=tk.X, padx=10, pady=5)
        ttk.Checkbutton(
            chk_frame,
            text="✅ Cho phép chọn file từ bất kỳ đâu (không chỉ trong resources/)",
            variable=self.allow_external_files,
            command=self._on_external_toggle
        ).pack(anchor=tk.W)
        
        # Template Selection
        tpl_frame = ttk.Frame(res_frame)
        tpl_frame.pack(fill=tk.X, padx=10, pady=5)
        
        ttk.Label(tpl_frame, text="Template HTML:", width=15).pack(side=tk.LEFT)
        self.entry_template = ttk.Entry(tpl_frame, textvariable=self.selected_template, width=60)
        self.entry_template.pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)
        
        self.btn_browse_template = ttk.Button(
            tpl_frame, 
            text="📂", 
            width=3,
            command=self._browse_template
        )
        self.btn_browse_template.pack(side=tk.LEFT, padx=2)
        
        self.combo_template = ttk.Combobox(
            tpl_frame, 
            textvariable=self.selected_template,
            state="readonly",
            width=15
        )
        self.combo_template.pack(side=tk.LEFT, padx=2)
        
        # Prompt Selection
        prm_frame = ttk.Frame(res_frame)
        prm_frame.pack(fill=tk.X, padx=10, pady=5)
        
        ttk.Label(prm_frame, text="Prompt Config:", width=15).pack(side=tk.LEFT)
        self.entry_prompt = ttk.Entry(prm_frame, textvariable=self.selected_prompt, width=60)
        self.entry_prompt.pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)
        
        self.btn_browse_prompt = ttk.Button(
            prm_frame,
            text="📂",
            width=3,
            command=self._browse_prompt
        )
        self.btn_browse_prompt.pack(side=tk.LEFT, padx=2)
        
        self.combo_prompt = ttk.Combobox(
            prm_frame,
            textvariable=self.selected_prompt,
            state="readonly",
            width=15
        )
        self.combo_prompt.pack(side=tk.LEFT, padx=2)
        
        # Refresh button
        ttk.Button(
            res_frame,
            text="🔄 Làm mới danh sách resources",
            command=self._scan_resources
        ).pack(pady=10)
        
        # JSON Selection
        mid_frame = ttk.Frame(self.tab_gen)
        mid_frame.pack(fill=tk.X, pady=5, padx=5)
        
        ttk.Button(
            mid_frame,
            text="📂 Quét các file JSON",
            command=self._scan_json
        ).pack(side=tk.LEFT, padx=5)
        
        ttk.Label(mid_frame, text="Chọn bài học từ danh sách bên dưới:").pack(side=tk.LEFT)
        
        # Treeview
        tree_frame = ttk.Frame(self.tab_gen)
        tree_frame.pack(fill=tk.BOTH, expand=True, pady=5, padx=5)
        
        # Scrollbars
        v_scroll = ttk.Scrollbar(tree_frame, orient=tk.VERTICAL)
        h_scroll = ttk.Scrollbar(tree_frame, orient=tk.HORIZONTAL)
        
        self.tree = ttk.Treeview(
            tree_frame,
            columns=("ch", "ls", "st"),
            show='headings',
            height=12,
            yscrollcommand=v_scroll.set,
            xscrollcommand=h_scroll.set
        )
        
        v_scroll.config(command=self.tree.yview)
        h_scroll.config(command=self.tree.xview)
        
        self.tree.heading("ch", text="Chương")
        self.tree.column("ch", width=200)
        
        self.tree.heading("ls", text="Bài học")
        self.tree.column("ls", width=500)
        
        self.tree.heading("st", text="Trạng thái")
        self.tree.column("st", width=150)
        
        self.tree.grid(row=0, column=0, sticky='nsew')
        v_scroll.grid(row=0, column=1, sticky='ns')
        h_scroll.grid(row=1, column=0, sticky='ew')
        
        tree_frame.grid_rowconfigure(0, weight=1)
        tree_frame.grid_columnconfigure(0, weight=1)
        
        # Action buttons
        bot_frame = ttk.Frame(self.tab_gen)
        bot_frame.pack(fill=tk.X, pady=10, padx=5)
        
        ttk.Button(
            bot_frame,
            text="▶️ BẮT ĐẦU SINH HTML (Enhanced)",
            command=self._start_generation,
            style="Accent.TButton"
        ).pack(side=tk.LEFT, padx=10)
        
        ttk.Button(
            bot_frame,
            text="🌐 Mở thư mục kết quả",
            command=lambda: os.startfile(self.output_dir.get()) if os.path.exists(self.output_dir.get()) else None
        ).pack(side=tk.LEFT)
        
        ttk.Button(
            bot_frame,
            text="🗑️ Xóa tất cả trạng thái",
            command=self._clear_status
        ).pack(side=tk.LEFT, padx=5)

    def _build_settings_tab(self):
        """Tab cài đặt nâng cao"""
        grp_ai = ttk.LabelFrame(self.tab_settings, text="🤖 Cài đặt AI")
        grp_ai.pack(fill=tk.X, pady=10, padx=5)
        
        # Temperature
        f1 = ttk.Frame(grp_ai)
        f1.pack(fill=tk.X, padx=10, pady=5)
        ttk.Label(f1, text="Temperature (0.0-1.0):", width=20).pack(side=tk.LEFT)
        self.temperature_var = tk.DoubleVar(value=0.2)
        ttk.Scale(
            f1,
            from_=0.0,
            to=1.0,
            variable=self.temperature_var,
            orient=tk.HORIZONTAL
        ).pack(side=tk.LEFT, fill=tk.X, expand=True)
        ttk.Label(f1, textvariable=self.temperature_var).pack(side=tk.LEFT)
        
        # Max tokens
        f2 = ttk.Frame(grp_ai)
        f2.pack(fill=tk.X, padx=10, pady=5)
        ttk.Label(f2, text="Max Output Tokens:", width=20).pack(side=tk.LEFT)
        self.max_tokens_var = tk.IntVar(value=16384)
        ttk.Entry(f2, textvariable=self.max_tokens_var, width=10).pack(side=tk.LEFT)
        
        # Design preferences
        grp_design = ttk.LabelFrame(self.tab_settings, text="🎨 Design Preferences")
        grp_design.pack(fill=tk.X, pady=10, padx=5)
        
        f3 = ttk.Frame(grp_design)
        f3.pack(fill=tk.X, padx=10, pady=5)
        ttk.Label(f3, text="Theme:", width=20).pack(side=tk.LEFT)
        self.theme_var = tk.StringVar(value="modern-gradient")
        themes = ["modern-gradient", "glassmorphism", "neumorphism", "minimal"]
        ttk.Combobox(f3, textvariable=self.theme_var, values=themes, state="readonly").pack(side=tk.LEFT, fill=tk.X, expand=True)

    # === FILE SELECTION METHODS ===
    
    def _select_excel(self):
        filename = filedialog.askopenfilename(
            title="Chọn file Excel",
            filetypes=[("Excel files", "*.xlsx *.xls"), ("All files", "*.*")]
        )
        if filename:
            self.excel_path.set(filename)
    
    def _browse_template(self):
        filename = filedialog.askopenfilename(
            title="Chọn Template HTML",
            filetypes=[("HTML files", "*.html"), ("All files", "*.*")],
            initialdir="resources/templates" if not self.allow_external_files.get() else None
        )
        if filename:
            self.selected_template.set(filename)
    
    def _browse_prompt(self):
        filename = filedialog.askopenfilename(
            title="Chọn Prompt Config",
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")],
            initialdir="resources/prompts" if not self.allow_external_files.get() else None
        )
        if filename:
            self.selected_prompt.set(filename)
    
    def _on_external_toggle(self):
        """Khi toggle checkbox, show/hide combobox"""
        if self.allow_external_files.get():
            # Cho phép chọn file bên ngoài - show browse buttons
            self.btn_browse_template.config(state='normal')
            self.btn_browse_prompt.config(state='normal')
            logging.info("✅ Đã BẬT chế độ chọn file từ bất kỳ đâu")
        else:
            # Chỉ dùng resources folder - hide browse buttons
            self.btn_browse_template.config(state='disabled')
            self.btn_browse_prompt.config(state='disabled')
            logging.info("🔒 Chỉ cho phép chọn file trong resources/")

    def _add_path_row(self, parent, label, var):
        f = ttk.Frame(parent)
        f.pack(fill=tk.X, padx=10, pady=5)
        ttk.Label(f, text=label, width=15).pack(side=tk.LEFT)
        ttk.Entry(f, textvariable=var).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        ttk.Button(
            f,
            text="📁",
            width=3,
            command=lambda: var.set(filedialog.askdirectory())
        ).pack(side=tk.LEFT)

    def _scan_resources(self):
        """Quét resources folder"""
        os.makedirs("resources/templates", exist_ok=True)
        os.makedirs("resources/prompts", exist_ok=True)
        
        templates = glob.glob("resources/templates/*.html")
        prompts = glob.glob("resources/prompts/*.txt")
        
        self.combo_template['values'] = templates if templates else ["Không có template"]
        self.combo_prompt['values'] = prompts if prompts else ["Không có prompt"]
        
        if templates:
            self.combo_template.current(0)
            self.selected_template.set(templates[0])
        
        if prompts:
            self.combo_prompt.current(0)
            self.selected_prompt.set(prompts[0])
        
        logging.info(f"✅ Tìm thấy {len(templates)} templates và {len(prompts)} prompts")

    def _convert_excel(self):
        if not self.excel_path.get():
            return messagebox.showwarning("Lỗi", "Chưa chọn file Excel")
        
        def run():
            self.progress.start()
            try:
                pipeline = ExcelToJsonPipeline(self.excel_path.get(), self.json_dir.get())
                if pipeline.load_excel():
                    pipeline.process_all()
                    self.root.after(0, self._scan_json)
                    self.root.after(0, lambda: messagebox.showinfo("Thành công", "Đã chuyển đổi Excel thành JSON!"))
            except Exception as e:
                logging.error(f"Lỗi Convert: {e}")
                self.root.after(0, lambda: messagebox.showerror("Lỗi", str(e)))
            finally:
                self.progress.stop()
        
        threading.Thread(target=run, daemon=True).start()

    def _scan_json(self):
        self.tree.delete(*self.tree.get_children())
        self.json_data = {}
        json_dir = self.json_dir.get()
        
        if not os.path.exists(json_dir):
            logging.warning(f"Thư mục JSON không tồn tại: {json_dir}")
            return
        
        count = 0
        for f in os.listdir(json_dir):
            if f.endswith('.json'):
                try:
                    with open(os.path.join(json_dir, f), 'r', encoding='utf-8') as file:
                        data = json.load(file)
                        
                        lessons = []
                        if isinstance(data, dict):
                            for ch_lessons in data.values():
                                lessons.extend(ch_lessons)
                        elif isinstance(data, list):
                            lessons = data
                        
                        for l in lessons:
                            lid = self.tree.insert(
                                "",
                                tk.END,
                                values=(l.get('Chương', 'N/A'), l.get('Bài học'), "⏳ Chưa xử lý")
                            )
                            self.json_data[lid] = l
                            count += 1
                except Exception as e:
                    logging.error(f"Lỗi đọc {f}: {e}")
        
        logging.info(f"📚 Đã load {count} bài học từ {len(os.listdir(json_dir))} file JSON")

    def _start_generation(self):
        selected = self.tree.selection()
        if not selected:
            return messagebox.showwarning("Cảnh báo", "Vui lòng chọn ít nhất 1 bài học!")
        
        tmpl = self.selected_template.get()
        prmt = self.selected_prompt.get()
        
        if not os.path.exists(tmpl):
            return messagebox.showerror("Lỗi", f"Template không tồn tại:\n{tmpl}")
        if not os.path.exists(prmt):
            return messagebox.showerror("Lỗi", f"Prompt không tồn tại:\n{prmt}")
        
        if not self.vertex_client:
            return messagebox.showerror("Lỗi", "Chưa kết nối Vertex AI!")
        
        def run():
            self.progress.start()
            
            # Sử dụng Enhanced Generator
            gen = EnhancedExperimentGenerator(self.vertex_client, self.output_dir.get())
            
            total = len(selected)
            success = 0
            failed = 0
            
            for i, item in enumerate(selected):
                data = self.json_data[item]
                lesson_name = data.get('Bài học', 'Unknown')
                
                logging.info(f"▶️ [{i+1}/{total}] Đang xử lý: {lesson_name}")
                
                # Update status
                self.root.after(0, lambda it=item: self.tree.set(it, "st", "⏳ Đang sinh..."))
                
                # Generate
                result = gen.process_experiment(data, tmpl, prmt)
                
                if result:
                    success += 1
                    self.root.after(0, lambda it=item: self.tree.set(it, "st", "✅ Thành công"))
                else:
                    failed += 1
                    self.root.after(0, lambda it=item: self.tree.set(it, "st", "❌ Thất bại"))
            
            self.progress.stop()
            
            msg = f"Hoàn thành!\n\n✅ Thành công: {success}\n❌ Thất bại: {failed}\n📊 Tổng: {total}"
            self.root.after(0, lambda: messagebox.showinfo("Kết quả", msg))
        
        threading.Thread(target=run, daemon=True).start()

    def _clear_status(self):
        """Xóa trạng thái của tất cả items"""
        for item in self.tree.get_children():
            self.tree.set(item, "st", "⏳ Chưa xử lý")

    def _setup_logging(self):
        h = QueueHandler(self.log_queue)
        h.setFormatter(logging.Formatter('%(asctime)s - %(message)s', '%H:%M:%S'))
        logging.getLogger().addHandler(h)
        logging.getLogger().setLevel(logging.INFO)

    def _process_log_queue(self):
        while not self.log_queue.empty():
            msg = self.log_queue.get()
            self.log_text.configure(state='normal')
            
            # Color coding
            if "❌" in msg or "ERROR" in msg:
                self.log_text.insert(tk.END, msg + "\n", "error")
                self.log_text.tag_config("error", foreground="#ff6b6b")
            elif "✅" in msg or "SUCCESS" in msg:
                self.log_text.insert(tk.END, msg + "\n", "success")
                self.log_text.tag_config("success", foreground="#51cf66")
            elif "⚠️" in msg or "WARNING" in msg:
                self.log_text.insert(tk.END, msg + "\n", "warning")
                self.log_text.tag_config("warning", foreground="#ffd43b")
            else:
                self.log_text.insert(tk.END, msg + "\n")
            
            self.log_text.see(tk.END)
            self.log_text.configure(state='disabled')
        
        self.root.after(100, self._process_log_queue)

    def _init_vertex(self):
        try:
            c = get_vertex_ai_credentials()
            if c:
                self.vertex_client = VertexClient(os.getenv("PROJECT_ID"), c, "gemini-2.5-pro")
                logging.info("✅ Vertex AI Connected (gemini-2.5-pro)")
            else:
                logging.error("❌ Vertex AI Credentials Error")
        except Exception as e:
            logging.error(f"❌ Vertex Init Error: {e}")

if __name__ == "__main__":
    root = tk.Tk()
    
    # Apply modern theme
    style = ttk.Style()
    style.theme_use('clam')
    
    app = EnhancedHTMLGeneratorGUI(root)
    root.mainloop()