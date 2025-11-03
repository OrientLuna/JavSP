"""
JavSP GUI主应用程序
基于tkinter的轻量级图形界面
"""

import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import logging
import sys
import os
from pathlib import Path
from typing import Optional

from ..config import Cfg
from ..scan_cache import get_cache, save_cache
from .main_window import MainWindow
from .config_editor import ConfigEditor
from .file_scanner import FileScanner

logger = logging.getLogger(__name__)


class JavSPApp:
    """JavSP GUI应用程序主类"""

    def __init__(self):
        """初始化应用程序"""
        self.root: Optional[tk.Tk] = None
        self.main_window: Optional[MainWindow] = None
        self.config_editor: Optional[ConfigEditor] = None
        self.file_scanner: Optional[FileScanner] = None

        # 当前状态
        self.current_config = None
        self.scan_results = []
        self.is_scanning = False

        logger.info("JavSP GUI应用程序初始化")

    def create_gui(self):
        """创建图形用户界面"""
        try:
            # 创建主窗口
            self.root = tk.Tk()
            self.root.title("JavSP - AV元数据刮削器")
            self.root.geometry("1000x700")
            self.root.minsize(800, 600)

            # 设置图标（如果存在）
            icon_path = Path(__file__).parent.parent.parent / "image" / "JavSP.ico"
            if icon_path.exists():
                try:
                    self.root.iconbitmap(str(icon_path))
                except Exception as e:
                    logger.warning(f"无法设置图标: {e}")

            # 创建样式
            self.setup_styles()

            # 创建主界面
            self.main_window = MainWindow(self.root, self)

            # 绑定关闭事件
            self.root.protocol("WM_DELETE_WINDOW", self.on_closing)

            logger.info("GUI界面创建完成")

        except Exception as e:
            logger.error(f"创建GUI失败: {e}")
            messagebox.showerror("错误", f"创建GUI失败: {e}")
            sys.exit(1)

    def setup_styles(self):
        """设置界面样式"""
        try:
            style = ttk.Style()

            # 设置主题
            available_themes = style.theme_names()
            if 'clam' in available_themes:
                style.theme_use('clam')
            elif 'alt' in available_themes:
                style.theme_use('alt')

            # 自定义样式
            style.configure('Title.TLabel', font=('Arial', 12, 'bold'))
            style.configure('Heading.TLabel', font=('Arial', 10, 'bold'))
            style.configure('Success.TLabel', foreground='green')
            style.configure('Error.TLabel', foreground='red')
            style.configure('Warning.TLabel', foreground='orange')

        except Exception as e:
            logger.warning(f"设置样式失败: {e}")

    def load_config(self):
        """加载配置"""
        try:
            self.current_config = Cfg()
            logger.info("配置加载成功")
            return True
        except Exception as e:
            logger.error(f"加载配置失败: {e}")
            messagebox.showerror("错误", f"加载配置失败: {e}")
            return False

    def save_config(self):
        """保存配置"""
        try:
            if self.current_config:
                # 配置会自动保存到文件
                logger.info("配置保存成功")
                return True
            return False
        except Exception as e:
            logger.error(f"保存配置失败: {e}")
            messagebox.showerror("错误", f"保存配置失败: {e}")
            return False

    def open_config_editor(self):
        """打开配置编辑器"""
        try:
            if not self.config_editor or not self.config_editor.window.winfo_exists():
                self.config_editor = ConfigEditor(self.root, self)

            self.config_editor.show()

        except Exception as e:
            logger.error(f"打开配置编辑器失败: {e}")
            messagebox.showerror("错误", f"打开配置编辑器失败: {e}")

    def open_file_scanner(self):
        """打开文件扫描器"""
        try:
            if not self.file_scanner or not self.file_scanner.window.winfo_exists():
                self.file_scanner = FileScanner(self.root, self)

            self.file_scanner.show()

        except Exception as e:
            logger.error(f"打开文件扫描器失败: {e}")
            messagebox.showerror("错误", f"打开文件扫描器失败: {e}")

    def start_scan(self, scan_path: str, force_rescan: bool = False):
        """开始扫描"""
        if self.is_scanning:
            messagebox.showwarning("警告", "正在扫描中，请等待完成")
            return

        try:
            self.is_scanning = True

            # 更新GUI状态
            if self.main_window:
                self.main_window.set_scanning_state(True)

            # 执行扫描
            logger.info(f"开始扫描: {scan_path}")

            # 在后台线程中执行扫描
            import threading
            scan_thread = threading.Thread(
                target=self._perform_scan,
                args=(scan_path, force_rescan),
                daemon=True
            )
            scan_thread.start()

        except Exception as e:
            self.is_scanning = False
            if self.main_window:
                self.main_window.set_scanning_state(False)
            logger.error(f"启动扫描失败: {e}")
            messagebox.showerror("错误", f"启动扫描失败: {e}")

    def _perform_scan(self, scan_path: str, force_rescan: bool):
        """在后台执行扫描"""
        try:
            # 导入扫描功能
            from ..file import scan_movies

            # 执行扫描
            movies = scan_movies(scan_path, force_rescan)

            # 更新结果
            self.scan_results = movies

            # 在主线程中更新GUI
            self.root.after(0, self._scan_completed, movies)

        except Exception as e:
            logger.error(f"扫描失败: {e}")
            self.root.after(0, self._scan_failed, str(e))

    def _scan_completed(self, movies):
        """扫描完成回调"""
        try:
            self.is_scanning = False

            if self.main_window:
                self.main_window.set_scanning_state(False)
                self.main_window.update_scan_results(movies)

            # 保存缓存
            if Cfg().general.enable_incremental_scan:
                try:
                    save_cache()
                except Exception as e:
                    logger.warning(f"保存缓存失败: {e}")

            messagebox.showinfo("完成", f"扫描完成！发现 {len(movies)} 部影片")

        except Exception as e:
            logger.error(f"更新扫描结果失败: {e}")

    def _scan_failed(self, error_msg: str):
        """扫描失败回调"""
        try:
            self.is_scanning = False

            if self.main_window:
                self.main_window.set_scanning_state(False)

            messagebox.showerror("扫描失败", f"扫描失败: {error_msg}")

        except Exception as e:
            logger.error(f"处理扫描失败回调错误: {e}")

    def clear_cache(self):
        """清空缓存"""
        try:
            result = messagebox.askyesno("确认", "确定要清空扫描缓存吗？")
            if result:
                cache = get_cache()
                cache.clear_cache()
                messagebox.showinfo("成功", "缓存已清空")
                logger.info("用户清空了扫描缓存")
        except Exception as e:
            logger.error(f"清空缓存失败: {e}")
            messagebox.showerror("错误", f"清空缓存失败: {e}")

    def get_cache_stats(self) -> dict:
        """获取缓存统计信息"""
        try:
            cache = get_cache()
            return cache.get_cache_stats()
        except Exception as e:
            logger.error(f"获取缓存统计失败: {e}")
            return {}

    def on_closing(self):
        """关闭应用程序"""
        try:
            # 保存缓存
            if Cfg().general.enable_incremental_scan:
                try:
                    save_cache()
                except Exception as e:
                    logger.warning(f"保存缓存失败: {e}")

            # 关闭子窗口
            if self.config_editor and self.config_editor.window.winfo_exists():
                self.config_editor.window.destroy()

            if self.file_scanner and self.file_scanner.window.winfo_exists():
                self.file_scanner.window.destroy()

            # 关闭主窗口
            if self.root:
                self.root.destroy()

            logger.info("应用程序正常关闭")

        except Exception as e:
            logger.error(f"关闭应用程序时出错: {e}")

    def run(self):
        """运行应用程序"""
        try:
            # 加载配置
            if not self.load_config():
                return

            # 创建GUI
            self.create_gui()

            # 运行主循环
            self.root.mainloop()

        except Exception as e:
            logger.error(f"运行应用程序失败: {e}")
            messagebox.showerror("错误", f"运行应用程序失败: {e}")
            sys.exit(1)


def main():
    """GUI应用程序入口点"""
    # 设置日志
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    try:
        app = JavSPApp()
        app.run()
    except Exception as e:
        logger.error(f"启动GUI应用程序失败: {e}")
        messagebox.showerror("错误", f"启动应用程序失败: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()