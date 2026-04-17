import argparse
import os
import re
import sys
import unicodedata
import threading
import traceback
import tkinter as tk
from tkinter import filedialog, scrolledtext, messagebox, ttk
from bs4 import BeautifulSoup
from markdownify import markdownify as md

# --- Cấu hình đường dẫn ---
BASE_DIR = r"D:\Dichtrung"
INPUT_SOURCE = os.path.join(BASE_DIR, "Source", "Source full")
OUTPUT_SPLIT = os.path.join(BASE_DIR, "Source", "Source split")

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

def remove_vietnamese_accents(text):
    """Xóa dấu tiếng Việt chuẩn để tạo tên thư mục/file."""
    text = text.replace('đ', 'd').replace('Đ', 'D')
    nfkd_form = unicodedata.normalize('NFKD', text)
    only_ascii = nfkd_form.encode('ASCII', 'ignore').decode('utf-8')
    return only_ascii

def create_safe_name(filename):
    """Giữ lại ký tự an toàn, xóa ký tự cấm của Windows."""
    safe_name = re.sub(r'[\\/*?:"<>|\n\r]', "", filename)
    safe_name = " ".join(safe_name.split())
    if len(safe_name) > 100:
        safe_name = safe_name[:100]
    return safe_name.strip()

def process_files(filepaths, log_func):
    os.makedirs(BASE_DIR, exist_ok=True)
    os.makedirs(INPUT_SOURCE, exist_ok=True)
    os.makedirs(OUTPUT_SPLIT, exist_ok=True)

    for filepath in filepaths:
        filename = os.path.basename(filepath)
        name_no_ext = os.path.splitext(filename)[0]

        safe_folder_name = create_safe_name(remove_vietnamese_accents(name_no_ext))
        output_dir = os.path.join(OUTPUT_SPLIT, safe_folder_name)
        os.makedirs(output_dir, exist_ok=True)

        log_func(f"\n[Bắt đầu] {filename}\n")
        log_func(f"  -> Đích: {output_dir}\n")

        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                html_content = f.read()

            soup = BeautifulSoup(html_content, "html.parser")
            for tag in soup(["script", "style"]):
                tag.extract()
            for a_tag in soup.find_all('a', href=True):
                if a_tag['href'].startswith('#chapter'):
                    a_tag.extract()

            md_text = md(str(soup), heading_style="ATX")

            pattern = re.compile(r'(?m)^#+\s+(.*(?:Chương|Hồi|Phần|Quyển|Tiết|Chapter|章|篇|卷|回).*)$', re.IGNORECASE)
            matches = list(pattern.finditer(md_text))

            if not matches:
                with open(os.path.join(output_dir, "NoChapters_Full.md"), 'w', encoding='utf-8') as f:
                    f.write(md_text.strip())
                log_func("  -> Cảnh báo: Không tách được chương. Đã lưu 1 file duy nhất.\n")
                continue

            for i, match in enumerate(matches):
                title = match.group(1).strip()
                safe_title = create_safe_name(title)
                start_idx = match.start()
                end_idx = matches[i + 1].start() if i + 1 < len(matches) else len(md_text)
                chapter_content = md_text[start_idx:end_idx].strip()
                file_out_name = f"{i + 1:04d} - {safe_title}.md"
                with open(os.path.join(output_dir, file_out_name), 'w', encoding='utf-8') as f:
                    f.write(chapter_content)

            log_func(f"  -> Thành công: Đã tách {len(matches)} chương.\n")

        except Exception as exc:
            log_func(f"  -> [LỖI]: {exc}\n")
            log_func(traceback.format_exc())

def parse_args():
    parser = argparse.ArgumentParser(
        description="Tách file HTML truyện thành các chương Markdown trong Source/Source split/."
    )
    parser.add_argument(
        "--file",
        dest="files",
        action="append",
        help="Đường dẫn tới file HTML cần tách. Có thể truyền nhiều lần.",
    )
    parser.add_argument(
        "--batch",
        action="store_true",
        help="Tách toàn bộ file .html trong Source/Source full.",
    )
    return parser.parse_args()

def cli_log(message):
    print(message, end="" if message.endswith("\n") else "\n")

