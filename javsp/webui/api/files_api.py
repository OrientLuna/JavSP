"""
文件相关API接口
"""

import logging
import os
from flask import Blueprint, request, jsonify
from pathlib import Path

logger = logging.getLogger(__name__)

# 创建蓝图
files_bp = Blueprint('files', __name__)


@files_bp.route('/browse', methods=['GET'])
def api_files_browse():
    """浏览文件目录"""
    try:
        # 获取查询参数
        path = request.args.get('path', '')
        show_hidden = request.args.get('show_hidden', 'false').lower() == 'true'

        # 处理根路径
        if not path:
            # 返回系统根目录列表（Linux/Unix系统）
            roots = []
            if os.name == 'nt':  # Windows
                import string
                for letter in string.ascii_uppercase:
                    if os.path.exists(f"{letter}:\\"):
                        roots.append({
                            'name': f"{letter}:\\",
                            'path': f"{letter}:\\",
                            'type': 'drive'
                        })
            else:  # Unix-like
                roots.append({
                    'name': '/',
                    'path': '/',
                    'type': 'drive'
                })

                # 添加常用目录
                common_dirs = ['/home', '/mnt', '/media', '/tmp']
                for dir_path in common_dirs:
                    if os.path.exists(dir_path):
                        roots.append({
                            'name': os.path.basename(dir_path),
                            'path': dir_path,
                            'type': 'directory'
                        })

            return jsonify({
                'current_path': '',
                'parent_path': None,
                'items': roots,
                'type': 'roots'
            })

        # 检查路径是否存在
        path_obj = Path(path)
        if not path_obj.exists():
            return jsonify({'error': f'路径不存在: {path}'}), 404

        if not path_obj.is_dir():
            return jsonify({'error': f'不是目录: {path}'}), 400

        # 获取父目录
        parent_path = str(path_obj.parent) if path_obj.parent != path_obj.parent else None

        # 读取目录内容
        items = []
        directories = []
        files = []

        try:
            for item in path_obj.iterdir():
                try:
                    # 跳过隐藏文件（除非明确要求显示）
                    if not show_hidden and item.name.startswith('.'):
                        continue

                    item_info = {
                        'name': item.name,
                        'path': str(item),
                        'type': 'directory' if item.is_dir() else 'file',
                        'size': 0,
                        'modified': 0
                    }

                    if item.is_dir():
                        directories.append(item_info)
                    else:
                        try:
                            stat = item.stat()
                            item_info['size'] = stat.st_size
                            item_info['modified'] = stat.st_mtime

                            # 检查是否为视频文件
                            video_extensions = {'.mp4', '.avi', '.mkv', '.mov', '.wmv', '.flv', '.m4v', '.3gp', '.rmvb', '.rm', '.ts', '.vob', '.iso', '.m2ts', '.strm', '.mpg'}
                            if item.suffix.lower() in video_extensions:
                                item_info['is_video'] = True
                            else:
                                item_info['is_video'] = False

                            files.append(item_info)
                        except (OSError, PermissionError):
                            # 跳过无法访问的文件
                            continue

                except (OSError, PermissionError):
                    # 跳过无法访问的项目
                    continue

        except PermissionError:
            return jsonify({'error': f'无权限访问目录: {path}'}), 403

        # 排序：目录在前，文件在后，都按名称排序
        directories.sort(key=lambda x: x['name'].lower())
        files.sort(key=lambda x: x['name'].lower())

        items = directories + files

        return jsonify({
            'current_path': str(path_obj),
            'parent_path': parent_path,
            'items': items,
            'type': 'directory'
        })

    except Exception as e:
        logger.error(f"浏览文件API错误: {e}")
        return jsonify({'error': f'浏览文件失败: {str(e)}'}), 500


