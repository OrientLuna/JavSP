"""
轻量重复文件处理模块

提供基本的重复文件检测和处理逻辑，主要针对新下载的重复文件。
"""

import os
import shutil
import logging
from enum import Enum
from typing import List, Optional, Tuple

from javsp.config import Cfg, FileMoveMode


class DuplicateStrategy(Enum):
    """重复文件处理策略"""
    SKIP = "skip"          # 跳过
    REPLACE = "replace"    # 替换
    ASK = "ask"           # 询问用户
    RENAME = "rename"     # 重命名


logger = logging.getLogger(__name__)


class DuplicateHandler:
    """重复文件处理器"""

    def __init__(self):
        self.strategy = self._get_strategy()

    def _get_strategy(self) -> DuplicateStrategy:
        """获取配置的重复处理策略"""
        cfg_instance = Cfg()
        if hasattr(cfg_instance.scanner, 'duplicate_strategy'):
            strategy = cfg_instance.scanner.duplicate_strategy.lower()
            try:
                return DuplicateStrategy(strategy)
            except ValueError:
                logger.warning(f"未知的重复处理策略: {strategy}，使用默认策略 'ask'")

        return DuplicateStrategy.ASK  # 默认策略

    def _compare_files(self, src_file: str, dst_file: str) -> Tuple[bool, str]:
        """比较两个文件，返回(是否替换, 原因)"""
        if not os.path.exists(dst_file):
            return True, "目标文件不存在"

        if not os.path.exists(src_file):
            return False, "源文件不存在"

        # 基本文件信息比较
        src_size = os.path.getsize(src_file)
        dst_size = os.path.getsize(dst_file)
        src_mtime = os.path.getmtime(src_file)
        dst_mtime = os.path.getmtime(dst_file)

        # 如果文件大小差异很小（小于1KB），认为是相同文件
        if abs(src_size - dst_size) < 1024:
            # 如果修改时间也相近，认为是同一文件
            if abs(src_mtime - dst_mtime) < 1:
                return False, "文件相同（大小和修改时间）"
            else:
                # 修改时间较新的优先
                if src_mtime > dst_mtime:
                    return True, "源文件更新"
                else:
                    return False, "目标文件更新"

        # 简单的大小比较策略
        if src_size > dst_size * 1.1:  # 源文件比目标文件大10%以上
            return True, f"源文件质量更好（{src_size} vs {dst_size} 字节）"
        elif dst_size > src_size * 1.1:  # 目标文件比源文件大10%以上
            return False, f"目标文件质量更好（{dst_size} vs {src_size} 字节）"
        else:
            # 文件大小相近，优先保留已有的
            return False, "文件质量相近，保留现有文件"

    def _ask_user(self, src_file: str, dst_file: str, reason: str) -> bool:
        """询问用户是否替换文件"""
        try:
            src_name = os.path.basename(src_file)
            dst_name = os.path.basename(dst_file)

            print(f"\n发现重复文件:")
            print(f"  源文件: {src_name}")
            print(f"  目标文件: {dst_name}")
            print(f"  建议: {reason}")

            while True:
                choice = input("是否替换目标文件? [y/N/r(重命名)]: ").strip().lower()
                if choice in ['', 'n']:
                    return False
                elif choice == 'y':
                    return True
                elif choice == 'r':
                    return 'rename'
                else:
                    print("请输入 y(是), n(否), 或 r(重命名)")
        except (EOFError, KeyboardInterrupt):
            print("\n默认选择: 不替换")
            return False

    def handle_duplicate(self, src_file: str, dst_file: str) -> Optional[str]:
        """
        处理重复文件

        Args:
            src_file: 源文件路径
            dst_file: 目标文件路径

        Returns:
            处理后的文件路径，如果跳过则返回None
        """
        if not os.path.exists(dst_file):
            return dst_file  # 目标文件不存在，直接返回

        # 比较文件
        should_replace, reason = self._compare_files(src_file, dst_file)

        # 根据策略决定如何处理
        if self.strategy == DuplicateStrategy.SKIP:
            logger.debug(f"跳过重复文件: {os.path.basename(dst_file)} ({reason})")
            return None

        elif self.strategy == DuplicateStrategy.REPLACE:
            if should_replace:
                logger.info(f"替换重复文件: {os.path.basename(dst_file)} ({reason})")
                return dst_file
            else:
                logger.debug(f"跳过重复文件: {os.path.basename(dst_file)} ({reason})")
                return None

        elif self.strategy == DuplicateStrategy.ASK:
            user_choice = self._ask_user(src_file, dst_file, reason)

            if user_choice == 'rename':
                # 生成新的文件名
                base, ext = os.path.splitext(dst_file)
                counter = 1
                while os.path.exists(f"{base}_{counter}{ext}"):
                    counter += 1
                new_dst = f"{base}_{counter}{ext}"
                logger.info(f"重命名重复文件: {os.path.basename(dst_file)} -> {os.path.basename(new_dst)}")
                return new_dst
            elif user_choice:
                logger.info(f"用户选择替换: {os.path.basename(dst_file)} ({reason})")
                return dst_file
            else:
                logger.debug(f"用户选择跳过: {os.path.basename(dst_file)}")
                return None

        elif self.strategy == DuplicateStrategy.RENAME:
            # 总是重命名
            base, ext = os.path.splitext(dst_file)
            counter = 1
            while os.path.exists(f"{base}_{counter}{ext}"):
                counter += 1
            new_dst = f"{base}_{counter}{ext}"
            logger.info(f"重命名重复文件: {os.path.basename(dst_file)} -> {os.path.basename(new_dst)}")
            return new_dst

        return None


def move_file_with_duplicate_check(src: str, dst: str, move_mode: FileMoveMode = None) -> Optional[str]:
    """
    移动文件并处理重复文件

    Args:
        src: 源文件路径
        dst: 目标文件路径
        move_mode: 移动模式

    Returns:
        实际使用的目标文件路径，如果跳过则返回None
    """
    if move_mode is None:
        cfg_instance = Cfg()
        move_mode = cfg_instance.summarizer.path.move_mode

    # 如果目标文件不存在，直接移动
    if not os.path.exists(dst):
        if move_mode == FileMoveMode.MOVE:
            shutil.move(src, dst)
        elif move_mode == FileMoveMode.HARD_LINK:
            os.link(src, dst)
        elif move_mode == FileMoveMode.SOFT_LINK:
            os.symlink(src, dst)
        return dst

    # 处理重复文件
    handler = DuplicateHandler()
    final_dst = handler.handle_duplicate(src, dst)

    if final_dst is None:
        # 跳过
        return None

    if final_dst != dst:
        # 如果文件名被修改了
        dst = final_dst

    # 执行文件操作
    try:
        if move_mode == FileMoveMode.MOVE:
            # 先删除目标文件（如果存在）
            if os.path.exists(dst):
                os.remove(dst)
            shutil.move(src, dst)
        elif move_mode == FileMoveMode.HARD_LINK:
            # 如果目标链接已存在，先删除
            if os.path.exists(dst):
                os.remove(dst)
            os.link(src, dst)
        elif move_mode == FileMoveMode.SOFT_LINK:
            # 如果目标链接已存在，先删除
            if os.path.exists(dst):
                os.remove(dst)
            os.symlink(src, dst)

        return dst
    except Exception as e:
        logger.error(f"文件操作失败: {e}")
        return None