def run_cli(args):
    files = []

    if args.files:
        files.extend(os.path.abspath(path) for path in args.files)

    if args.batch:
        batch_files = [
            os.path.join(INPUT_SOURCE, f)
            for f in os.listdir(INPUT_SOURCE)
            if f.lower().endswith(".html")
        ]
        files.extend(batch_files)

    if not files:
        return False

    unique_files = []
    seen = set()
    for filepath in files:
        if filepath not in seen:
            unique_files.append(filepath)
            seen.add(filepath)

    missing_files = [filepath for filepath in unique_files if not os.path.isfile(filepath)]
    if missing_files:
        for filepath in missing_files:
            cli_log(f"[LỖI] Không tìm thấy file: {filepath}")
        return True

    process_files(unique_files, cli_log)
    cli_log("\n>>> HOÀN THÀNH TẤT CẢ CÁC TÁC VỤ <<<")
    return True

class NovelConverterApp:
    def __init__(self, root):
        self.root = root
        self.root.title("HTML to Markdown - Folder Structure Optimized")
        self.root.geometry("700x550")
        
        # Tạo thư mục gốc nếu chưa có
        os.makedirs(BASE_DIR, exist_ok=True)
        os.makedirs(INPUT_SOURCE, exist_ok=True)
        os.makedirs(OUTPUT_SPLIT, exist_ok=True)

        self.setup_ui()

    def setup_ui(self):
        # Header nút bấm
        btn_frame = ttk.Frame(self.root, padding="15")
        btn_frame.pack(fill=tk.X)

        self.btn_single = ttk.Button(btn_frame, text="Chọn file HTML lẻ", command=self.process_single)
        self.btn_single.pack(side=tk.LEFT, padx=5)

        self.btn_batch = ttk.Button(btn_frame, text="Chạy hàng loạt từ thư mục Source", command=self.process_batch)
        self.btn_batch.pack(side=tk.LEFT, padx=5)

        # Thông tin đường dẫn
        info_frame = ttk.Frame(self.root, padding="10")
        info_frame.pack(fill=tk.X)
        ttk.Label(info_frame, text=f"Đầu vào: {INPUT_SOURCE}", foreground="gray").pack(anchor=tk.W)
        ttk.Label(info_frame, text=f"Cấu trúc đầu ra: {OUTPUT_SPLIT}\\[Tên Truyện]\\", font=('Segoe UI', 9, 'bold')).pack(anchor=tk.W)

        # Khung hiển thị Log
        self.log_area = scrolledtext.ScrolledText(self.root, wrap=tk.WORD, height=20, bg="#f0f0f0")
        self.log_area.pack(fill=tk.BOTH, expand=True, padx=15, pady=10)
        self.log("Phần mềm đã sẵn sàng. Chào mừng bạn!\n")

    def log(self, message):
        self.log_area.insert(tk.END, message)
        self.log_area.see(tk.END)

    def process_single(self):
        filepath = filedialog.askopenfilename(
            initialdir=INPUT_SOURCE,
            title="Chọn file HTML",
            filetypes=(("HTML files", "*.html"), ("All files", "*.*"))
        )
        if filepath:
            self.run_task(self.execute_logic, [filepath])

    def process_batch(self):
        files = [os.path.join(INPUT_SOURCE, f) for f in os.listdir(INPUT_SOURCE) if f.endswith('.html')]
        if not files:
            messagebox.showinfo("Lưu ý", f"Thư mục {INPUT_SOURCE} hiện tại không có file .html nào.")
            return
        if messagebox.askyesno("Xác nhận", f"Tìm thấy {len(files)} file truyện. Bắt đầu xử lý?"):
            self.run_task(self.execute_logic, files)

    def run_task(self, target, args):
        self.btn_single.config(state=tk.DISABLED)
        self.btn_batch.config(state=tk.DISABLED)
        threading.Thread(target=self.thread_handler, args=(target, args), daemon=True).start()

    def thread_handler(self, target, args):
        target(args)
        self.root.after(0, lambda: self.btn_single.config(state=tk.NORMAL))
        self.root.after(0, lambda: self.btn_batch.config(state=tk.NORMAL))
        self.log("\n>>> HOÀN THÀNH TẤT CẢ CÁC TÁC VỤ <<<\n")

    def execute_logic(self, filepaths):
        process_files(filepaths, self.log)

if __name__ == "__main__":
    args = parse_args()
    if run_cli(args):
        sys.exit(0)

    root = tk.Tk()
    app = NovelConverterApp(root)
    root.mainloop()
