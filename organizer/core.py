"""
organizer/core.py - 核心文件整理逻辑
"""

import logging
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd

from .rules import (
    build_extension_index,
    get_default_extension_index,
    get_effective_rules,
    validate_category_name,
)
from .utils import (
    ensure_dir_exists,
    get_file_extension,
    is_path_under_root,
    safe_move_file,
    validate_folder_path,
    verify_target_category_dir,
)

logger = logging.getLogger(__name__)

# 预览表最多构建的行数（界面分页展示；超出则截断并提示）
PREVIEW_BUILD_LIMIT = 100_000


def _relative_display_path(file_path: Path, root_resolved: Path) -> str:
    """用于界面展示：相对所选文件夹的路径，避免泄露完整绝对路径。"""
    try:
        return os.path.relpath(file_path.resolve(), start=root_resolved)
    except ValueError:
        return file_path.name


@dataclass
class OrganizeResult:
    """文件整理结果数据类"""

    total_files: int = 0
    moved_files: int = 0
    skipped_files: int = 0
    errors: List[str] = field(default_factory=list)
    categories: Dict[str, int] = field(default_factory=dict)


@dataclass
class FolderAnalysis:
    """单次遍历根目录后的分析结果（性能优化与安全统计）。"""

    root_resolved: Path
    all_files: List[Path]
    organizable_files: List[Path]
    categorized_files: List[Path]
    total_size: int
    file_types: Dict[str, int]
    subdirs: List[str]
    stat_failed: int
    symlink_count: int


def categorize_file(
    file_ext: str,
    rules: Dict[str, List[str]],
) -> Optional[str]:
    """
    根据文件扩展名确定目标文件夹类别。
    """
    idx = build_extension_index(rules)
    return idx.get(file_ext.lower())


def analyze_folder(
    folder_path: str,
    ext_index: Optional[Dict[str, str]] = None,
) -> Optional[FolderAnalysis]:
    """
    单次扫描根目录：统计信息 + 可整理文件列表（不含符号链接文件）。
    """
    folder = Path(folder_path)
    if not folder.exists() or not folder.is_dir():
        return None

    if ext_index is None:
        ext_index = get_default_extension_index()

    root_resolved = folder.resolve()
    all_files: List[Path] = []
    organizable: List[Path] = []
    categorized: List[Path] = []
    file_types: Dict[str, int] = {}
    subdirs: List[str] = []
    total_size = 0
    stat_failed = 0
    symlink_count = 0

    try:
        dir_iter = folder.iterdir()
    except OSError as exc:
        logger.warning("无法列出目录: %s — %s", folder_path, exc)
        return None

    for item in dir_iter:
        try:
            is_directory = item.is_dir()
            is_regular_file = item.is_file()
        except OSError as exc:
            stat_failed += 1
            logger.warning("无法访问目录项，已跳过: %s — %s", item, exc)
            continue

        if is_directory:
            subdirs.append(item.name)
            continue
        if not is_regular_file:
            continue

        all_files.append(item)
        ext = get_file_extension(item)
        file_types[ext] = file_types.get(ext, 0) + 1

        try:
            is_link = item.is_symlink()
        except OSError as exc:
            stat_failed += 1
            logger.warning("无法判断是否为符号链接，已跳过: %s — %s", item, exc)
            continue

        if is_link:
            symlink_count += 1
            try:
                total_size += item.stat().st_size
            except OSError as exc:
                stat_failed += 1
                logger.debug("无法读取符号链接目标大小: %s — %s", item, exc)
            continue

        organizable.append(item)
        try:
            total_size += item.stat().st_size
        except OSError as exc:
            stat_failed += 1
            logger.debug("无法读取文件大小: %s — %s", item, exc)

        if ext_index.get(ext):
            categorized.append(item)

    return FolderAnalysis(
        root_resolved=root_resolved,
        all_files=all_files,
        organizable_files=organizable,
        categorized_files=categorized,
        total_size=total_size,
        file_types=file_types,
        subdirs=subdirs,
        stat_failed=stat_failed,
        symlink_count=symlink_count,
    )


def scan_folder(
    folder_path: str,
    rules: Optional[Dict[str, List[str]]] = None,
    ext_index: Optional[Dict[str, str]] = None,
) -> Tuple[List[Path], List[Path]]:
    """
    扫描文件夹，返回 (根下所有普通文件含链接, 将被归类的非链接文件)。
    """
    if rules is None:
        rules = get_effective_rules()
    if ext_index is None:
        ext_index = build_extension_index(rules)

    analysis = analyze_folder(folder_path, ext_index)
    if analysis is None:
        return [], []
    return analysis.all_files, analysis.categorized_files


