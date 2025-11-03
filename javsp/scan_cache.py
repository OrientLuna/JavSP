"""
文件扫描缓存模块
用于实现增量扫描，解决软链接模式下无法识别已处理文件的问题
"""
import json
import hashlib
import logging
import os
from pathlib import Path
from typing import Dict, List, Optional, Set
from datetime import datetime

logger = logging.getLogger(__name__)


class ScanCache:
    """扫描缓存管理器"""

    def __init__(self, cache_file: str = "data/scan_cache.json"):
        """
        初始化缓存管理器

        Args:
            cache_file: 缓存文件路径
        """
        self.cache_file = Path(cache_file)
        self.cache_file.parent.mkdir(parents=True, exist_ok=True)
        self.cache_data: Dict[str, Dict] = {}
        self.load_cache()

    def _get_file_hash(self, file_path: str) -> str:
        """
        计算文件哈希值

        Args:
            file_path: 文件路径

        Returns:
            文件内容的MD5哈希值
        """
        try:
            with open(file_path, 'rb') as f:
                # 只读取文件前1MB来计算哈希，提高性能
                content = f.read(1024 * 1024)
                return hashlib.md5(content).hexdigest()
        except (IOError, OSError) as e:
            logger.warning(f"无法计算文件哈希 '{file_path}': {e}")
            return ""

    def _get_file_size(self, file_path: str) -> int:
        """获取文件大小"""
        try:
            return os.path.getsize(file_path)
        except OSError:
            return 0

    def _get_file_mtime(self, file_path: str) -> float:
        """获取文件修改时间"""
        try:
            return os.path.getmtime(file_path)
        except OSError:
            return 0

    def load_cache(self):
        """从文件加载缓存"""
        if self.cache_file.exists():
            try:
                with open(self.cache_file, 'r', encoding='utf-8') as f:
                    self.cache_data = json.load(f)
                logger.debug(f"已加载扫描缓存: {len(self.cache_data)} 个文件")
            except (json.JSONDecodeError, IOError) as e:
                logger.warning(f"加载缓存文件失败: {e}")
                self.cache_data = {}
        else:
            self.cache_data = {}

    def save_cache(self):
        """保存缓存到文件"""
        try:
            with open(self.cache_file, 'w', encoding='utf-8') as f:
                json.dump(self.cache_data, f, ensure_ascii=False, indent=2)
            logger.debug(f"已保存扫描缓存: {len(self.cache_data)} 个文件")
        except IOError as e:
            logger.warning(f"保存缓存文件失败: {e}")

    def is_file_processed(self, file_path: str, movie_id: Optional[str] = None) -> bool:
        """
        检查文件是否已处理过

        Args:
            file_path: 文件路径
            movie_id: 可选的电影番号，用于更精确的匹配

        Returns:
            True 如果文件已处理过且内容未变化
        """
        if file_path not in self.cache_data:
            return False

        cache_entry = self.cache_data[file_path]

        # 检查文件是否存在
        if not os.path.exists(file_path):
            # 文件不存在，从缓存中移除
            del self.cache_data[file_path]
            return False

        # 检查文件哈希是否变化
        current_hash = self._get_file_hash(file_path)
        if cache_entry.get('hash') != current_hash:
            logger.debug(f"文件内容已变化: {file_path}")
            return False

        # 如果提供了movie_id，检查是否匹配
        if movie_id and cache_entry.get('movie_id') != movie_id:
            logger.debug(f"文件关联的番号不匹配: {file_path}")
            return False

        return True

    def mark_file_processed(self, file_path: str, movie_id: str, processed_at: Optional[str] = None):
        """
        标记文件为已处理

        Args:
            file_path: 文件路径
            movie_id: 电影番号
            processed_at: 处理时间，默认为当前时间
        """
        if not processed_at:
            processed_at = datetime.now().isoformat()

        self.cache_data[file_path] = {
            'hash': self._get_file_hash(file_path),
            'size': self._get_file_size(file_path),
            'mtime': self._get_file_mtime(file_path),
            'movie_id': movie_id,
            'processed_at': processed_at
        }

    def get_processed_files_by_movie_id(self, movie_id: str) -> List[str]:
        """
        获取指定番号的所有已处理文件

        Args:
            movie_id: 电影番号

        Returns:
            已处理的文件路径列表
        """
        return [
            file_path for file_path, cache_entry in self.cache_data.items()
            if cache_entry.get('movie_id') == movie_id and os.path.exists(file_path)
        ]

    def remove_file(self, file_path: str):
        """
        从缓存中移除文件记录

        Args:
            file_path: 文件路径
        """
        if file_path in self.cache_data:
            del self.cache_data[file_path]

    def cleanup_missing_files(self) -> int:
        """
        清理不存在的文件记录

        Returns:
            清理的文件数量
        """
        removed_count = 0
        files_to_remove = []

        for file_path in self.cache_data.keys():
            if not os.path.exists(file_path):
                files_to_remove.append(file_path)

        for file_path in files_to_remove:
            del self.cache_data[file_path]
            removed_count += 1

        if removed_count > 0:
            logger.debug(f"清理了 {removed_count} 个不存在的文件记录")

        return removed_count

    def clear_cache(self):
        """清空所有缓存"""
        self.cache_data.clear()
        logger.info("已清空扫描缓存")

    def get_cache_stats(self) -> Dict:
        """
        获取缓存统计信息

        Returns:
            包含统计信息的字典
        """
        total_files = len(self.cache_data)
        existing_files = sum(1 for file_path in self.cache_data.keys() if os.path.exists(file_path))
        movie_ids = set(entry.get('movie_id') for entry in self.cache_data.values() if entry.get('movie_id'))

        return {
            'total_files': total_files,
            'existing_files': existing_files,
            'missing_files': total_files - existing_files,
            'unique_movies': len(movie_ids),
            'cache_file': str(self.cache_file)
        }

    def export_cache(self, export_file: str):
        """
        导出缓存到指定文件

        Args:
            export_file: 导出文件路径
        """
        try:
            export_path = Path(export_file)
            export_path.parent.mkdir(parents=True, exist_ok=True)

            with open(export_path, 'w', encoding='utf-8') as f:
                json.dump(self.cache_data, f, ensure_ascii=False, indent=2)

            logger.info(f"已导出缓存到: {export_file}")
        except IOError as e:
            logger.error(f"导出缓存失败: {e}")

    def import_cache(self, import_file: str, merge: bool = True):
        """
        从指定文件导入缓存

        Args:
            import_file: 导入文件路径
            merge: 是否与现有缓存合并，False则替换现有缓存
        """
        try:
            with open(import_file, 'r', encoding='utf-8') as f:
                imported_data = json.load(f)

            if merge:
                self.cache_data.update(imported_data)
                logger.info(f"已合并缓存: 新增 {len(imported_data)} 条记录")
            else:
                self.cache_data = imported_data
                logger.info(f"已替换缓存: 共 {len(imported_data)} 条记录")

        except (json.JSONDecodeError, IOError) as e:
            logger.error(f"导入缓存失败: {e}")


# 全局缓存实例
_global_cache: Optional[ScanCache] = None


def get_cache() -> ScanCache:
    """
    获取全局缓存实例

    Returns:
        ScanCache实例
    """
    global _global_cache
    if _global_cache is None:
        from javsp.config import Cfg
        cache_file = Cfg().general.cache_file
        _global_cache = ScanCache(cache_file)
    return _global_cache


def init_cache(cache_file: Optional[str] = None):
    """
    初始化全局缓存

    Args:
        cache_file: 缓存文件路径，如果为None则使用配置中的路径
    """
    global _global_cache
    if cache_file:
        _global_cache = ScanCache(cache_file)
    else:
        _global_cache = get_cache()


def save_cache():
    """保存全局缓存"""
    if _global_cache:
        _global_cache.save_cache()