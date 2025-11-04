"""
增量刮削跟踪系统

提供基于JSON文件的刮削记录功能，避免重复处理已处理的文件。
支持轻量级的重复文件检测和处理。
"""

import json
import os
import time
from pathlib import Path
from typing import Dict, List, Optional, Set, Any
from datetime import datetime

from javsp.config import Cfg
import logging

logger = logging.getLogger(__name__)


class ProcessedMovie:
    """已处理电影的记录结构"""

    def __init__(self, movie_id: str, data_src: str = "normal"):
        self.movie_id = movie_id
        self.data_src = data_src
        self.processed_time = time.time()
        self.source_files: List[Dict[str, Any]] = []
        self.target_files: List[str] = []
        self.config_hash: Optional[str] = None

    def add_source_file(self, file_path: str, file_size: int, file_mtime: float):
        """添加源文件信息"""
        self.source_files.append({
            "path": file_path,
            "size": file_size,
            "mtime": file_mtime
        })

    def add_target_file(self, file_path: str):
        """添加目标文件信息"""
        self.target_files.append(file_path)

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "movie_id": self.movie_id,
            "data_src": self.data_src,
            "processed_time": self.processed_time,
            "source_files": self.source_files,
            "target_files": self.target_files,
            "config_hash": self.config_hash
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ProcessedMovie':
        """从字典创建实例"""
        movie = cls(data["movie_id"], data.get("data_src", "normal"))
        movie.processed_time = data["processed_time"]
        movie.source_files = data.get("source_files", [])
        movie.target_files = data.get("target_files", [])
        movie.config_hash = data.get("config_hash")
        return movie


