"""
配置相关API接口
"""

import logging
from flask import Blueprint, request, jsonify
import yaml
from pathlib import Path

from ...config import Cfg, FileMoveMode, OperationMode

logger = logging.getLogger(__name__)

# 创建蓝图
config_bp = Blueprint('config', __name__)


@config_bp.route('/', methods=['GET'])
def api_config_get():
    """获取当前配置"""
    try:
        cfg = Cfg()

        # 转换为字典格式
        config_dict = {
            'scanner': {
                'input_directory': str(cfg.scanner.input_directory) if cfg.scanner.input_directory else None,
                'filename_extensions': cfg.scanner.filename_extensions,
                'minimum_size': str(cfg.scanner.minimum_size),
                'skip_nfo_dir': cfg.scanner.skip_nfo_dir,
                'manual': cfg.scanner.manual,
                'ignored_id_pattern': cfg.scanner.ignored_id_pattern,
                'ignored_folder_name_pattern': cfg.scanner.ignored_folder_name_pattern
            },
            'network': {
                'proxy_server': str(cfg.network.proxy_server) if cfg.network.proxy_server else None,
                'retry': cfg.network.retry,
                'timeout': str(cfg.network.timeout)
            },
            'summarizer': {
                'operation_mode': cfg.summarizer.operation_mode.value,
                'move_files': cfg.summarizer.move_files,
                'move_mode': cfg.summarizer.path.move_mode.value,
                'use_absolute_paths': cfg.summarizer.path.use_absolute_paths,
                'output_folder': cfg.summarizer.path.output_folder_pattern
            },
            'general': {
                'cache_file': cfg.general.cache_file,
                'enable_incremental_scan': cfg.general.enable_incremental_scan,
                'cache_cleanup_interval': cfg.general.cache_cleanup_interval,
                'enable_webui': cfg.general.enable_webui,
                'webui_port': cfg.general.webui_port
            },
            'other': {
                'interactive': cfg.other.interactive,
                'check_update': cfg.other.check_update,
                'auto_update': cfg.other.auto_update
            }
        }

        return jsonify(config_dict)

    except Exception as e:
        logger.error(f"获取配置API错误: {e}")
        return jsonify({'error': f'获取配置失败: {str(e)}'}), 500


