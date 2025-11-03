"""
扫描相关API接口
"""

import logging
import threading
from flask import Blueprint, request, jsonify
from pathlib import Path

from ...config import Cfg
from ...scan_cache import get_cache, save_cache
from ...datatype import Movie

logger = logging.getLogger(__name__)

# 创建蓝图
scan_bp = Blueprint('scan', __name__)

# 全局扫描状态
_is_scanning = False
_scan_thread = None
_scan_results = []


@scan_bp.route('/start', methods=['POST'])
def api_scan_start():
    """开始扫描"""
    try:
        data = request.get_json()
        if not data:
            logger.error(f"扫描启动失败: 未提供请求数据")
            return jsonify({'error': '请提供请求数据'}), 400

        scan_path = data.get('path')
        force_rescan = data.get('force_rescan', False)

        logger.info(f"收到扫描请求: path='{scan_path}', force_rescan={force_rescan}")

        if not scan_path:
            logger.error(f"扫描启动失败: 未提供扫描路径")
            return jsonify({'error': '请提供扫描路径'}), 400

        # 检查路径是否存在
        if not Path(scan_path).exists():
            logger.error(f"扫描启动失败: 路径不存在: {scan_path}")
            return jsonify({'error': f'路径不存在: {scan_path}'}), 400

        if _is_scanning:
            logger.warning(f"扫描启动失败: 正在扫描中")
            return jsonify({'error': '正在扫描中，请等待完成'}), 409

        logger.info(f"开始后台扫描: {scan_path}, force_rescan={force_rescan}")

        # 启动扫描
        success = _start_background_scan(scan_path, force_rescan)

        if success:
            logger.info(f"扫描启动成功: {scan_path}")
            return jsonify({
                'message': '扫描已开始',
                'path': scan_path,
                'force_rescan': force_rescan
            })
        else:
            logger.error(f"扫描启动失败: 未知错误")
            return jsonify({'error': '启动扫描失败'}), 500

    except Exception as e:
        logger.error(f"启动扫描API错误: {e}")
        return jsonify({'error': f'启动扫描失败: {str(e)}'}), 500


@scan_bp.route('/stop', methods=['POST'])
def api_scan_stop():
    """停止扫描"""
    try:
        if not is_scanning:
            return jsonify({'error': '当前没有扫描任务'}), 400

        success = _stop_scan()

        if success:
            return jsonify({'message': '扫描已停止'})
        else:
            return jsonify({'error': '停止扫描失败'}), 500

    except Exception as e:
        logger.error(f"停止扫描API错误: {e}")
        return jsonify({'error': f'停止扫描失败: {str(e)}'}), 500


@scan_bp.route('/status', methods=['GET'])
def api_scan_status():
    """获取扫描状态"""
    try:
        return jsonify({
            'is_scanning': _is_scanning,
            'results_count': len(_scan_results),
            'config': {
                'enable_incremental_scan': Cfg().general.enable_incremental_scan,
                'cache_file': Cfg().general.cache_file
            }
        })

    except Exception as e:
        logger.error(f"获取扫描状态API错误: {e}")
        return jsonify({'error': f'获取状态失败: {str(e)}'}), 500


@scan_bp.route('/results', methods=['GET'])
def api_scan_results():
    """获取扫描结果"""
    try:
        # 获取查询参数
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 50, type=int)
        search = request.args.get('search', '').strip()

        results = _get_scan_results()

        # 搜索过滤
        if search:
            results = [r for r in results if search.lower() in r['id'].lower()]

        # 分页
        total = len(results)
        start = (page - 1) * per_page
        end = start + per_page
        paginated_results = results[start:end]

        return jsonify({
            'results': paginated_results,
            'pagination': {
                'page': page,
                'per_page': per_page,
                'total': total,
                'pages': (total + per_page - 1) // per_page
            }
        })

    except Exception as e:
        logger.error(f"获取扫描结果API错误: {e}")
        return jsonify({'error': f'获取结果失败: {str(e)}'}), 500


@scan_bp.route('/preview', methods=['POST'])
def api_scan_preview():
    """预览扫描结果（不实际执行扫描）"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': '请提供请求数据'}), 400

        scan_path = data.get('path')
        if not scan_path:
            return jsonify({'error': '请提供扫描路径'}), 400

        # 检查路径是否存在
        if not Path(scan_path).exists():
            return jsonify({'error': f'路径不存在: {scan_path}'}), 400

        # 这里可以实现预览逻辑，比如快速扫描文件数量等
        # 为了演示，返回基本信息
        try:
            import os
            video_extensions = {'.mp4', '.avi', '.mkv', '.mov', '.wmv', '.flv', '.m4v', '.3gp', '.rmvb', '.rm', '.ts', '.vob', '.iso', '.m2ts', '.strm', '.mpg'}
            file_count = 0
            total_size = 0

            for root, dirs, files in os.walk(scan_path):
                for file in files:
                    if any(file.lower().endswith(ext) for ext in video_extensions):
                        file_path = os.path.join(root, file)
                        try:
                            file_size = os.path.getsize(file_path)
                            total_size += file_size
                            file_count += 1
                        except OSError:
                            continue

            return jsonify({
                'path': scan_path,
                'estimated_files': file_count,
                'estimated_size': total_size,
                'estimated_size_str': _format_size(total_size),
                'message': f'预计发现 {file_count} 个视频文件'
            })

        except Exception as e:
            logger.error(f"预览扫描失败: {e}")
            return jsonify({'error': f'预览失败: {str(e)}'}), 500

    except Exception as e:
        logger.error(f"预览扫描API错误: {e}")
        return jsonify({'error': f'预览失败: {str(e)}'}), 500


def _format_size(size_bytes: int) -> str:
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


# 扫描功能实现
def _start_background_scan(scan_path: str, force_rescan: bool = False):
    """后台扫描函数"""
    global _is_scanning, _scan_thread, _scan_results

    if _is_scanning:
        return False

    try:
        _is_scanning = True

        # 在后台线程中执行扫描
        _scan_thread = threading.Thread(
            target=_perform_scan,
            args=(scan_path, force_rescan),
            daemon=True
        )
        _scan_thread.start()

        return True

    except Exception as e:
        logger.error(f"启动扫描失败: {e}")
        _is_scanning = False
        return False


def _perform_scan(scan_path: str, force_rescan: bool):
    """执行扫描"""
    global _is_scanning, _scan_results

    try:
        from ...file import scan_movies

        logger.info(f"开始扫描: {scan_path}, force_rescan={force_rescan}")

        # 执行扫描
        movies = scan_movies(scan_path, force_rescan)

        # 更新结果
        _scan_results = movies

        # 保存缓存
        if Cfg().general.enable_incremental_scan:
            try:
                save_cache()
                logger.info("缓存已保存")
            except Exception as e:
                logger.warning(f"保存缓存失败: {e}")

        logger.info(f"扫描完成: 发现 {len(movies)} 部影片")

    except Exception as e:
        logger.error(f"扫描失败: {e}")

    finally:
        _is_scanning = False


def _stop_scan():
    """停止扫描"""
    global _is_scanning
    _is_scanning = False
    return True


def _get_scan_results() -> list:
    """获取扫描结果"""
    results = []
    for movie in _scan_results:
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
            'size_str': _format_size(total_size)
        })

    return results


def is_scanning():
    """检查是否正在扫描"""
    return _is_scanning


def get_scan_results():
    """获取扫描结果"""
    return _get_scan_results()