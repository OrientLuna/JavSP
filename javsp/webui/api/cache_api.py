"""
缓存相关API接口
"""

import logging
import json
from flask import Blueprint, request, jsonify, send_file
from pathlib import Path
from io import BytesIO

from ...scan_cache import get_cache

logger = logging.getLogger(__name__)

# 创建蓝图
cache_bp = Blueprint('cache', __name__)


@cache_bp.route('/stats', methods=['GET'])
def api_cache_stats():
    """获取缓存统计信息"""
    try:
        cache = get_cache()
        stats = cache.get_cache_stats()

        # 添加额外信息
        cache_file = Path(stats.get('cache_file', ''))
        if cache_file.exists():
            stats['cache_file_exists'] = True
            stats['cache_file_size'] = cache_file.stat().st_size
            stats['cache_file_modified'] = cache_file.stat().st_mtime
        else:
            stats['cache_file_exists'] = False
            stats['cache_file_size'] = 0
            stats['cache_file_modified'] = None

        return jsonify(stats)

    except Exception as e:
        logger.error(f"获取缓存统计API错误: {e}")
        return jsonify({'error': f'获取缓存统计失败: {str(e)}'}), 500


@cache_bp.route('/details', methods=['GET'])
def api_cache_details():
    """获取缓存详细信息"""
    try:
        # 获取查询参数
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 50, type=int)
        search = request.args.get('search', '').strip()

        cache = get_cache()
        cache_data = cache.cache_data

        # 搜索过滤
        if search:
            filtered_data = {}
            for file_path, cache_entry in cache_data.items():
                if (search.lower() in file_path.lower() or
                    search.lower() in cache_entry.get('movie_id', '').lower()):
                    filtered_data[file_path] = cache_entry
            cache_data = filtered_data

        # 转换为列表格式
        details = []
        for file_path, cache_entry in cache_data.items():
            details.append({
                'file_path': file_path,
                'movie_id': cache_entry.get('movie_id', 'Unknown'),
                'hash': cache_entry.get('hash', ''),
                'size': cache_entry.get('size', 0),
                'mtime': cache_entry.get('mtime', 0),
                'processed_at': cache_entry.get('processed_at', ''),
                'file_exists': Path(file_path).exists()
            })

        # 按处理时间排序
        details.sort(key=lambda x: x.get('processed_at', ''), reverse=True)

        # 分页
        total = len(details)
        start = (page - 1) * per_page
        end = start + per_page
        paginated_details = details[start:end]

        return jsonify({
            'details': paginated_details,
            'pagination': {
                'page': page,
                'per_page': per_page,
                'total': total,
                'pages': (total + per_page - 1) // per_page
            }
        })

    except Exception as e:
        logger.error(f"获取缓存详情API错误: {e}")
        return jsonify({'error': f'获取缓存详情失败: {str(e)}'}), 500


@cache_bp.route('/clear', methods=['DELETE'])
def api_cache_clear():
    """清空缓存"""
    try:
        cache = get_cache()
        cache.clear_cache()

        return jsonify({'message': '缓存已清空'})

    except Exception as e:
        logger.error(f"清空缓存API错误: {e}")
        return jsonify({'error': f'清空缓存失败: {str(e)}'}), 500


@cache_bp.route('/cleanup', methods=['POST'])
def api_cache_cleanup():
    """清理缓存（删除无效记录）"""
    try:
        cache = get_cache()
        removed_count = cache.cleanup_missing_files()

        return jsonify({
            'message': f'清理完成，删除了 {removed_count} 个无效记录',
            'removed_count': removed_count
        })

    except Exception as e:
        logger.error(f"清理缓存API错误: {e}")
        return jsonify({'error': f'清理缓存失败: {str(e)}'}), 500


@cache_bp.route('/export', methods=['GET'])
def api_cache_export():
    """导出缓存"""
    try:
        cache = get_cache()

        # 创建内存文件
        buffer = BytesIO()
        cache_data = json.dumps(cache.cache_data, ensure_ascii=False, indent=2)
        buffer.write(cache_data.encode('utf-8'))
        buffer.seek(0)

        return send_file(
            buffer,
            as_attachment=True,
            download_name='scan_cache.json',
            mimetype='application/json'
        )

    except Exception as e:
        logger.error(f"导出缓存API错误: {e}")
        return jsonify({'error': f'导出缓存失败: {str(e)}'}), 500


