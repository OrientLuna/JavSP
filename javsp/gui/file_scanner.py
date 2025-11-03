"""
文件扫描器和监控器
提供文件扫描状态监控和实时监控功能
"""

import tkinter as tk
from tkinter import ttk, messagebox
import threading
import time
import logging
from pathlib import Path
from typing import List, Dict, Optional
import os

from ..datatype import Movie
from ..scan_cache import get_cache

logger = logging.getLogger(__name__)


class FileScanner:
    """文件扫描器窗口"""

    def __init__(self, parent, app):
        """
        初始化文件扫描器

        Args:
            parent: 父窗口
            app: JavSPApp实例
        """
        self.app = app
        self.window = tk.Toplevel(parent)
        self.window.title("文件扫描器")
        self.window.geometry("700x500")
        self.window.transient(parent)
        self.window.grab_set()

        # 监控状态
        self.is_monitoring = False
        self.monitor_thread = None
        self.monitored_path = None

        # 扫描统计
        self.scan_stats = {
            'total_files': 0,
            'processed_files': 0,
            'new_files': 0,
            'modified_files': 0,
            'start_time': None,
            'end_time': None
        }

        # 创建界面
        self.create_widgets()
        self.update_cache_stats()

        # 居中显示
        self.center_window()

        logger.info("文件扫描器已打开")

    def center_window(self):
        """居中显示窗口"""
        self.window.update_idletasks()
        width = self.window.winfo_width()
        height = self.window.winfo_height()
        x = (self.window.winfo_screenwidth() // 2) - (width // 2)
        y = (self.window.winfo_screenheight() // 2) - (height // 2)
        self.window.geometry(f'{width}x{height}+{x}+{y}')

    def create_widgets(self):
        """创建界面组件"""
        # 主框架
        main_frame = ttk.Frame(self.window, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)

        # 创建notebook
        notebook = ttk.Notebook(main_frame)
        notebook.pack(fill=tk.BOTH, expand=True)

        # 扫描页面
        self.create_scan_tab(notebook)

        # 监控页面
        self.create_monitor_tab(notebook)

        # 缓存页面
        self.create_cache_tab(notebook)

        # 按钮区域
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X, pady=(10, 0))

        ttk.Button(button_frame, text="关闭", command=self.destroy).pack(side=tk.RIGHT)

    def create_scan_tab(self, notebook):
        """创建扫描页面"""
        frame = ttk.Frame(notebook, padding="10")
        notebook.add(frame, text="扫描状态")

        # 路径选择
        path_frame = ttk.Frame(frame)
        path_frame.pack(fill=tk.X, pady=(0, 10))

        ttk.Label(path_frame, text="监控路径:").pack(side=tk.LEFT)
        self.monitor_path_var = tk.StringVar()
        path_entry = ttk.Entry(path_frame, textvariable=self.monitor_path_var, width=40)
        path_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(10, 5))

        ttk.Button(path_frame, text="浏览...", command=self.browse_path).pack(side=tk.LEFT)
        ttk.Button(path_frame, text="开始监控", command=self.start_monitoring).pack(side=tk.LEFT, padx=(5, 0))

        # 统计信息
        stats_frame = ttk.LabelFrame(frame, text="扫描统计", padding="10")
        stats_frame.pack(fill=tk.X, pady=(0, 10))

        # 创建统计标签
        self.stats_labels = {}
        stats_info = [
            ('total_files', '总文件数'),
            ('processed_files', '已处理文件'),
            ('new_files', '新文件'),
            ('modified_files', '修改文件'),
            ('scan_time', '扫描时间')
        ]

        for i, (key, label) in enumerate(stats_info):
            row_frame = ttk.Frame(stats_frame)
            row_frame.grid(row=i, column=0, sticky=tk.W, pady=2)

            ttk.Label(row_frame, text=f"{label}:").pack(side=tk.LEFT)
            self.stats_labels[key] = ttk.Label(row_frame, text="0")
            self.stats_labels[key].pack(side=tk.LEFT, padx=(10, 0))

        # 实时日志
        log_frame = ttk.LabelFrame(frame, text="实时日志", padding="10")
        log_frame.pack(fill=tk.BOTH, expand=True)

        # 创建文本框和滚动条
        log_scroll = ttk.Scrollbar(log_frame)
        log_scroll.pack(side=tk.RIGHT, fill=tk.Y)

        self.log_text = tk.Text(log_frame, height=10, yscrollcommand=log_scroll.set)
        self.log_text.pack(fill=tk.BOTH, expand=True)
        log_scroll.config(command=self.log_text.yview)

        # 配置日志样式
        self.log_text.tag_configure('INFO', foreground='black')
        self.log_text.tag_configure('SUCCESS', foreground='green')
        self.log_text.tag_configure('WARNING', foreground='orange')
        self.log_text.tag_configure('ERROR', foreground='red')

    def create_monitor_tab(self, notebook):
        """创建监控页面"""
        frame = ttk.Frame(notebook, padding="10")
        notebook.add(frame, text="实时监控")

        # 监控设置
        settings_frame = ttk.LabelFrame(frame, text="监控设置", padding="10")
        settings_frame.pack(fill=tk.X, pady=(0, 10))

        # 监控间隔
        interval_frame = ttk.Frame(settings_frame)
        interval_frame.pack(fill=tk.X, pady=(0, 10))

        ttk.Label(interval_frame, text="监控间隔(秒):").pack(side=tk.LEFT)
        self.interval_var = tk.StringVar(value="5")
        interval_spin = ttk.Spinbox(interval_frame, from_=1, to=60, textvariable=self.interval_var, width=10)
        interval_spin.pack(side=tk.LEFT, padx=(10, 0))

        # 文件类型过滤
        filter_frame = ttk.Frame(settings_frame)
        filter_frame.pack(fill=tk.X)

        ttk.Label(filter_frame, text="监控文件类型:").pack(side=tk.LEFT)
        self.filter_var = tk.StringVar(value=".mp4,.avi,.mkv,.mov")
        filter_entry = ttk.Entry(filter_frame, textvariable=self.filter_var, width=30)
        filter_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(10, 0))

        # 监控状态
        status_frame = ttk.LabelFrame(frame, text="监控状态", padding="10")
        status_frame.pack(fill=tk.X, pady=(0, 10))

        self.monitor_status_label = ttk.Label(status_frame, text="未开始监控", foreground='gray')
        self.monitor_status_label.pack()

        self.monitor_progress = ttk.Progressbar(status_frame, mode='indeterminate')
        self.monitor_progress.pack(fill=tk.X, pady=(10, 0))

        # 最近文件变化
        changes_frame = ttk.LabelFrame(frame, text="最近文件变化", padding="10")
        changes_frame.pack(fill=tk.BOTH, expand=True)

        # 创建文件变化列表
        columns = ('时间', '类型', '文件')
        self.changes_tree = ttk.Treeview(changes_frame, columns=columns, show='headings', height=10)

        for col in columns:
            self.changes_tree.heading(col, text=col)
            self.changes_tree.column(col, width=100)

        self.changes_tree.column('文件', width=400)

        # 添加滚动条
        changes_scroll = ttk.Scrollbar(changes_frame, orient=tk.VERTICAL, command=self.changes_tree.yview)
        self.changes_tree.configure(yscrollcommand=changes_scroll.set)

        self.changes_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        changes_scroll.pack(side=tk.RIGHT, fill=tk.Y)

    def create_cache_tab(self, notebook):
        """创建缓存页面"""
        frame = ttk.Frame(notebook, padding="10")
        notebook.add(frame, text="缓存管理")

        # 缓存统计
        cache_stats_frame = ttk.LabelFrame(frame, text="缓存统计", padding="10")
        cache_stats_frame.pack(fill=tk.X, pady=(0, 10))

        self.cache_stats_labels = {}
        cache_info = [
            ('total_files', '总缓存文件'),
            ('existing_files', '存在文件'),
            ('missing_files', '缺失文件'),
            ('unique_movies', '唯一影片'),
            ('cache_size', '缓存大小')
        ]

        for i, (key, label) in enumerate(cache_info):
            row_frame = ttk.Frame(cache_stats_frame)
            row_frame.grid(row=i, column=0, sticky=tk.W, pady=2)

            ttk.Label(row_frame, text=f"{label}:").pack(side=tk.LEFT)
            self.cache_stats_labels[key] = ttk.Label(row_frame, text="0")
            self.cache_stats_labels[key].pack(side=tk.LEFT, padx=(10, 0))

        # 缓存操作
        cache_ops_frame = ttk.LabelFrame(frame, text="缓存操作", padding="10")
        cache_ops_frame.pack(fill=tk.X, pady=(0, 10))

        button_frame = ttk.Frame(cache_ops_frame)
        button_frame.pack()

        ttk.Button(button_frame, text="清理缓存", command=self.cleanup_cache).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(button_frame, text="导出缓存", command=self.export_cache).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(button_frame, text="导入缓存", command=self.import_cache).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(button_frame, text="清空缓存", command=self.clear_cache).pack(side=tk.LEFT)

        # 缓存详情
        cache_details_frame = ttk.LabelFrame(frame, text="缓存详情", padding="10")
        cache_details_frame.pack(fill=tk.BOTH, expand=True)

        # 创建缓存列表
        columns = ('番号', '文件路径', '处理时间', '文件大小')
        self.cache_tree = ttk.Treeview(cache_details_frame, columns=columns, show='headings')

        for col in columns:
            self.cache_tree.heading(col, text=col)
            self.cache_tree.column(col, width=120)

        self.cache_tree.column('文件路径', width=300)

        # 添加滚动条
        cache_scroll = ttk.Scrollbar(cache_details_frame, orient=tk.VERTICAL, command=self.cache_tree.yview)
        self.cache_tree.configure(yscrollcommand=cache_scroll.set)

        self.cache_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        cache_scroll.pack(side=tk.RIGHT, fill=tk.Y)

    def browse_path(self):
        """浏览路径"""
        path = tk.filedialog.askdirectory(title="选择监控路径")
        if path:
            self.monitor_path_var.set(path)

    def start_monitoring(self):
        """开始监控"""
        if self.is_monitoring:
            self.stop_monitoring()
            return

        path = self.monitor_path_var.get().strip()
        if not path:
            messagebox.showwarning("警告", "请选择监控路径")
            return

        if not Path(path).exists():
            messagebox.showerror("错误", "选择的路径不存在")
            return

        self.monitored_path = path
        self.is_monitoring = True
        self.monitor_status_label.config(text="正在监控...", foreground='green')
        self.monitor_progress.start(10)

        # 启动监控线程
        self.monitor_thread = threading.Thread(target=self.monitor_loop, daemon=True)
        self.monitor_thread.start()

        self.add_log(f"开始监控: {path}", 'SUCCESS')

    def stop_monitoring(self):
        """停止监控"""
        self.is_monitoring = False
        self.monitor_status_label.config(text="监控已停止", foreground='gray')
        self.monitor_progress.stop()
        self.add_log("监控已停止", 'WARNING')

    def monitor_loop(self):
        """监控循环"""
        file_states = {}  # 记录文件状态

        try:
            interval = int(self.interval_var.get())
            extensions = [ext.strip() for ext in self.filter_var.get().split(',') if ext.strip()]
        except ValueError:
            interval = 5
            extensions = ['.mp4', '.avi', '.mkv', '.mov']

        while self.is_monitoring:
            try:
                # 扫描文件变化
                current_files = self.scan_directory(self.monitored_path, extensions)

                for file_path in current_files:
                    current_mtime = os.path.getmtime(file_path)
                    current_size = os.path.getsize(file_path)

                    if file_path in file_states:
                        old_mtime, old_size = file_states[file_path]
                        if current_mtime > old_mtime or current_size != old_size:
                            # 文件被修改
                            self.window.after(0, self.add_file_change, '修改', file_path)
                    else:
                        # 新文件
                        self.window.after(0, self.add_file_change, '新增', file_path)

                    file_states[file_path] = (current_mtime, current_size)

                # 检查删除的文件
                deleted_files = set(file_states.keys()) - set(current_files)
                for file_path in deleted_files:
                    del file_states[file_path]
                    self.window.after(0, self.add_file_change, '删除', file_path)

                time.sleep(interval)

            except Exception as e:
                self.window.after(0, self.add_log, f"监控出错: {e}", 'ERROR')
                time.sleep(interval)

    def scan_directory(self, path: str, extensions: List[str]) -> List[str]:
        """扫描目录中的文件"""
        files = []
        try:
            for root, dirs, filenames in os.walk(path):
                for filename in filenames:
                    file_path = os.path.join(root, filename)
                    if any(filename.lower().endswith(ext.lower()) for ext in extensions):
                        files.append(file_path)
        except Exception as e:
            self.add_log(f"扫描目录出错: {e}", 'ERROR')

        return files

    def add_file_change(self, change_type: str, file_path: str):
        """添加文件变化记录"""
        import datetime
        timestamp = datetime.datetime.now().strftime("%H:%M:%S")

        # 添加到变化列表
        self.changes_tree.insert('', 0, values=(timestamp, change_type, file_path))

        # 限制显示数量
        items = self.changes_tree.get_children()
        if len(items) > 100:
            self.changes_tree.delete(items[-1])

        # 添加到日志
        self.add_log(f"文件{change_type}: {file_path}", 'INFO')

    def add_log(self, message: str, level: str = 'INFO'):
        """添加日志消息"""
        import datetime
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_entry = f"[{timestamp}] {message}\n"

        self.log_text.insert(tk.END, log_entry, level)
        self.log_text.see(tk.END)

        # 限制日志长度
        lines = self.log_text.get('1.0', tk.END).split('\n')
        if len(lines) > 1000:
            self.log_text.delete('1.0', '100.0')

    def update_cache_stats(self):
        """更新缓存统计"""
        try:
            cache = get_cache()
            stats = cache.get_cache_stats()

            self.cache_stats_labels['total_files'].config(text=str(stats.get('total_files', 0)))
            self.cache_stats_labels['existing_files'].config(text=str(stats.get('existing_files', 0)))
            self.cache_stats_labels['missing_files'].config(text=str(stats.get('missing_files', 0)))
            self.cache_stats_labels['unique_movies'].config(text=str(stats.get('unique_movies', 0)))

            # 计算缓存大小
            cache_file = Path(stats.get('cache_file', ''))
            if cache_file.exists():
                size = cache_file.stat().st_size
                size_str = self.format_size(size)
            else:
                size_str = "0 B"

            self.cache_stats_labels['cache_size'].config(text=size_str)

            # 更新缓存详情列表
            self.update_cache_details(cache)

        except Exception as e:
            self.add_log(f"更新缓存统计失败: {e}", 'ERROR')

    def update_cache_details(self, cache):
        """更新缓存详情列表"""
        # 清空现有项目
        for item in self.cache_tree.get_children():
            self.cache_tree.delete(item)

        # 添加缓存项目
        try:
            for file_path, cache_entry in cache.cache_data.items():
                movie_id = cache_entry.get('movie_id', 'Unknown')
                processed_at = cache_entry.get('processed_at', 'Unknown')
                file_size = cache_entry.get('size', 0)

                # 格式化文件大小
                size_str = self.format_size(file_size)

                # 限制路径显示长度
                display_path = file_path
                if len(display_path) > 80:
                    display_path = '...' + display_path[-77:]

                self.cache_tree.insert('', 'end', values=(movie_id, display_path, processed_at, size_str))

        except Exception as e:
            self.add_log(f"更新缓存详情失败: {e}", 'ERROR')

    def format_size(self, size_bytes: int) -> str:
        """格式化文件大小"""
        if size_bytes == 0:
            return "0 B"

        size_names = ["B", "KB", "MB", "GB", "TB"]
        i = 0
        size = float(size_bytes)

        while size >= 1024.0 and i < len(size_names) - 1:
            size /= 1024.0
            i += 1

        return f"{size:.1f} {size_names[i]}"

    def cleanup_cache(self):
        """清理缓存"""
        try:
            cache = get_cache()
            removed_count = cache.cleanup_missing_files()
            messagebox.showinfo("完成", f"清理完成，删除了 {removed_count} 个无效记录")
            self.update_cache_stats()
            self.add_log(f"清理缓存完成，删除 {removed_count} 条记录", 'SUCCESS')

        except Exception as e:
            messagebox.showerror("错误", f"清理缓存失败: {e}")

    def export_cache(self):
        """导出缓存"""
        file_path = tk.filedialog.asksaveasfilename(
            title="导出缓存",
            defaultextension=".json",
            filetypes=[("JSON文件", "*.json"), ("所有文件", "*.*")]
        )
        if file_path:
            try:
                cache = get_cache()
                cache.export_cache(file_path)
                messagebox.showinfo("完成", "缓存导出成功")
                self.add_log(f"缓存已导出到: {file_path}", 'SUCCESS')

            except Exception as e:
                messagebox.showerror("错误", f"导出缓存失败: {e}")

    def import_cache(self):
        """导入缓存"""
        file_path = tk.filedialog.askopenfilename(
            title="导入缓存",
            filetypes=[("JSON文件", "*.json"), ("所有文件", "*.*")]
        )
        if file_path:
            try:
                result = messagebox.askyesno("确认", "导入缓存会与现有缓存合并，是否继续？")
                if result:
                    cache = get_cache()
                    cache.import_cache(file_path, merge=True)
                    self.update_cache_stats()
                    messagebox.showinfo("完成", "缓存导入成功")
                    self.add_log(f"缓存已从 {file_path} 导入", 'SUCCESS')

            except Exception as e:
                messagebox.showerror("错误", f"导入缓存失败: {e}")

    def clear_cache(self):
        """清空缓存"""
        result = messagebox.askyesno("确认", "确定要清空所有缓存吗？此操作不可恢复！")
        if result:
            try:
                cache = get_cache()
                cache.clear_cache()
                self.update_cache_stats()
                messagebox.showinfo("完成", "缓存已清空")
                self.add_log("缓存已清空", 'WARNING')

            except Exception as e:
                messagebox.showerror("错误", f"清空缓存失败: {e}")

    def show(self):
        """显示窗口"""
        self.window.deiconify()
        self.window.lift()

    def destroy(self):
        """销毁窗口"""
        if self.is_monitoring:
            self.stop_monitoring()
        self.window.destroy()