def preview_organization(
    folder_path: str,
    rules: Optional[Dict[str, List[str]]] = None,
    ext_index: Optional[Dict[str, str]] = None,
    analysis: Optional[FolderAnalysis] = None,
) -> Tuple[pd.DataFrame, Dict[str, Any]]:
    """
    生成整理预览表；列含相对路径与目标分类文件夹名。
    可传入已缓存的 analysis 避免重复扫描；超大目录按 PREVIEW_BUILD_LIMIT 截断。
    """
    columns = _PREVIEW_COLUMNS
    meta: Dict[str, Any] = {
        "total_rows": 0,
        "dataframe_rows": 0,
        "truncated": False,
    }

    folder = Path(folder_path)
    if rules is None:
        rules = get_effective_rules()
    if ext_index is None:
        ext_index = build_extension_index(rules)

    if not folder.exists() or not folder.is_dir():
        return pd.DataFrame(columns=columns), meta

    if analysis is None:
        analysis = analyze_folder(folder_path, ext_index)
    if analysis is None:
        return pd.DataFrame(columns=columns), meta

    root_r = analysis.root_resolved
    rows: List[Dict[str, str]] = []

    for file_path in analysis.all_files:
        rel = _relative_display_path(file_path, root_r)
        try:
            is_link = file_path.is_symlink()
        except OSError:
            is_link = False
        if is_link:
            rows.append(
                {
                    "文件名": file_path.name,
                    "相对路径": rel,
                    "目标文件夹": "（符号链接，不移动）",
                }
            )
            continue
        ext = get_file_extension(file_path)
        category = ext_index.get(ext)
        if validate_category_name(category):
            target = category
        else:
            target = "—"
        rows.append(
            {
                "文件名": file_path.name,
                "相对路径": rel,
                "目标文件夹": target,
            }
        )

    meta["total_rows"] = len(rows)
    if len(rows) > PREVIEW_BUILD_LIMIT:
        meta["truncated"] = True
        rows = rows[:PREVIEW_BUILD_LIMIT]
    meta["dataframe_rows"] = len(rows)

    return pd.DataFrame(rows, columns=columns), meta


def organize_folder(
    folder_path: str,
    rules: Optional[Dict[str, List[str]]] = None,
    dry_run: bool = False,
) -> OrganizeResult:
    """
    整理指定文件夹中的文件，按规则分类到子文件夹。
    """
    if rules is None:
        rules = get_effective_rules()

    result = OrganizeResult()
    folder = Path(folder_path)
    ext_index = build_extension_index(rules)

    if not folder.exists():
        result.errors.append(f"文件夹不存在: {folder_path}")
        return result

    if not folder.is_dir():
        result.errors.append(f"路径不是文件夹: {folder_path}")
        return result

    ok, vmsg = validate_folder_path(str(folder.resolve()), require_write=not dry_run)
    if not ok:
        result.errors.append(vmsg or "路径无效")
        return result

    analysis = analyze_folder(folder_path, ext_index)
    if analysis is None:
        result.errors.append(f"无法读取文件夹: {folder_path}")
        return result

    root_resolved = analysis.root_resolved
    result.total_files = len(analysis.all_files)

    for category in rules.keys():
        result.categories[category] = 0

    if analysis.stat_failed:
        logger.info(
            "整理目录中有 %s 个文件无法读取大小（已计入统计跳过）",
            analysis.stat_failed,
        )

    for file_path in analysis.categorized_files:
        ext = get_file_extension(file_path)
        category = ext_index.get(ext)
        if category is None or not validate_category_name(category):
            result.skipped_files += 1
            continue

        if dry_run:
            result.moved_files += 1
            result.categories[category] += 1
            continue

        safe_ok, safe_msg = verify_target_category_dir(folder, category)
        if not safe_ok:
            result.errors.append(safe_msg or f"目标不安全: {category}")
            continue

        target_dir = folder / category
        if not ensure_dir_exists(target_dir):
            result.errors.append(f"无法创建目录: {target_dir}")
            continue

        if not is_path_under_root(target_dir.resolve(), root_resolved):
            result.errors.append(
                f"目标目录解析后不在所选文件夹内: {category}，已跳过移动"
            )
            continue

        success, error_msg = safe_move_file(
            file_path,
            target_dir,
            root=root_resolved,
        )
        if success:
            result.moved_files += 1
            result.categories[category] += 1
        else:
            result.errors.append(error_msg or f"移动文件失败: {file_path.name}")

    uncategorized = len(analysis.organizable_files) - len(
        analysis.categorized_files
    )
    not_moved_categorized = len(analysis.categorized_files) - result.moved_files
    result.skipped_files = (
        uncategorized + analysis.symlink_count + not_moved_categorized
    )

    return result


def get_folder_stats(
    folder_path: str,
    rules: Optional[Dict[str, List[str]]] = None,
    ext_index: Optional[Dict[str, str]] = None,
) -> Dict[str, Any]:
    """
    获取文件夹的统计信息（与 analyze_folder 单次扫描一致）。
    """
    if rules is None:
        rules = get_effective_rules()
    if ext_index is None:
        ext_index = build_extension_index(rules)

    analysis = analyze_folder(folder_path, ext_index)
    if analysis is None:
        return {"exists": False, "error": "文件夹不存在"}

    return {
        "exists": True,
        "total_files": len(analysis.all_files),
        "total_size": analysis.total_size,
        "file_types": analysis.file_types,
        "subdirs": analysis.subdirs,
        "stat_failed": analysis.stat_failed,
        "symlink_count": analysis.symlink_count,
    }
