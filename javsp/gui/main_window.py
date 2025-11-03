"""
JavSP主窗口
提供主要的用户界面和功能入口
"""

import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import logging
from pathlib import Path
from typing import List, Optional

from ..datatype import Movie

logger = logging.getLogger(__name__)


class MainWindow:
    """主窗口类"""

    def __init__(self, root: tk.Tk, app):
        """
        初始化主窗口

        Args:
            root: Tk根窗口
            app: JavSPApp实例
        """
        self.root = root
        self.app = app
        self.window = root

        # 界面元素
        self.status_bar = None
        self.progress_bar = None
        self.status_label = None
        self.scan_tree = None
        self.scan_button = None
        self.stop_button = None
        self.config_button = None
        self.clear_cache_button = None

        # 数据
        self.scan_results: List[Movie] = []

        # 创建界面
        self.create_widgets()
        self.create_menu()
        self.create_status_bar()

        logger.info("主窗口创建完成")

    def create_widgets(self):
        """创建界面组件"""
        # 主框架
        main_frame = ttk.Frame(self.window, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))

        # 配置网格权重
        self.window.columnconfigure(0, weight=1)
        self.window.rowconfigure(0, weight=1)
        main_frame.columnconfigure(1, weight=1)
        main_frame.rowconfigure(1, weight=1)

        # 标题
        title_label = ttk.Label(
            main_frame,
            text="JavSP - AV元数据刮削器",
            style='Title.TLabel'
        )
        title_label.grid(row=0, column=0, columnspan=3, pady=(0, 20))

        # 控制面板
        self.create_control_panel(main_frame)

        # 扫描结果区域
        self.create_results_area(main_frame)

    def create_control_panel(self, parent):
        """创建控制面板"""
        control_frame = ttk.LabelFrame(parent, text="控制面板", padding="10")
        control_frame.grid(row=1, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=(0, 10))

        # 文件夹选择
        folder_frame = ttk.Frame(control_frame)
        folder_frame.grid(row=0, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 10))
        folder_frame.columnconfigure(1, weight=1)

        ttk.Label(folder_frame, text="扫描文件夹:").grid(row=0, column=0, padx=(0, 10))

        self.folder_var = tk.StringVar()
        folder_entry = ttk.Entry(folder_frame, textvariable=self.folder_var, width=50)
        folder_entry.grid(row=0, column=1, sticky=(tk.W, tk.E), padx=(0, 10))

        browse_button = ttk.Button(
            folder_frame,
            text="浏览...",
            command=self.browse_folder
        )
        browse_button.grid(row=0, column=2)

        # 操作按钮
        button_frame = ttk.Frame(control_frame)
        button_frame.grid(row=1, column=0, columnspan=2, sticky=(tk.W, tk.E))

        self.scan_button = ttk.Button(
            button_frame,
            text="开始扫描",
            command=self.start_scan
        )
        self.scan_button.grid(row=0, column=0, padx=(0, 10))

        self.stop_button = ttk.Button(
            button_frame,
            text="停止扫描",
            command=self.stop_scan,
            state=tk.DISABLED
        )
        self.stop_button.grid(row=0, column=1, padx=(0, 10))

        self.config_button = ttk.Button(
            button_frame,
            text="配置设置",
            command=self.app.open_config_editor
        )
        self.config_button.grid(row=0, column=2, padx=(0, 10))

        self.clear_cache_button = ttk.Button(
            button_frame,
            text="清空缓存",
            command=self.app.clear_cache
        )
        self.clear_cache_button.grid(row=0, column=3, padx=(0, 10))

        # 选项
        options_frame = ttk.Frame(control_frame)
        options_frame.grid(row=2, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(10, 0))

        self.force_rescan_var = tk.BooleanVar()
        force_rescan_check = ttk.Checkbutton(
            options_frame,
            text="强制重新扫描（忽略缓存）",
            variable=self.force_rescan_var
        )
        force_rescan_check.grid(row=0, column=0, sticky=tk.W)

    def create_results_area(self, parent):
        """创建扫描结果区域"""
        results_frame = ttk.LabelFrame(parent, text="扫描结果", padding="10")
        results_frame.grid(row=2, column=0, columnspan=3, sticky=(tk.W, tk.E, tk.N, tk.S))
        results_frame.columnconfigure(0, weight=1)
        results_frame.rowconfigure(0, weight=1)

        # 创建Treeview
        columns = ('番号', '文件数', '路径', '大小')
        self.scan_tree = ttk.Treeview(results_frame, columns=columns, show='tree headings')

        # 设置列
        self.scan_tree.heading('#0', text='')
        self.scan_tree.column('#0', width=0, stretch=tk.NO)

        for col in columns:
            self.scan_tree.heading(col, text=col)
            self.scan_tree.column(col, width=100)

        self.scan_tree.column('路径', width=300, stretch=tk.YES)

        # 添加滚动条
        tree_scroll = ttk.Scrollbar(
            results_frame,
            orient=tk.VERTICAL,
            command=self.scan_tree.yview
        )
        self.scan_tree.configure(yscrollcommand=tree_scroll.set)

        # 布局
        self.scan_tree.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        tree_scroll.grid(row=0, column=1, sticky=(tk.N, tk.S))

        # 绑定双击事件
        self.scan_tree.bind('<Double-1>', self.on_item_double_click)

    def create_menu(self):
        """创建菜单栏"""
        menubar = tk.Menu(self.window)
        self.window.config(menu=menubar)

        # 文件菜单
        file_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="文件", menu=file_menu)
        file_menu.add_command(label="选择文件夹...", command=self.browse_folder)
        file_menu.add_separator()
        file_menu.add_command(label="退出", command=self.app.on_closing)

        # 扫描菜单
        scan_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="扫描", menu=scan_menu)
        scan_menu.add_command(label="开始扫描", command=self.start_scan)
        scan_menu.add_command(label="停止扫描", command=self.stop_scan)
        scan_menu.add_separator()
        scan_menu.add_command(label="清空缓存", command=self.app.clear_cache)

        # 工具菜单
        tools_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="工具", menu=tools_menu)
        tools_menu.add_command(label="配置设置", command=self.app.open_config_editor)
        tools_menu.add_command(label="文件扫描器", command=self.app.open_file_scanner)

        # 帮助菜单
        help_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="帮助", menu=help_menu)
        help_menu.add_command(label="关于", command=self.show_about)

    def create_status_bar(self):
        """创建状态栏"""
        status_frame = ttk.Frame(self.window)
        status_frame.grid(row=1, column=0, sticky=(tk.W, tk.E), padx=10, pady=(0, 10))
        status_frame.columnconfigure(1, weight=1)

        # 状态标签
        self.status_label = ttk.Label(status_frame, text="就绪")
        self.status_label.grid(row=0, column=0, sticky=tk.W)

        # 进度条
        self.progress_bar = ttk.Progressbar(
            status_frame,
            mode='indeterminate',
            length=200
        )
        self.progress_bar.grid(row=0, column=1, sticky=tk.E, padx=(10, 0))

    def browse_folder(self):
        """浏览选择文件夹"""
        folder = filedialog.askdirectory(title="选择要扫描的文件夹")
        if folder:
            self.folder_var.set(folder)

    def start_scan(self):
        """开始扫描"""
        folder = self.folder_var.get().strip()
        if not folder:
            messagebox.showwarning("警告", "请选择要扫描的文件夹")
            return

        if not Path(folder).exists():
            messagebox.showerror("错误", "选择的文件夹不存在")
            return

        force_rescan = self.force_rescan_var.get()
        self.app.start_scan(folder, force_rescan)

    def stop_scan(self):
        """停止扫描"""
        # 这里可以添加停止扫描的逻辑
        messagebox.showinfo("提示", "停止扫描功能待实现")

    def set_scanning_state(self, is_scanning: bool):
        """设置扫描状态"""
        if is_scanning:
            self.scan_button.config(state=tk.DISABLED)
            self.stop_button.config(state=tk.NORMAL)
            self.status_label.config(text="正在扫描...")
            self.progress_bar.start(10)
        else:
            self.scan_button.config(state=tk.NORMAL)
            self.stop_button.config(state=tk.DISABLED)
            self.status_label.config(text="就绪")
            self.progress_bar.stop()

    def update_scan_results(self, movies: List[Movie]):
        """更新扫描结果"""
        try:
            # 清空现有结果
            for item in self.scan_tree.get_children():
                self.scan_tree.delete(item)

            # 添加新结果
            for movie in movies:
                movie_id = movie.dvdid if hasattr(movie, 'dvdid') and movie.dvdid else movie.cid
                file_count = len(movie.files) if movie.files else 0

                # 获取第一个文件的路径作为示例
                example_path = ""
                if movie.files:
                    example_path = str(Path(movie.files[0]).parent)

                # 计算总大小
                total_size = 0
                if movie.files:
                    try:
                        for file_path in movie.files:
                            if Path(file_path).exists():
                                total_size += Path(file_path).stat().st_size
                    except Exception:
                        total_size = 0

                size_str = self.format_size(total_size)

                # 添加到树形控件
                self.scan_tree.insert(
                    '',
                    'end',
                    values=(movie_id, file_count, example_path, size_str)
                )

            self.scan_results = movies

            # 更新状态
            self.status_label.config(text=f"扫描完成，发现 {len(movies)} 部影片")

        except Exception as e:
            logger.error(f"更新扫描结果失败: {e}")
            messagebox.showerror("错误", f"更新扫描结果失败: {e}")

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

    def on_item_double_click(self, event):
        """处理结果项双击事件"""
        selection = self.scan_tree.selection()
        if selection:
            item = self.scan_tree.item(selection[0])
            values = item['values']
            if values:
                movie_id = values[0]
                messagebox.showinfo("影片信息", f"番号: {movie_id}\n功能待完善")

    def show_about(self):
        """显示关于对话框"""
        about_text = """JavSP - AV元数据刮削器
版本: 2.8.0

汇总多站点数据的AV元数据刮削器
自动抓取并汇总多个站点数据
生成NFO文件供媒体服务器使用

项目地址: https://github.com/Yuukiy/JavSP
许可: GPL-3.0 License"""

        messagebox.showinfo("关于 JavSP", about_text)