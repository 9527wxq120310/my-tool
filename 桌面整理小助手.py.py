import os
import sys
import shutil
import ctypes
import threading
from pathlib import Path
from tkinter import Tk, Frame, Label, Button, Entry, StringVar, messagebox, ttk, filedialog

def is_admin():
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except Exception:
        return False

def run_as_admin():
    try:
        ctypes.windll.shell32.ShellExecuteW(
            None, "runas", sys.executable, " ".join(sys.argv), None, 1
        )
    except Exception:
        pass

CATEGORIES = {
    "文档": [".pdf", ".doc", ".docx", ".txt", ".pptx", ".xlsx", ".md", ".rtf", ".csv"],
    "图片": [".jpg", ".jpeg", ".png", ".gif", ".bmp", ".svg", ".webp", ".ico"],
    "视频": [".mp4", ".avi", ".mov", ".mkv", ".flv", ".wmv"],
    "音频": [".mp3", ".wav", ".flac", ".m4a", ".aac"],
    "压缩包": [".zip", ".rar", ".7z", ".tar", ".gz"],
    "程序": [".exe", ".msi", ".apk", ".dmg"],
    "代码": [".py", ".js", ".html", ".css", ".java", ".cpp", ".c", ".h"],
}

def organize_folder(folder_path):
    folder = Path(folder_path)
    moved = 0
    skipped = 0
    for item in folder.iterdir():
        if not item.is_file():
            continue
        ext = item.suffix.lower()
        category = "其他"
        for cat, exts in CATEGORIES.items():
            if ext in exts:
                category = cat
                break
        dest_dir = folder / category
        dest_dir.mkdir(exist_ok=True)
        dest = dest_dir / item.name
        if dest.exists():
            counter = 1
            while dest.exists():
                dest = dest_dir / f"{item.stem}_{counter}{item.suffix}"
                counter += 1
        try:
            shutil.move(str(item), str(dest))
            moved += 1
        except Exception:
            skipped += 1
    return moved, skipped

def get_temp_dirs():
    dirs = []
    try:
        user_temp = os.environ.get("TEMP", "")
        if user_temp and os.path.isdir(user_temp):
            dirs.append(("用户临时文件", user_temp))
    except Exception:
        pass
    try:
        win_temp = os.path.join(os.environ.get("WINDIR", "C:\\Windows"), "Temp")
        if os.path.isdir(win_temp):
            dirs.append(("系统临时文件", win_temp))
    except Exception:
        pass
    try:
        prefetch = os.path.join(os.environ.get("WINDIR", "C:\\Windows"), "Prefetch")
        if os.path.isdir(prefetch):
            dirs.append(("Prefetch缓存", prefetch))
    except Exception:
        pass
    return dirs

def format_size(size_bytes):
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f} KB"
    elif size_bytes < 1024 * 1024 * 1024:
        return f"{size_bytes / (1024 * 1024):.1f} MB"
    else:
        return f"{size_bytes / (1024 * 1024 * 1024):.2f} GB"

def scan_temp():
    dirs = get_temp_dirs()
    results = []
    total_size = 0
    total_files = 0
    for name, path in dirs:
        size = 0
        count = 0
        try:
            for root, _, files in os.walk(path):
                for f in files:
                    fp = os.path.join(root, f)
                    try:
                        size += os.path.getsize(fp)
                        count += 1
                    except Exception:
                        pass
        except Exception:
            pass
        results.append((name, path, count, size))
        total_size += size
        total_files += count
    return results, total_files, total_size

def clean_temp(paths_to_clean):
    deleted = 0
    failed = 0
    for path in paths_to_clean:
        try:
            if os.path.isfile(path):
                os.remove(path)
                deleted += 1
            elif os.path.isdir(path):
                shutil.rmtree(path, ignore_errors=True)
                deleted += 1
        except Exception:
            failed += 1
    return deleted, failed

def collect_all_temp_files(dirs):
    files = []
    for _, path in dirs:
        try:
            for root, _, filenames in os.walk(path):
                for f in filenames:
                    files.append(os.path.join(root, f))
        except Exception:
            pass
    return files