class IncrementalTracker:
    """增量刮削跟踪器"""

    def __init__(self, tracking_file: Optional[str] = None):
        self.tracking_file = tracking_file or self._get_default_tracking_file()
        self.processed_movies: Dict[str, ProcessedMovie] = {}
        self._load_tracking_data()

    def _get_default_tracking_file(self) -> str:
        """获取默认跟踪文件路径"""
        cfg_instance = Cfg()
        if hasattr(cfg_instance.scanner, 'tracking_file') and cfg_instance.scanner.tracking_file:
            # 如果是相对路径，相对于输入目录
            tracking_file = cfg_instance.scanner.tracking_file
            if not os.path.isabs(tracking_file) and cfg_instance.scanner.input_directory:
                tracking_file = os.path.join(cfg_instance.scanner.input_directory, tracking_file)
            return tracking_file

        # 默认在输入目录下创建隐藏文件
        if cfg_instance.scanner.input_directory:
            return os.path.join(cfg_instance.scanner.input_directory, ".javsp_processed.json")

        # 最后备选：当前目录
        return ".javsp_processed.json"

    def _load_tracking_data(self):
        """加载跟踪数据"""
        if not os.path.exists(self.tracking_file):
            logger.debug(f"跟踪文件不存在，将创建新的: {self.tracking_file}")
            return

        try:
            with open(self.tracking_file, 'r', encoding='utf-8') as f:
                data = json.load(f)

            for movie_id, movie_data in data.get("processed_movies", {}).items():
                self.processed_movies[movie_id] = ProcessedMovie.from_dict(movie_data)

            logger.debug(f"从跟踪文件加载了 {len(self.processed_movies)} 个已处理电影的记录")
        except Exception as e:
            logger.warning(f"加载跟踪文件失败: {e}，将重新开始跟踪")
            self.processed_movies = {}

    def _save_tracking_data(self):
        """保存跟踪数据"""
        try:
            # 确保目录存在
            os.makedirs(os.path.dirname(self.tracking_file), exist_ok=True)

            data = {
                "version": "1.0",
                "last_run": time.time(),
                "processed_movies": {
                    movie_id: movie.to_dict()
                    for movie_id, movie in self.processed_movies.items()
                }
            }

            with open(self.tracking_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)

            logger.debug(f"跟踪数据已保存到: {self.tracking_file}")
        except Exception as e:
            logger.error(f"保存跟踪数据失败: {e}")

    def is_movie_processed(self, movie_id: str, source_files: List[str]) -> bool:
        """检查电影是否已处理"""
        cfg_instance = Cfg()
        # 检查是否启用增量刮削
        if not hasattr(cfg_instance.scanner, 'incremental') or not cfg_instance.scanner.incremental:
            return False

        # 如果没有跟踪文件或为空，返回False
        if not self.processed_movies:
            return False

        if movie_id not in self.processed_movies:
            return False

        processed_movie = self.processed_movies[movie_id]

        # 检查源文件是否有变更
        if hasattr(cfg_instance.scanner, 'update_modified') and cfg_instance.scanner.update_modified:
            return self._check_files_unchanged(processed_movie, source_files)

        # 默认情况下，如果记录存在就认为已处理
        return True

    def _check_files_unchanged(self, processed_movie: ProcessedMovie, source_files: List[str]) -> bool:
        """检查源文件是否未变更"""
        for file_path in source_files:
            if not os.path.exists(file_path):
                return False

            current_size = os.path.getsize(file_path)
            current_mtime = os.path.getmtime(file_path)

            # 查找匹配的记录
            file_changed = True
            for file_record in processed_movie.source_files:
                if file_record["path"] == file_path:
                    if (abs(file_record["size"] - current_size) < 1024 and  # 大小允许1KB误差
                        abs(file_record["mtime"] - current_mtime) < 1):      # 时间允许1秒误差
                        file_changed = False
                    break

            if file_changed:
                return False

        return True

    def mark_movie_processed(self, movie_id: str, data_src: str, source_files: List[str],
                           target_files: List[str]):
        """标记电影为已处理"""
        processed_movie = ProcessedMovie(movie_id, data_src)

        # 添加源文件信息
        for file_path in source_files:
            if os.path.exists(file_path):
                processed_movie.add_source_file(
                    file_path,
                    os.path.getsize(file_path),
                    os.path.getmtime(file_path)
                )

        # 添加目标文件信息
        for file_path in target_files:
            processed_movie.add_target_file(file_path)

        self.processed_movies[movie_id] = processed_movie
        self._save_tracking_data()
        logger.debug(f"电影 {movie_id} 已标记为处理完成")

    def remove_movie(self, movie_id: str):
        """移除电影的跟踪记录"""
        if movie_id in self.processed_movies:
            del self.processed_movies[movie_id]
            self._save_tracking_data()
            logger.debug(f"已移除电影 {movie_id} 的跟踪记录")

    def get_processed_movie_ids(self) -> Set[str]:
        """获取所有已处理的电影ID"""
        return set(self.processed_movies.keys())

    def cleanup_missing_targets(self):
        """清理目标文件不存在的记录"""
        cleaned_count = 0
        movies_to_remove = []

        for movie_id, processed_movie in self.processed_movies.items():
            # 检查是否有目标文件存在
            has_existing_target = any(
                os.path.exists(target_file)
                for target_file in processed_movie.target_files
            )

            if not has_existing_target:
                movies_to_remove.append(movie_id)

        for movie_id in movies_to_remove:
            del self.processed_movies[movie_id]
            cleaned_count += 1

        if cleaned_count > 0:
            self._save_tracking_data()
            logger.info(f"清理了 {cleaned_count} 个目标文件不存在的记录")

        return cleaned_count

    def get_statistics(self) -> Dict[str, Any]:
        """获取跟踪统计信息"""
        total_movies = len(self.processed_movies)
        total_source_files = sum(
            len(movie.source_files)
            for movie in self.processed_movies.values()
        )
        total_target_files = sum(
            len(movie.target_files)
            for movie in self.processed_movies.values()
        )

        return {
            "tracking_file": self.tracking_file,
            "total_movies": total_movies,
            "total_source_files": total_source_files,
            "total_target_files": total_target_files,
            "last_run": max(
                (movie.processed_time for movie in self.processed_movies.values()),
                default=0
            )
        }


# 全局跟踪器实例
_tracker: Optional[IncrementalTracker] = None


def get_tracker() -> IncrementalTracker:
    """获取全局跟踪器实例"""
    global _tracker
    if _tracker is None:
        _tracker = IncrementalTracker()
    return _tracker


def reset_tracker():
    """重置全局跟踪器实例"""
    global _tracker
    _tracker = None