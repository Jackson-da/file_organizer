"""
organizer/utils.py - 工具函数
"""

import logging
import os
import shutil
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import yaml

from .rules import validate_category_name

logger = logging.getLogger(__name__)

# 文件大小格式化常量
_SIZE_KB = 1024
_SIZE_MB = 1024 ** 2
_SIZE_GB = 1024 ** 3

# 文件名冲突重命名上限
_FILENAME_COLLISION_MAX = 1000


def get_file_extension(file_path: Path) -> str:
    """
    获取文件的扩展名（包含点号）。

    Args:
        file_path: 文件路径对象

    Returns:
        文件扩展名（小写，包含点号）
    """
    return file_path.suffix.lower()


def is_path_under_root(path: Path, root: Path) -> bool:
    """判断 path 解析后是否位于 root 目录之下（含 root 本身）。"""
    try:
        resolved_path = path.resolve()
        resolved_root = root.resolve()
        resolved_path.relative_to(resolved_root)
        return True
    except (ValueError, OSError) as exc:
        logger.debug("路径不在根目录下: %s -> %s: %s", path, root, exc)
        return False


def verify_target_category_dir(root: Path, category: str) -> Tuple[bool, str]:
    """
    校验分类子目录是否可安全使用：名称合法、非同名文件、解析后仍在根目录内。
    """
    if not validate_category_name(category):
        return False, f"非法或不允许的分类文件夹名: {category!r}"

    target = root / category
    if target.exists() and not target.is_dir():
        return False, f"「{category}」已存在且不是文件夹，无法写入"

    if target.exists():
        if not is_path_under_root(target, root):
            return (
                False,
                f"「{category}」解析后不在所选文件夹内（可能是指向外部的符号链接）",
            )

    return True, ""


def ensure_dir_exists(dir_path: Path) -> bool:
    """
    确保目录存在，如果不存在则创建。

    Args:
        dir_path: 目录路径对象

    Returns:
        True 如果目录存在或创建成功，False 如果创建失败
    """
    try:
        dir_path.mkdir(parents=True, exist_ok=True)
        return True
    except OSError as exc:
        logger.warning("创建目录失败: %s — %s", dir_path, exc, exc_info=True)
        return False


def _resolve_target_filename(
    source: Path,
    target_dir: Path,
    overwrite: bool,
    suffix_template: str = "_{}{}",
) -> Tuple[Path, Optional[str]]:
    """
    解析目标文件路径，处理文件名冲突。

    Args:
        source: 源文件路径
        target_dir: 目标目录路径
        overwrite: 是否覆盖已存在的文件
        suffix_template: 冲突时后缀格式，默认为 "_{}{}" (name_counter_ext)

    Returns:
        Tuple[目标路径, 错误信息或None]
    """
    target_file = target_dir / source.name

    if target_file.exists() and not overwrite:
        base_name = source.stem
        extension = source.suffix
        counter = 1
        while target_file.exists():
            if counter > _FILENAME_COLLISION_MAX:
                return target_file, f"无法为文件找到可用名称（已尝试 {_FILENAME_COLLISION_MAX} 次）: {source.name}"
            new_name = suffix_template.format(counter, extension)
            target_file = target_dir / f"{base_name}{new_name}"
            counter += 1

    return target_file, None


def safe_move_file(
    source: Path,
    target_dir: Path,
    overwrite: bool = False,
    root: Optional[Path] = None,
) -> Tuple[bool, Optional[str]]:
    """
    安全地移动文件到目标目录。

    Args:
        source: 源文件路径
        target_dir: 目标目录路径
        overwrite: 是否覆盖已存在的文件
        root: 若给定，则源、目标均须解析后位于该根目录下

    Returns:
        Tuple[bool, Optional[str]]: (是否成功, 错误信息或None)
    """
    try:
        if root is not None:
            try:
                src_resolved = source.resolve()
            except OSError as exc:
                logger.warning("无法解析源路径: %s — %s", source, exc)
                return False, f"无法解析源文件路径: {source.name}"
            if not is_path_under_root(src_resolved, root):
                return False, "源文件不在允许的根文件夹内（可能已被替换为外部链接）"

        if not ensure_dir_exists(target_dir):
            return False, f"无法创建目标目录: {target_dir}"

        if root is not None and not is_path_under_root(target_dir, root):
            return False, "目标目录不在允许的根文件夹内"

        # 使用公共函数处理文件名冲突
        target_file, err = _resolve_target_filename(source, target_dir, overwrite)
        if err:
            return False, err

        if root is not None and not is_path_under_root(target_file.parent, root):
            return False, "目标路径不在允许的根文件夹内"

        if root is not None:
            try:
                dest_check = target_file.resolve()
            except OSError as exc:
                logger.warning("无法解析目标文件路径: %s — %s", target_file, exc)
                return False, f"无法解析目标路径: {target_file.name}"
            if not is_path_under_root(dest_check, root):
                return False, "目标文件路径解析后不在允许的根文件夹内"

        shutil.move(str(source), str(target_file))
        return True, None

    except PermissionError as exc:
        logger.warning("移动文件权限错误: %s — %s", source, exc)
        return False, f"权限不足，无法移动文件: {source.name}"
    except FileNotFoundError as exc:
        logger.warning("移动文件未找到: %s — %s", source, exc)
        return False, f"文件不存在: {source}"
    except OSError as exc:
        logger.warning("移动文件系统错误: %s — %s", source, exc, exc_info=True)
        return False, f"移动文件时系统错误: {source.name} — {exc}"
    except shutil.Error as exc:
        logger.warning("shutil 移动失败: %s — %s", source, exc, exc_info=True)
        return False, f"移动文件失败: {source.name} — {exc}"