@cache_bp.route('/import', methods=['POST'])
def api_cache_import():
    """导入缓存"""
    try:
        # 检查是否有文件上传
        if 'file' in request.files:
            file = request.files['file']
            if file.filename:
                # 从文件读取
                try:
                    cache_data = json.load(file)
                except json.JSONDecodeError as e:
                    return jsonify({'error': f'文件格式错误: {str(e)}'}), 400
        else:
            # 从请求数据读取
            data = request.get_json()
            if not data or 'cache_data' not in data:
                return jsonify({'error': '请提供缓存数据'}), 400

            cache_data = data['cache_data']

        merge = request.form.get('merge', 'true').lower() == 'true' if request.form else True

        # 临时保存到文件并导入
        import tempfile
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False, encoding='utf-8') as temp_file:
            json.dump(cache_data, temp_file, ensure_ascii=False, indent=2)
            temp_file_path = temp_file.name

        try:
            cache = get_cache()
            cache.import_cache(temp_file_path, merge=merge)

            return jsonify({
                'message': f'缓存导入成功',
                'merge': merge,
                'imported_count': len(cache_data)
            })

        finally:
            # 清理临时文件
            Path(temp_file_path).unlink(missing_ok=True)

    except Exception as e:
        logger.error(f"导入缓存API错误: {e}")
        return jsonify({'error': f'导入缓存失败: {str(e)}'}), 500


@cache_bp.route('/validate', methods=['POST'])
def api_cache_validate():
    """验证缓存完整性"""
    try:
        cache = get_cache()

        validation_results = {
            'total_files': 0,
            'existing_files': 0,
            'missing_files': 0,
            'invalid_hashes': 0,
            'issues': []
        }

        for file_path, cache_entry in cache.cache_data.items():
            validation_results['total_files'] += 1

            file_exists = Path(file_path).exists()
            if file_exists:
                validation_results['existing_files'] += 1

                # 验证文件哈希
                try:
                    current_hash = cache._get_file_hash(file_path)
                    cached_hash = cache_entry.get('hash', '')
                    if current_hash != cached_hash:
                        validation_results['invalid_hashes'] += 1
                        validation_results['issues'].append({
                            'file_path': file_path,
                            'issue': '文件内容已变更',
                            'current_hash': current_hash,
                            'cached_hash': cached_hash
                        })
                except Exception as e:
                    validation_results['issues'].append({
                        'file_path': file_path,
                        'issue': f'无法计算文件哈希: {str(e)}'
                    })
            else:
                validation_results['missing_files'] += 1
                validation_results['issues'].append({
                    'file_path': file_path,
                    'issue': '文件不存在'
                })

        # 计算完整性评分
        if validation_results['total_files'] > 0:
            integrity_score = (validation_results['existing_files'] - validation_results['invalid_hashes']) / validation_results['total_files']
            validation_results['integrity_score'] = round(integrity_score * 100, 2)
        else:
            validation_results['integrity_score'] = 100

        return jsonify(validation_results)

    except Exception as e:
        logger.error(f"验证缓存API错误: {e}")
        return jsonify({'error': f'验证缓存失败: {str(e)}'}), 500


@cache_bp.route('/repair', methods=['POST'])
def api_cache_repair():
    """修复缓存问题"""
    try:
        cache = get_cache()

        repair_results = {
            'cleaned_missing': 0,
            'updated_hashes': 0,
            'errors': []
        }

        # 清理不存在的文件
        files_to_remove = []
        for file_path in cache.cache_data.keys():
            if not Path(file_path).exists():
                files_to_remove.append(file_path)

        for file_path in files_to_remove:
            del cache.cache_data[file_path]
            repair_results['cleaned_missing'] += 1

        # 更新文件哈希
        for file_path, cache_entry in cache.cache_data.items():
            try:
                current_hash = cache._get_file_hash(file_path)
                cached_hash = cache_entry.get('hash', '')
                if current_hash != cached_hash:
                    cache_entry['hash'] = current_hash
                    cache_entry['size'] = cache._get_file_size(file_path)
                    cache_entry['mtime'] = cache._get_file_mtime(file_path)
                    repair_results['updated_hashes'] += 1
            except Exception as e:
                repair_results['errors'].append({
                    'file_path': file_path,
                    'error': str(e)
                })

        # 保存修复后的缓存
        cache.save_cache()

        return jsonify({
            'message': '缓存修复完成',
            'results': repair_results
        })

    except Exception as e:
        logger.error(f"修复缓存API错误: {e}")
        return jsonify({'error': f'修复缓存失败: {str(e)}'}), 500