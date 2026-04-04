"""
organizer - 本地文件整理工具包
"""

from .core import (
    FolderAnalysis,
    OrganizeResult,
    PREVIEW_BUILD_LIMIT,
    analyze_folder,
    categorize_file,
    get_folder_stats,
    organize_folder,
    preview_organization,
    scan_folder,
)
from .rules import (
    DEFAULT_RULES,
    build_extension_index,
    get_all_extensions,
    get_category_for_extension,
    get_default_extension_index,
    get_effective_rules,
    load_rules_from_dict,
    merge_rules,
    reload_rules,
    resolve_config_path,
    validate_category_name,
)
from .utils import (
    copy_file,
    ensure_dir_exists,
    format_file_size,
    get_file_extension,
    is_path_under_root,
    load_config,
    save_config,
    safe_move_file,
    validate_folder_path,
    verify_target_category_dir,
)

__version__ = "1.0.0"
__all__ = [
    "FolderAnalysis",
    "OrganizeResult",
    "PREVIEW_BUILD_LIMIT",
    "analyze_folder",
    "categorize_file",
    "scan_folder",
    "preview_organization",
    "organize_folder",
    "get_folder_stats",
    "DEFAULT_RULES",
    "build_extension_index",
    "get_default_extension_index",
    "get_effective_rules",
    "reload_rules",
    "resolve_config_path",
    "get_all_extensions",
    "get_category_for_extension",
    "load_rules_from_dict",
    "merge_rules",
    "validate_category_name",
    "get_file_extension",
    "ensure_dir_exists",
    "safe_move_file",
    "copy_file",
    "format_file_size",
    "load_config",
    "save_config",
    "validate_folder_path",
    "is_path_under_root",
    "verify_target_category_dir",
]