def copy_file(
    source: Path,
    target_dir: Path,
    overwrite: bool = False,
    root: Optional[Path] = None,
) -> Tuple[bool, Optional[str]]:
    """
    安全地复制文件到目标目录。
    """
    try:
        if root is not None:
            try:
                src_resolved = source.resolve()
            except OSError as exc:
                logger.warning("无法解析源路径: %s — %s", source, exc)
                return False, f"无法解析源文件路径: {source.name}"
            if not is_path_under_root(src_resolved, root):
                return False, "源文件不在允许的根文件夹内"

        if not ensure_dir_exists(target_dir):
            return False, f"无法创建目标目录: {target_dir}"

        if root is not None and not is_path_under_root(target_dir, root):
            return False, "目标目录不在允许的根文件夹内"

        # 使用公共函数处理文件名冲突（复制使用 _copy_ 后缀）
        target_file, err = _resolve_target_filename(
            source, target_dir, overwrite, suffix_template="_copy_{}{}"
        )
        if err:
            return False, err

        if root is not None:
            try:
                dest_check = target_file.resolve()
            except OSError as exc:
                logger.warning("无法解析目标文件路径: %s — %s", target_file, exc)
                return False, f"无法解析目标路径: {target_file.name}"
            if not is_path_under_root(dest_check, root):
                return False, "目标文件路径解析后不在允许的根文件夹内"

        shutil.copy2(str(source), str(target_file))
        return True, None

    except PermissionError as exc:
        logger.warning("复制文件权限错误: %s — %s", source, exc)
        return False, f"权限不足，无法复制文件: {source.name}"
    except OSError as exc:
        logger.warning("复制文件系统错误: %s — %s", source, exc, exc_info=True)
        return False, f"复制文件时系统错误: {source.name} — {exc}"
    except shutil.Error as exc:
        logger.warning("shutil 复制失败: %s — %s", source, exc, exc_info=True)
        return False, f"复制文件失败: {source.name} — {exc}"


def format_file_size(size_bytes: int) -> str:
    """
    格式化文件大小为可读字符串。

    Args:
        size_bytes: 文件大小（字节）

    Returns:
        格式化后的大小字符串（如 "1.5 MB"）
    """
    if size_bytes < _SIZE_KB:
        return f"{size_bytes} B"
    elif size_bytes < _SIZE_MB:
        return f"{size_bytes / _SIZE_KB:.1f} KB"
    elif size_bytes < _SIZE_GB:
        return f"{size_bytes / _SIZE_MB:.1f} MB"
    else:
        return f"{size_bytes / _SIZE_GB:.1f} GB"


def load_config(config_path: str) -> Tuple[Optional[dict], Optional[str]]:
    """
    从 YAML 文件加载配置。

    Returns:
        (配置字典, None) 成功时；(None, 错误说明) 失败时。
    """
    try:
        with open(config_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
        if data is not None and not isinstance(data, dict):
            return None, "配置文件根节点必须是映射（字典）类型"
        return data, None
    except FileNotFoundError:
        return None, "配置文件不存在"
    except OSError as exc:
        logger.warning("读取配置失败: %s — %s", config_path, exc)
        return None, f"无法读取配置文件: {exc}"
    except yaml.YAMLError as exc:
        logger.warning("YAML 解析失败: %s — %s", config_path, exc)
        return None, f"YAML 格式错误: {exc}"


def save_config(config: dict, config_path: str) -> bool:
    """
    保存配置到 YAML 文件。

    Args:
        config: 配置字典
        config_path: 配置文件路径

    Returns:
        True 如果保存成功，False 如果保存失败
    """
    try:
        with open(config_path, "w", encoding="utf-8") as f:
            yaml.dump(config, f, allow_unicode=True, default_flow_style=False)
        return True
    except OSError as exc:
        logger.warning("保存配置失败: %s — %s", config_path, exc, exc_info=True)
        return False
    except yaml.YAMLError as exc:
        logger.warning("YAML 序列化失败: %s — %s", config_path, exc)
        return False


def is_hidden_file(file_path: Path) -> bool:
    """
    检查文件是否为隐藏文件。
    """
    if os.name == "nt":
        try:
            import ctypes

            attrs = ctypes.windll.kernel32.GetFileAttributesW(str(file_path))
            if attrs != -1 and bool(attrs & 2):
                return True
        except OSError as exc:
            logger.debug("GetFileAttributesW 失败，回退到文件名判断: %s — %s", file_path, exc)
        except AttributeError as exc:
            logger.debug("ctypes 属性异常，回退到文件名判断: %s — %s", file_path, exc)

    return file_path.name.startswith(".")


def validate_folder_path(
    folder_path: str,
    require_write: bool = False,
) -> Tuple[bool, Optional[str]]:
    """
    验证文件夹路径是否有效。

    Args:
        folder_path: 文件夹路径
        require_write: 为 True 时额外要求对目录有写权限（整理前使用）

    Note:
        Windows 上权限检查可能受 UAC 影响，以管理员权限运行时
        可能无法准确检测普通用户权限。
    """
    path = Path(folder_path)

    if not path.exists():
        return False, "文件夹不存在"

    if not path.is_dir():
        return False, "路径不是文件夹"

    if not os.access(path, os.R_OK):
        return False, "没有读取权限"

    if require_write and not os.access(path, os.W_OK):
        return False, "没有写入权限，无法整理或移动文件"

    return True, None