@config_bp.route('/', methods=['PUT'])
def api_config_update():
    """更新配置"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': '请提供配置数据'}), 400

        # 这里实现配置更新逻辑
        # 由于配置系统比较复杂，这里提供基本的配置保存功能
        try:
            config_file = Path('config.yml')

            # 读取现有配置
            if config_file.exists():
                with open(config_file, 'r', encoding='utf-8') as f:
                    config_data = yaml.safe_load(f)
            else:
                config_data = {}

            # 更新配置
            _update_config_data(config_data, data)

            # 保存配置
            with open(config_file, 'w', encoding='utf-8') as f:
                yaml.dump(config_data, f, default_flow_style=False, allow_unicode=True)

            return jsonify({'message': '配置已更新'})

        except Exception as e:
            logger.error(f"保存配置失败: {e}")
            return jsonify({'error': f'保存配置失败: {str(e)}'}), 500

    except Exception as e:
        logger.error(f"更新配置API错误: {e}")
        return jsonify({'error': f'更新配置失败: {str(e)}'}), 500


@config_bp.route('/schema', methods=['GET'])
def api_config_schema():
    """获取配置模式（字段定义）"""
    try:
        schema = {
            'scanner': {
                'input_directory': {'type': 'string', 'description': '扫描目录'},
                'filename_extensions': {'type': 'array', 'description': '支持的视频格式'},
                'minimum_size': {'type': 'string', 'description': '最小文件大小'},
                'skip_nfo_dir': {'type': 'boolean', 'description': '跳过包含NFO文件的文件夹'},
                'manual': {'type': 'boolean', 'description': '手动确认番号'},
                'ignored_id_pattern': {'type': 'array', 'description': '忽略的ID模式'},
                'ignored_folder_name_pattern': {'type': 'array', 'description': '忽略的文件夹名模式'}
            },
            'network': {
                'proxy_server': {'type': 'string', 'description': '代理服务器'},
                'retry': {'type': 'integer', 'description': '重试次数'},
                'timeout': {'type': 'string', 'description': '请求超时'}
            },
            'summarizer': {
                'operation_mode': {
                    'type': 'string',
                    'enum': ['scrape_and_organize', 'scrape_only', 'organize_only'],
                    'description': '运行模式'
                },
                'move_files': {'type': 'boolean', 'description': '移动文件'},
                'move_mode': {
                    'type': 'string',
                    'enum': ['move', 'hard_link', 'soft_link'],
                    'description': '移动模式'
                },
                'use_absolute_paths': {'type': 'boolean', 'description': '使用绝对路径'},
                'output_dir': {'type': 'string', 'description': '输出目录'}
            },
            'general': {
                'cache_file': {'type': 'string', 'description': '缓存文件路径'},
                'enable_incremental_scan': {'type': 'boolean', 'description': '启用增量扫描'},
                'cache_cleanup_interval': {'type': 'integer', 'description': '缓存清理间隔'},
                'enable_webui': {'type': 'boolean', 'description': '启用WebUI'},
                'webui_port': {'type': 'integer', 'description': 'WebUI端口'}
            },
            'other': {
                'interactive': {'type': 'boolean', 'description': '交互模式'},
                'check_update': {'type': 'boolean', 'description': '检查更新'},
                'auto_update': {'type': 'boolean', 'description': '自动更新'}
            }
        }

        return jsonify(schema)

    except Exception as e:
        logger.error(f"获取配置模式API错误: {e}")
        return jsonify({'error': f'获取配置模式失败: {str(e)}'}), 500


@config_bp.route('/validate', methods=['POST'])
def api_config_validate():
    """验证配置"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': '请提供配置数据'}), 400

        errors = []

        # 验证各个配置项
        if 'general' in data:
            general = data['general']

            # 验证WebUI端口
            if 'webui_port' in general:
                port = general['webui_port']
                if not isinstance(port, int) or port < 1 or port > 65535:
                    errors.append('WebUI端口必须是1-65535之间的整数')

            # 验证缓存清理间隔
            if 'cache_cleanup_interval' in general:
                interval = general['cache_cleanup_interval']
                if not isinstance(interval, int) or interval < 1:
                    errors.append('缓存清理间隔必须是正整数')

        if 'network' in data:
            network = data['network']

            # 验证重试次数
            if 'retry' in network:
                retry = network['retry']
                if not isinstance(retry, int) or retry < 0:
                    errors.append('重试次数必须是非负整数')

        if 'summarizer' in data:
            summarizer = data['summarizer']

            # 验证运行模式
            if 'operation_mode' in summarizer:
                mode = summarizer['operation_mode']
                valid_modes = ['scrape_and_organize', 'scrape_only', 'organize_only']
                if mode not in valid_modes:
                    errors.append(f'运行模式必须是: {", ".join(valid_modes)}')

            # 验证移动模式
            if 'move_mode' in summarizer:
                mode = summarizer['move_mode']
                valid_modes = ['move', 'hard_link', 'soft_link']
                if mode not in valid_modes:
                    errors.append(f'移动模式必须是: {", ".join(valid_modes)}')

        if errors:
            return jsonify({'valid': False, 'errors': errors})
        else:
            return jsonify({'valid': True, 'message': '配置验证通过'})

    except Exception as e:
        logger.error(f"验证配置API错误: {e}")
        return jsonify({'error': f'验证配置失败: {str(e)}'}), 500


@config_bp.route('/reset', methods=['POST'])
def api_config_reset():
    """重置配置为默认值"""
    try:
        # 这里实现配置重置逻辑
        # 为了演示，返回成功消息
        return jsonify({'message': '配置重置功能待实现'})

    except Exception as e:
        logger.error(f"重置配置API错误: {e}")
        return jsonify({'error': f'重置配置失败: {str(e)}'}), 500


@config_bp.route('/export', methods=['GET'])
def api_config_export():
    """导出配置"""
    try:
        config_file = Path('config.yml')
        if not config_file.exists():
            return jsonify({'error': '配置文件不存在'}), 404

        with open(config_file, 'r', encoding='utf-8') as f:
            config_content = f.read()

        return jsonify({
            'filename': 'config.yml',
            'content': config_content
        })

    except Exception as e:
        logger.error(f"导出配置API错误: {e}")
        return jsonify({'error': f'导出配置失败: {str(e)}'}), 500


@config_bp.route('/import', methods=['POST'])
def api_config_import():
    """导入配置"""
    try:
        data = request.get_json()
        if not data or 'content' not in data:
            return jsonify({'error': '请提供配置内容'}), 400

        config_content = data['content']

        # 验证YAML格式
        try:
            yaml.safe_load(config_content)
        except yaml.YAMLError as e:
            return jsonify({'error': f'配置格式错误: {str(e)}'}), 400

        # 保存配置
        config_file = Path('config.yml')
        with open(config_file, 'w', encoding='utf-8') as f:
            f.write(config_content)

        return jsonify({'message': '配置导入成功'})

    except Exception as e:
        logger.error(f"导入配置API错误: {e}")
        return jsonify({'error': f'导入配置失败: {str(e)}'}), 500


def _update_config_data(config_data: dict, updates: dict):
    """递归更新配置数据"""
    for key, value in updates.items():
        if key in config_data and isinstance(config_data[key], dict) and isinstance(value, dict):
            _update_config_data(config_data[key], value)
        else:
            config_data[key] = value