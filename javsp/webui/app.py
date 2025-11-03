"""
JavSP WebUI主应用程序
基于Flask的Web管理界面
"""

import logging
from flask import Flask, render_template, jsonify, request
from flask_cors import CORS
from flask_socketio import SocketIO, emit
import threading
import time
from pathlib import Path
from typing import Dict, List, Optional

from ..config import Cfg
from ..scan_cache import get_cache, save_cache
from ..datatype import Movie
from .api.scan_api import scan_bp
from .api.config_api import config_bp
from .api.cache_api import cache_bp
from .api.files_api import files_bp

logger = logging.getLogger(__name__)

# 全局变量
app: Optional[Flask] = None
socketio: Optional[SocketIO] = None
scan_thread: Optional[threading.Thread] = None
scan_results: List[Movie] = []
is_scanning = False


def create_app() -> Flask:
    """创建Flask应用"""
    global app, socketio

    app = Flask(__name__,
                 template_folder='templates',
                 static_folder='static')

    # 配置
    app.config['SECRET_KEY'] = 'javsp-webui-secret-key'
    app.config['JSON_AS_ASCII'] = False  # 支持中文JSON

    # 启用CORS
    CORS(app)

    # 初始化SocketIO
    socketio = SocketIO(app, cors_allowed_origins="*")

    # 注册蓝图
    app.register_blueprint(scan_bp, url_prefix='/api/scan')
    app.register_blueprint(config_bp, url_prefix='/api/config')
    app.register_blueprint(cache_bp, url_prefix='/api/cache')
    app.register_blueprint(files_bp, url_prefix='/api/files')

    # 注册路由
    register_routes()
    register_socketio_events()

    logger.info("WebUI应用创建完成")
    return app


def register_routes():
    """注册路由"""

    @app.route('/')
    def index():
        """主页"""
        return render_template('index.html')

    @app.route('/api/status')
    def api_status():
        """系统状态API"""
        try:
            cfg = Cfg()
            cache = get_cache()
            stats = cache.get_cache_stats()

            return jsonify({
                'status': 'running',
                'version': getattr(__import__('sys'), 'javsp_version', '未知版本'),
                'config': {
                    'enable_incremental_scan': cfg.general.enable_incremental_scan,
                    'cache_file': cfg.general.cache_file,
                    'webui_port': cfg.general.webui_port
                },
                'cache_stats': stats,
                'is_scanning': is_scanning,
                'scan_results_count': len(scan_results)
            })
        except Exception as e:
            logger.error(f"获取系统状态失败: {e}")
            return jsonify({'error': str(e)}), 500

    @app.route('/api/system/info')
    def api_system_info():
        """系统信息API"""
        try:
            import platform
            import psutil

            return jsonify({
                'platform': platform.platform(),
                'python_version': platform.python_version(),
                'cpu_count': psutil.cpu_count(),
                'memory_total': psutil.virtual_memory().total,
                'disk_free': psutil.disk_usage('.').free,
                'timestamp': time.time()
            })
        except ImportError:
            # 如果没有psutil，返回基本信息
            return jsonify({
                'platform': platform.platform(),
                'python_version': platform.python_version(),
                'timestamp': time.time()
            })
        except Exception as e:
            logger.error(f"获取系统信息失败: {e}")
            return jsonify({'error': str(e)}), 500


def register_socketio_events():
    """注册SocketIO事件"""

    @socketio.on('connect')
    def handle_connect():
        """客户端连接"""
        logger.info("WebUI客户端已连接")
        emit('status', {'message': '已连接到JavSP WebUI'})

    @socketio.on('disconnect')
    def handle_disconnect():
        """客户端断开连接"""
        logger.info("WebUI客户端已断开连接")

    @socketio.on('scan_progress')
    def handle_scan_progress(data):
        """扫描进度更新"""
        emit('scan_progress', data, broadcast=True)


def emit_scan_progress(progress_data: Dict):
    """发送扫描进度"""
    if socketio:
        socketio.emit('scan_progress', progress_data)


def emit_status_update(status_data: Dict):
    """发送状态更新"""
    if socketio:
        socketio.emit('status_update', status_data)


def emit_log_message(log_data: Dict):
    """发送日志消息"""
    if socketio:
        socketio.emit('log_message', log_data)


# 全局扫描函数，供API模块使用
def start_background_scan(scan_path: str, force_rescan: bool = False):
    """后台扫描函数"""
    global is_scanning, scan_thread, scan_results

    if is_scanning:
        return False

    try:
        is_scanning = True

        # 发送扫描开始状态
        emit_status_update({
            'status': 'scanning',
            'message': f'开始扫描: {scan_path}',
            'timestamp': time.time()
        })

        # 在后台线程中执行扫描
        scan_thread = threading.Thread(
            target=_perform_scan,
            args=(scan_path, force_rescan),
            daemon=True
        )
        scan_thread.start()

        return True

    except Exception as e:
        logger.error(f"启动扫描失败: {e}")
        is_scanning = False
        return False


def _perform_scan(scan_path: str, force_rescan: bool):
    """执行扫描"""
    global is_scanning, scan_results

    try:
        from ..file import scan_movies

        logger.info(f"开始扫描: {scan_path}, force_rescan={force_rescan}")

        # 发送进度更新
        emit_scan_progress({
            'progress': 10,
            'message': '正在初始化扫描...',
            'timestamp': time.time()
        })

        # 执行扫描
        movies = scan_movies(scan_path, force_rescan)

        # 发送进度更新
        emit_scan_progress({
            'progress': 90,
            'message': '正在处理扫描结果...',
            'timestamp': time.time()
        })

        # 更新结果
        scan_results = movies

        # 保存缓存
        if Cfg().general.enable_incremental_scan:
            try:
                save_cache()
                emit_log_message({
                    'level': 'info',
                    'message': '缓存已保存',
                    'timestamp': time.time()
                })
            except Exception as e:
                emit_log_message({
                    'level': 'warning',
                    'message': f'保存缓存失败: {e}',
                    'timestamp': time.time()
                })

        # 发送完成状态
        emit_scan_progress({
            'progress': 100,
            'message': f'扫描完成，发现 {len(movies)} 部影片',
            'timestamp': time.time()
        })

        emit_status_update({
            'status': 'completed',
            'message': f'扫描完成，发现 {len(movies)} 部影片',
            'timestamp': time.time()
        })

        logger.info(f"扫描完成: 发现 {len(movies)} 部影片")

    except Exception as e:
        logger.error(f"扫描失败: {e}")
        emit_scan_progress({
            'progress': 0,
            'message': f'扫描失败: {e}',
            'timestamp': time.time(),
            'error': True
        })

        emit_status_update({
            'status': 'error',
            'message': f'扫描失败: {e}',
            'timestamp': time.time()
        })

    finally:
        is_scanning = False


def stop_scan():
    """停止扫描"""
    global is_scanning
    is_scanning = False

    emit_status_update({
        'status': 'stopped',
        'message': '扫描已停止',
        'timestamp': time.time()
    })

    return True


def get_scan_results() -> List[Dict]:
    """获取扫描结果"""
    results = []
    for movie in scan_results:
        movie_id = movie.dvdid if hasattr(movie, 'dvdid') and movie.dvdid else movie.cid
        file_count = len(movie.files) if movie.files else 0

        # 获取第一个文件的路径
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

        results.append({
            'id': movie_id,
            'file_count': file_count,
            'path': example_path,
            'size': total_size,
            'size_str': format_size(total_size)
        })

    return results


def format_size(size_bytes: int) -> str:
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