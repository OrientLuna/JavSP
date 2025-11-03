"""
配置编辑器
提供图形化的配置编辑功能
"""

import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import logging
from pathlib import Path
import json

from ..config import Cfg, FileMoveMode, OperationMode

logger = logging.getLogger(__name__)


class ConfigEditor:
    """配置编辑器窗口"""

    def __init__(self, parent, app):
        """
        初始化配置编辑器

        Args:
            parent: 父窗口
            app: JavSPApp实例
        """
        self.app = app
        self.window = tk.Toplevel(parent)
        self.window.title("配置设置")
        self.window.geometry("800x600")
        self.window.transient(parent)
        self.window.grab_set()

        # 配置数据
        self.config_data = {}
        self.config_widgets = {}

        # 创建界面
        self.create_widgets()
        self.load_config()

        # 居中显示
        self.center_window()

        logger.info("配置编辑器已打开")

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

        # 创建notebook用于分组配置
        notebook = ttk.Notebook(main_frame)
        notebook.pack(fill=tk.BOTH, expand=True)

        # 创建各个配置页面
        self.create_scanner_tab(notebook)
        self.create_network_tab(notebook)
        self.create_summarizer_tab(notebook)
        self.create_general_tab(notebook)

        # 按钮区域
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X, pady=(10, 0))

        ttk.Button(button_frame, text="保存", command=self.save_config).pack(side=tk.RIGHT, padx=(5, 0))
        ttk.Button(button_frame, text="重置", command=self.reset_config).pack(side=tk.RIGHT, padx=(5, 0))
        ttk.Button(button_frame, text="导入", command=self.import_config).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(button_frame, text="导出", command=self.export_config).pack(side=tk.LEFT, padx=(0, 5))

    def create_scanner_tab(self, notebook):
        """创建扫描器配置页面"""
        frame = ttk.Frame(notebook, padding="10")
        notebook.add(frame, text="扫描器")

        # 文件夹设置
        folder_frame = ttk.LabelFrame(frame, text="文件夹设置", padding="10")
        folder_frame.pack(fill=tk.X, pady=(0, 10))

        self.config_widgets['input_directory'] = self.create_file_entry(
            folder_frame, "扫描目录:", 0, is_directory=True
        )

        # 文件设置
        file_frame = ttk.LabelFrame(frame, text="文件设置", padding="10")
        file_frame.pack(fill=tk.X, pady=(0, 10))

        self.config_widgets['filename_extensions'] = self.create_text_entry(
            file_frame, "支持的视频格式:", 0,
            ".mp4,.avi,.mkv,.mov,.wmv,.flv,.m4v,.3gp,.rmvb,.rm,.ts,.vob,.iso,.m2ts"
        )

        self.config_widgets['minimum_size'] = self.create_text_entry(
            file_frame, "最小文件大小:", 1, "50MiB"
        )

        # 扫描选项
        options_frame = ttk.LabelFrame(frame, text="扫描选项", padding="10")
        options_frame.pack(fill=tk.X)

        self.config_widgets['skip_nfo_dir'] = self.create_checkbutton(
            options_frame, "跳过包含NFO文件的文件夹", 0
        )

        self.config_widgets['manual'] = self.create_checkbutton(
            options_frame, "手动确认番号", 1
        )

    def create_network_tab(self, notebook):
        """创建网络配置页面"""
        frame = ttk.Frame(notebook, padding="10")
        notebook.add(frame, text="网络")

        # 代理设置
        proxy_frame = ttk.LabelFrame(frame, text="代理设置", padding="10")
        proxy_frame.pack(fill=tk.X, pady=(0, 10))

        self.config_widgets['proxy_server'] = self.create_text_entry(
            proxy_frame, "代理服务器:", 0, "http://127.0.0.1:1080"
        )

        # 超时设置
        timeout_frame = ttk.LabelFrame(frame, text="超时设置", padding="10")
        timeout_frame.pack(fill=tk.X)

        self.config_widgets['timeout'] = self.create_text_entry(
            timeout_frame, "请求超时:", 0, "PT30S"
        )

        self.config_widgets['retry'] = self.create_text_entry(
            timeout_frame, "重试次数:", 1, "3"
        )

    def create_summarizer_tab(self, notebook):
        """创建整理器配置页面"""
        frame = ttk.Frame(notebook, padding="10")
        notebook.add(frame, text="整理器")

        # 运行模式
        mode_frame = ttk.LabelFrame(frame, text="运行模式", padding="10")
        mode_frame.pack(fill=tk.X, pady=(0, 10))

        self.config_widgets['operation_mode'] = self.create_combobox(
            mode_frame, "运行模式:", 0,
            ["scrape_and_organize", "scrape_only", "organize_only"],
            "scrape_and_organize"
        )

        # 文件操作
        file_frame = ttk.LabelFrame(frame, text="文件操作", padding="10")
        file_frame.pack(fill=tk.X, pady=(0, 10))

        self.config_widgets['move_files'] = self.create_checkbutton(
            file_frame, "移动文件", 0
        )

        self.config_widgets['move_mode'] = self.create_combobox(
            file_frame, "移动模式:", 1,
            ["move", "hard_link", "soft_link"],
            "move"
        )

        self.config_widgets['use_absolute_paths'] = self.create_checkbutton(
            file_frame, "使用绝对路径", 2
        )

        # 路径设置
        path_frame = ttk.LabelFrame(frame, text="路径设置", padding="10")
        path_frame.pack(fill=tk.X)

        self.config_widgets['output_dir'] = self.create_file_entry(
            path_frame, "输出目录:", 0, is_directory=True
        )

    def create_general_tab(self, notebook):
        """创建通用配置页面"""
        frame = ttk.Frame(notebook, padding="10")
        notebook.add(frame, text="通用")

        # 缓存设置
        cache_frame = ttk.LabelFrame(frame, text="缓存设置", padding="10")
        cache_frame.pack(fill=tk.X, pady=(0, 10))

        self.config_widgets['enable_incremental_scan'] = self.create_checkbutton(
            cache_frame, "启用增量扫描", 0
        )

        self.config_widgets['cache_file'] = self.create_file_entry(
            cache_frame, "缓存文件:", 1, is_directory=False
        )

        self.config_widgets['cache_cleanup_interval'] = self.create_text_entry(
            cache_frame, "缓存清理间隔(天):", 2, "30"
        )

        # 应用设置
        app_frame = ttk.LabelFrame(frame, text="应用设置", padding="10")
        app_frame.pack(fill=tk.X)

        self.config_widgets['interactive'] = self.create_checkbutton(
            app_frame, "交互模式", 0
        )

        self.config_widgets['check_update'] = self.create_checkbutton(
            app_frame, "检查更新", 1
        )

        self.config_widgets['auto_update'] = self.create_checkbutton(
            app_frame, "自动更新", 2
        )

    def create_text_entry(self, parent, label_text: str, row: int, default_value: str = ""):
        """创建文本输入框"""
        ttk.Label(parent, text=label_text).grid(row=row, column=0, sticky=tk.W, padx=(0, 10), pady=2)

        var = tk.StringVar(value=default_value)
        entry = ttk.Entry(parent, textvariable=var, width=50)
        entry.grid(row=row, column=1, sticky=(tk.W, tk.E), pady=2)

        parent.columnconfigure(1, weight=1)
        return var

    def create_file_entry(self, parent, label_text: str, row: int, is_directory: bool = False):
        """创建文件/目录选择框"""
        ttk.Label(parent, text=label_text).grid(row=row, column=0, sticky=tk.W, padx=(0, 10), pady=2)

        var = tk.StringVar()
        entry = ttk.Entry(parent, textvariable=var, width=40)
        entry.grid(row=row, column=1, sticky=(tk.W, tk.E), padx=(0, 10), pady=2)

        button = ttk.Button(parent, text="浏览...", width=8,
                          command=lambda: self.browse_file(var, is_directory))
        button.grid(row=row, column=2, pady=2)

        parent.columnconfigure(1, weight=1)
        return var

    def create_checkbutton(self, parent, label_text: str, row: int):
        """创建复选框"""
        var = tk.BooleanVar()
        check = ttk.Checkbutton(parent, text=label_text, variable=var)
        check.grid(row=row, column=0, columnspan=2, sticky=tk.W, pady=2)
        return var

    def create_combobox(self, parent, label_text: str, row: int, values: list, default_value: str):
        """创建下拉框"""
        ttk.Label(parent, text=label_text).grid(row=row, column=0, sticky=tk.W, padx=(0, 10), pady=2)

        var = tk.StringVar(value=default_value)
        combo = ttk.Combobox(parent, textvariable=var, values=values, state="readonly")
        combo.grid(row=row, column=1, sticky=(tk.W, tk.E), pady=2)

        parent.columnconfigure(1, weight=1)
        return var

    def browse_file(self, var: tk.StringVar, is_directory: bool):
        """浏览文件/目录"""
        if is_directory:
            path = filedialog.askdirectory(title="选择目录")
        else:
            path = filedialog.askopenfilename(title="选择文件")

        if path:
            var.set(path)

    def load_config(self):
        """加载配置到界面"""
        try:
            config = self.app.current_config
            if not config:
                config = Cfg()

            # 加载配置值到界面元素
            # 扫描器配置
            if hasattr(config.scanner, 'input_directory') and config.scanner.input_directory:
                self.config_widgets['input_directory'].set(str(config.scanner.input_directory))

            if hasattr(config.scanner, 'filename_extensions'):
                extensions = ','.join(config.scanner.filename_extensions)
                self.config_widgets['filename_extensions'].set(extensions)

            if hasattr(config.scanner, 'minimum_size'):
                self.config_widgets['minimum_size'].set(str(config.scanner.minimum_size))

            self.config_widgets['skip_nfo_dir'].set(config.scanner.skip_nfo_dir)
            self.config_widgets['manual'].set(config.scanner.manual)

            # 网络配置
            if hasattr(config.network, 'proxy_server') and config.network.proxy_server:
                self.config_widgets['proxy_server'].set(str(config.network.proxy_server))

            if hasattr(config.network, 'timeout'):
                self.config_widgets['timeout'].set(str(config.network.timeout))

            self.config_widgets['retry'].set(str(config.network.retry))

            # 整理器配置
            self.config_widgets['operation_mode'].set(config.summarizer.operation_mode.value)
            self.config_widgets['move_files'].set(config.summarizer.move_files)
            self.config_widgets['move_mode'].set(config.summarizer.path.move_mode.value)
            self.config_widgets['use_absolute_paths'].set(config.summarizer.path.use_absolute_paths)

            # 通用配置
            self.config_widgets['enable_incremental_scan'].set(config.general.enable_incremental_scan)
            self.config_widgets['cache_file'].set(config.general.cache_file)
            self.config_widgets['cache_cleanup_interval'].set(str(config.general.cache_cleanup_interval))
            self.config_widgets['interactive'].set(config.other.interactive)
            self.config_widgets['check_update'].set(config.other.check_update)
            self.config_widgets['auto_update'].set(config.other.auto_update)

            logger.info("配置加载完成")

        except Exception as e:
            logger.error(f"加载配置失败: {e}")
            messagebox.showerror("错误", f"加载配置失败: {e}")

    def save_config(self):
        """保存配置"""
        try:
            # 这里应该将界面数据保存到配置文件
            # 由于配置系统比较复杂，这里简化处理
            messagebox.showinfo("提示", "配置保存功能待完善")
            logger.info("用户尝试保存配置")

        except Exception as e:
            logger.error(f"保存配置失败: {e}")
            messagebox.showerror("错误", f"保存配置失败: {e}")

    def reset_config(self):
        """重置配置"""
        result = messagebox.askyesno("确认", "确定要重置所有配置为默认值吗？")
        if result:
            messagebox.showinfo("提示", "配置重置功能待完善")

    def import_config(self):
        """导入配置"""
        file_path = filedialog.askopenfilename(
            title="导入配置文件",
            filetypes=[("YAML文件", "*.yml *.yaml"), ("所有文件", "*.*")]
        )
        if file_path:
            messagebox.showinfo("提示", "配置导入功能待完善")

    def export_config(self):
        """导出配置"""
        file_path = filedialog.asksaveasfilename(
            title="导出配置文件",
            defaultextension=".yml",
            filetypes=[("YAML文件", "*.yml *.yaml"), ("所有文件", "*.*")]
        )
        if file_path:
            messagebox.showinfo("提示", "配置导出功能待完善")

    def show(self):
        """显示窗口"""
        self.window.deiconify()
        self.window.lift()

    def destroy(self):
        """销毁窗口"""
        self.window.destroy()