class App:
    def __init__(self, root):
        self.root = root
        self.root.title("桌面整理小助手")
        self.root.geometry("620x520")
        self.root.resizable(False, False)

        notebook = ttk.Notebook(root)
        notebook.pack(fill="both", expand=True, padx=10, pady=10)

        self.build_desktop_tab(notebook)
        self.build_clean_tab(notebook)
        self.build_search_tab(notebook)

    def build_desktop_tab(self, notebook):
        tab = Frame(notebook)
        notebook.add(tab, text="桌面整理")

        Label(tab, text="选择要整理的文件夹：", font=("微软雅黑", 10)).pack(pady=(15, 5))
        self.desktop_var = StringVar(value=str(Path.home() / "Desktop"))
        Entry(tab, textvariable=self.desktop_var, width=50, font=("微软雅黑", 9)).pack(pady=5)

        btn_frame = Frame(tab)
        btn_frame.pack(pady=5)
        Button(btn_frame, text="选择文件夹", command=self.select_folder, font=("微软雅黑", 9)).pack(side="left", padx=5)
        Button(btn_frame, text="开始整理", command=self.start_organize, bg="#4CAF50", fg="white", font=("微软雅黑", 9)).pack(side="left", padx=5)

        self.org_status = StringVar(value="就绪")
        Label(tab, textvariable=self.org_status, font=("微软雅黑", 9), fg="#555").pack(pady=10)

    def select_folder(self):
        folder = filedialog.askdirectory()
        if folder:
            self.desktop_var.set(folder)

    def start_organize(self):
        folder = self.desktop_var.get().strip()
        if not folder or not os.path.isdir(folder):
            messagebox.showwarning("提示", "请选择一个有效的文件夹")
            return
        if not messagebox.askyesno("确认", f"确定要整理\n{folder}\n中的文件吗？"):
            return
        self.org_status.set("正在整理...")
        self.root.update()

        def task():
            try:
                moved, skipped = organize_folder(folder)
                self.root.after(0, lambda: self.org_status.set(
                    f"整理完成！移动 {moved} 个文件，跳过 {skipped} 个"
                ))
            except Exception as e:
                self.root.after(0, lambda: self.org_status.set(f"整理失败：{e}"))

        threading.Thread(target=task, daemon=True).start()

    def build_clean_tab(self, notebook):
        tab = Frame(notebook)
        notebook.add(tab, text="C盘清理")

        Label(tab, text="扫描并清理临时文件、缓存文件", font=("微软雅黑", 10)).pack(pady=(15, 5))

        btn_frame = Frame(tab)
        btn_frame.pack(pady=5)
        Button(btn_frame, text="扫描垃圾", command=self.start_scan, font=("微软雅黑", 9)).pack(side="left", padx=5)
        self.clean_btn = Button(btn_frame, text="开始清理", command=self.start_clean,
                                bg="#f44336", fg="white", font=("微软雅黑", 9), state="disabled")
        self.clean_btn.pack(side="left", padx=5)

        self.cl_status = StringVar(value="请先扫描")
        Label(tab, textvariable=self.cl_status, font=("微软雅黑", 9), fg="#555").pack(pady=5)

        columns = ("名称", "路径", "文件数", "大小")
        self.tree = ttk.Treeview(tab, columns=columns, show="headings", height=10)
        for col in columns:
            self.tree.heading(col, text=col)
            self.tree.column(col, width=130)
        self.tree.pack(fill="both", expand=True, padx=10, pady=5)

        self.scan_results = []
        self.all_temp_files = []

    def start_scan(self):
        self.cl_status.set("正在扫描...")
        self.root.update()

        def task():
            try:
                results, total_files, total_size = scan_temp()
                self.scan_results = results
                self.all_temp_files = collect_all_temp_files(get_temp_dirs())
                self.root.after(0, lambda: self.update_scan_ui(results, total_files, total_size))
            except Exception as e:
                self.root.after(0, lambda: self.cl_status.set(f"扫描失败：{e}"))

        threading.Thread(target=task, daemon=True).start()

    def update_scan_ui(self, results, total_files, total_size):
        for item in self.tree.get_children():
            self.tree.delete(item)
        for name, path, count, size in results:
            self.tree.insert("", "end", values=(name, path, count, format_size(size)))
        self.cl_status.set(f"扫描完成：共 {total_files} 个文件，约 {format_size(total_size)}")
        self.clean_btn.config(state="normal")

    def start_clean(self):
        if not self.all_temp_files:
            messagebox.showwarning("提示", "请先扫描")
            return
        if not messagebox.askyesno("确认", "确定要清理这些临时文件吗？\n被占用的文件会自动跳过。"):
            return
        self.cl_status.set("正在清理...")
        self.clean_btn.config(state="disabled")
        self.root.update()

        def task():
            try:
                deleted, failed = clean_temp(self.all_temp_files)
                self.root.after(0, lambda: self.finish_clean(deleted, failed))
            except Exception as e:
                self.root.after(0, lambda: self.cl_status.set(f"清理失败：{e}"))

        threading.Thread(target=task, daemon=True).start()

    def finish_clean(self, deleted, failed):
        self.cl_status.set(f"清理完成：成功 {deleted} 个，跳过/失败 {failed} 个")
        self.clean_btn.config(state="disabled")
        self.all_temp_files.clear()

    def build_search_tab(self, notebook):
        tab = Frame(notebook)
        notebook.add(tab, text="文件搜索")

        Label(tab, text="搜索文件夹：", font=("微软雅黑", 9)).pack(pady=(10, 3))
        self.search_dir_var = StringVar(value=str(Path.home() / "Desktop"))
        Entry(tab, textvariable=self.search_dir_var, width=55, font=("微软雅黑", 9)).pack(pady=3)

        Label(tab, text="搜索关键词：", font=("微软雅黑", 9)).pack(pady=(5, 3))
        self.search_kw_var = StringVar()
        Entry(tab, textvariable=self.search_kw_var, width=55, font=("微软雅黑", 9)).pack(pady=3)

        btn_frame = Frame(tab)
        btn_frame.pack(pady=5)
        Button(btn_frame, text="选择目录", command=self.select_search_dir, font=("微软雅黑", 9)).pack(side="left", padx=5)
        Button(btn_frame, text="开始搜索", command=self.start_search, bg="#2196F3", fg="white", font=("微软雅黑", 9)).pack(side="left", padx=5)

        self.sr_status = StringVar(value="输入关键词后搜索")
        Label(tab, textvariable=self.sr_status, font=("微软雅黑", 9), fg="#555").pack(pady=5)

        columns = ("文件名", "所在文件夹")
        self.search_tree = ttk.Treeview(tab, columns=columns, show="headings", height=10)
        self.search_tree.heading("文件名", text="文件名")
        self.search_tree.heading("所在文件夹", text="所在文件夹")
        self.search_tree.column("文件名", width=200)
        self.search_tree.column("所在文件夹", width=350)
        self.search_tree.pack(fill="both", expand=True, padx=10, pady=5)

        self.search_tree.bind("<Double-1>", self.open_file)

    def select_search_dir(self):
        folder = filedialog.askdirectory()
        if folder:
            self.search_dir_var.set(folder)

    def start_search(self):
        keyword = self.search_kw_var.get().strip().lower()
        search_dir = self.search_dir_var.get().strip()
        if not keyword:
            messagebox.showwarning("提示", "请输入搜索关键词")
            return
        if not search_dir or not os.path.isdir(search_dir):
            messagebox.showwarning("提示", "请选择一个有效的文件夹")
            return

        self.sr_status.set("正在搜索...")
        for item in self.search_tree.get_children():
            self.search_tree.delete(item)
        self.root.update()

        def task():
            results = []
            try:
                for root, _, files in os.walk(search_dir):
                    for f in files:
                        if keyword in f.lower():
                            results.append((f, root))
            except Exception:
                pass

            def update():
                for name, folder in results:
                    self.search_tree.insert("", "end", values=(name, folder))
                self.sr_status.set(f"搜索完成，找到 {len(results)} 个文件")

            self.root.after(0, update)

        threading.Thread(target=task, daemon=True).start()

    def open_file(self, event):
        item = self.search_tree.selection()
        if not item:
            return
        values = self.search_tree.item(item[0], "values")
        if len(values) >= 2:
            filepath = os.path.join(values[1], values[0])
            if os.path.exists(filepath):
                os.startfile(filepath)


def main():
    if os.name == "nt" and not is_admin():
        run_as_admin()
        sys.exit()

    root = Tk()
    App(root)
    root.mainloop()

if __name__ == "__main__":
    main()