@files_bp.route('/select', methods=['POST'])
def api_files_select():
    """选择文件目录"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': '请提供请求数据'}), 400

        path = data.get('path')
        if not path:
            return jsonify({'error': '请提供路径'}), 400

        path_obj = Path(path)
        if not path_obj.exists():
            return jsonify({'error': f'路径不存在: {path}'}), 404

        if not path_obj.is_dir():
            return jsonify({'error': f'不是目录: {path}'}), 400

        # 返回目录信息
        return jsonify({
            'path': str(path_obj),
            'name': path_obj.name,
            'writable': os.access(path_obj, os.W_OK),
            'exists': True
        })

    except Exception as e:
        logger.error(f"选择文件API错误: {e}")
        return jsonify({'error': f'选择文件失败: {str(e)}'}), 500


@files_bp.route('/preview', methods=['POST'])
def api_files_preview():
    """预览目录中的视频文件"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': '请提供请求数据'}), 400

        path = data.get('path')
        if not path:
            return jsonify({'error': '请提供路径'}), 400

        path_obj = Path(path)
        if not path_obj.exists():
            return jsonify({'error': f'路径不存在: {path}'}), 404

        if not path_obj.is_dir():
            return jsonify({'error': f'不是目录: {path}'}), 400

        # 扫描视频文件
        video_extensions = {'.mp4', '.avi', '.mkv', '.mov', '.wmv', '.flv', '.m4v', '.3gp', '.rmvb', '.rm', '.ts', '.vob', '.iso', '.m2ts', '.strm', '.mpg'}
        video_files = []
        total_size = 0

        try:
            for root, dirs, filenames in os.walk(path):
                for filename in filenames:
                    file_path = Path(root) / filename
                    if filename.lower().endswith(tuple(video_extensions)):
                        try:
                            stat = file_path.stat()
                            file_info = {
                                'path': str(file_path),
                                'name': filename,
                                'size': stat.st_size,
                                'size_str': _format_size(stat.st_size),
                                'modified': stat.st_mtime,
                                'relative_path': str(file_path.relative_to(path_obj))
                            }
                            video_files.append(file_info)
                            total_size += stat.st_size
                        except (OSError, PermissionError):
                            continue

        except Exception as e:
            logger.error(f"扫描视频文件失败: {e}")
            return jsonify({'error': f'扫描失败: {str(e)}'}), 500

        return jsonify({
            'path': str(path_obj),
            'video_files': video_files,
            'total_count': len(video_files),
            'total_size': total_size,
            'total_size_str': _format_size(total_size)
        })

    except Exception as e:
        logger.error(f"预览文件API错误: {e}")
        return jsonify({'error': f'预览文件失败: {str(e)}'}), 500


@files_bp.route('/validate', methods=['POST'])
def api_files_validate():
    """验证目录是否适合扫描"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': '请提供请求数据'}), 400

        path = data.get('path')
        if not path:
            return jsonify({'error': '请提供路径'}), 400

        path_obj = Path(path)
        if not path_obj.exists():
            return jsonify({'error': f'路径不存在: {path}'}), 404

        if not path_obj.is_dir():
            return jsonify({'error': f'不是目录: {path}'}), 400

        validation_result = {
            'valid': True,
            'warnings': [],
            'errors': [],
            'recommendations': []
        }

        # 检查权限
        if not os.access(path_obj, os.R_OK):
            validation_result['valid'] = False
            validation_result['errors'].append('无读取权限')

        if not os.access(path_obj, os.W_OK):
            validation_result['warnings'].append('无写入权限，可能无法保存整理后的文件')

        # 检查目录是否为空
        try:
            has_files = False
            has_videos = False
            for item in path_obj.iterdir():
                if item.is_file():
                    has_files = True
                    if item.suffix.lower() in {'.mp4', '.avi', '.mkv', '.mov', '.wmv', '.flv', '.m4v', '.3gp', '.rmvb', '.rm', '.ts', '.vob', '.iso', '.m2ts', '.strm', '.mpg'}:
                        has_videos = True
                        break

            if not has_files:
                validation_result['warnings'].append('目录为空')
            elif not has_videos:
                validation_result['warnings'].append('目录中没有检测到视频文件')

        except PermissionError:
            validation_result['warnings'].append('无法完全检查目录内容（权限问题）')

        # 检查磁盘空间
        try:
            import shutil
            total, used, free = shutil.disk_usage(path)
            free_gb = free // (1024**3)
            if free_gb < 10:  # 少于10GB
                validation_result['warnings'].append(f'磁盘空间较少，剩余 {free_gb} GB')
        except:
            pass

        # 检查是否有子目录
        try:
            subdirs = [d for d in path_obj.iterdir() if d.is_dir()]
            if len(subdirs) > 100:
                validation_result['recommendations'].append('子目录较多，扫描可能需要较长时间')
        except:
            pass

        return jsonify(validation_result)

    except Exception as e:
        logger.error(f"验证文件API错误: {e}")
        return jsonify({'error': f'验证文件失败: {str(e)}'}), 500


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