"""
organizer/rules.py - 文件分类规则（从 config.yaml 加载，失败时使用包内 default_rules.yaml）
"""

import logging
import os
import re
import threading
from pathlib import Path

import yaml

logger = logging.getLogger(__name__)

_PACKAGE_DIR = Path(__file__).resolve().parent
_ENV_CONFIG = "FILE_ORGANIZER_CONFIG"

# Windows 文件名非法字符（分类名将用作子文件夹名）
_WIN_INVALID_NAME_CHARS = re.compile(r'[<>:"/\\|?*]')
_WIN_RESERVED_STEMS = frozenset(
    {
        "CON",
        "PRN",
        "AUX",
        "NUL",
        "COM0",
        "COM1",
        "COM2",
        "COM3",
        "COM4",
        "COM5",
        "COM6",
        "COM7",
        "COM8",
        "COM9",
        "LPT0",
        "LPT1",
        "LPT2",
        "LPT3",
        "LPT4",
        "LPT5",
        "LPT6",
        "LPT7",
        "LPT8",
        "LPT9",
    }
)

_effective_rules: dict[str, list[str]] | None = None
_load_identity: tuple[str, ...] | None = None
_DEFAULT_RULES_INDEX: dict[str, str] | None = None
_LAST_RULES_OBJECT_ID: int | None = None
_rules_lock = threading.Lock()


def resolve_config_path(explicit: str | os.PathLike | None = None) -> Path:
    """
    解析配置文件路径：
    1. 参数 explicit
    2. 环境变量 FILE_ORGANIZER_CONFIG
    3. 项目根目录（organizer 的上一级）下的 config.yaml
    """
    if explicit is not None:
        return Path(explicit).expanduser().resolve()
    env = os.environ.get(_ENV_CONFIG)
    if env:
        return Path(env).expanduser().resolve()
    project_root = _PACKAGE_DIR.parent
    return (project_root / "config.yaml").resolve()


def _try_load_rules_from_file(path: Path) -> dict[str, list[str]] | None:
    if not path.is_file():
        return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
    except OSError as exc:
        logger.warning("无法读取配置文件: %s — %s", path, exc)
        return None
    except yaml.YAMLError as exc:
        logger.warning("YAML 解析失败: %s — %s", path, exc)
        return None

    if not isinstance(data, dict):
        return None
    raw = data.get("rules")
    if not isinstance(raw, dict):
        return None
    try:
        return load_rules_from_dict(raw)
    except ValueError as exc:
        logger.warning("rules 校验失败（%s）: %s", path, exc)
        return None


def _current_load_identity() -> tuple[str, ...]:
    """用于判断是否需要重新加载（路径 + mtime）。"""
    user = resolve_config_path()
    if user.is_file():
        try:
            return (
                "user",
                str(user.resolve()),
                user.stat().st_mtime,
            )
        except OSError:
            pass
    builtin = _PACKAGE_DIR / "default_rules.yaml"
    if builtin.is_file():
        try:
            return (
                "builtin",
                str(builtin.resolve()),
                builtin.stat().st_mtime,
            )
        except OSError:
            pass
    return ("empty", "", 0.0)


def reload_rules() -> None:
    """清除缓存，下次访问时重新读取 YAML。"""
    global _effective_rules, _load_identity, _DEFAULT_RULES_INDEX, _LAST_RULES_OBJECT_ID
    _effective_rules = None
    _load_identity = None
    _DEFAULT_RULES_INDEX = None
    _LAST_RULES_OBJECT_ID = None


def get_effective_rules(
    config_path: str | os.PathLike | None = None,
    *,
    force_reload: bool = False,
) -> dict[str, list[str]]:
    """
    返回当前生效的分类规则（字典不可变请视为只读；修改请改 YAML 后 reload_rules）。

    优先加载项目 config.yaml；不存在或 rules 无效时使用包内 default_rules.yaml。

    线程安全：使用锁保护全局缓存的读写操作。
    """
    global _effective_rules, _load_identity

    if config_path is not None:
        path = Path(config_path).expanduser().resolve()
        rules = _try_load_rules_from_file(path)
        if rules is None:
            builtin = _PACKAGE_DIR / "default_rules.yaml"
            rules = _try_load_rules_from_file(builtin) if builtin.is_file() else {}
            if not rules:
                logger.error("指定配置无效且内置默认不可用: %s", path)
        return rules

    ident = _current_load_identity()

    # 先检查缓存（快速路径，无需加锁）
    if (
        not force_reload
        and _effective_rules is not None
        and ident == _load_identity
    ):
        return _effective_rules

    # 缓存未命中或需要重载，加锁访问
    with _rules_lock:
        # 双检查（其他线程可能已更新）
        if (
            not force_reload
            and _effective_rules is not None
            and ident == _load_identity
        ):
            return _effective_rules

        user = resolve_config_path()
        rules: dict[str, list[str]] | None = None
        if user.is_file():
            rules = _try_load_rules_from_file(user)

        if rules is None:
            builtin = _PACKAGE_DIR / "default_rules.yaml"
            rules = _try_load_rules_from_file(builtin)
            if rules is None:
                logger.error("未找到有效规则（请检查 config.yaml 与 default_rules.yaml）")
                rules = {}

        _effective_rules = rules
        _load_identity = ident
        _invalidate_extension_index_cache()
        return _effective_rules


def _invalidate_extension_index_cache() -> None:
    global _DEFAULT_RULES_INDEX, _LAST_RULES_OBJECT_ID
    _DEFAULT_RULES_INDEX = None
    _LAST_RULES_OBJECT_ID = None


def __getattr__(name: str) -> object:
    """兼容 `from organizer.rules import DEFAULT_RULES`。"""
    if name == "DEFAULT_RULES":
        return get_effective_rules()
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


def validate_category_name(name: str) -> bool:
    """
    校验分类名可否安全用作根目录下的子文件夹名。
    """
    if not isinstance(name, str) or not name.strip():
        return False
    if name.strip() != name:
        return False
    if ".." in name or "/" in name or "\\" in name:
        return False
    if name in (".", ".."):
        return False
    if os.name == "nt" and _WIN_INVALID_NAME_CHARS.search(name):
        return False
    if os.name == "nt":
        stem = name.split(".", 1)[0].upper()
        if stem in _WIN_RESERVED_STEMS:
            return False
    if len(name) > 200:
        return False
    return True


def build_extension_index(rules: dict[str, list[str]]) -> dict[str, str]:
    """
    将规则表预处理为「扩展名(小写, 带点) -> 分类名」映射。
    """
    index: dict[str, str] = {}
    for category, extensions in rules.items():
        if not validate_category_name(category):
            continue
        for ext in extensions:
            if not isinstance(ext, str):
                continue
            e = ext.strip().lower()
            if not e.startswith("."):
                e = "." + e
            index.setdefault(e, category)
    return index


def get_default_extension_index() -> dict[str, str]:
    """基于当前生效规则的扩展名索引（带缓存，线程安全）。"""
    global _DEFAULT_RULES_INDEX, _LAST_RULES_OBJECT_ID
    rules = get_effective_rules()
    rid = id(rules)
    # 缓存命中检查（无需加锁，只读操作）
    if _DEFAULT_RULES_INDEX is not None and _LAST_RULES_OBJECT_ID == rid:
        return _DEFAULT_RULES_INDEX
    # 缓存未命中，加锁更新
    with _rules_lock:
        # 双检查
        if _DEFAULT_RULES_INDEX is not None and _LAST_RULES_OBJECT_ID == rid:
            return _DEFAULT_RULES_INDEX
        _DEFAULT_RULES_INDEX = build_extension_index(rules)
        _LAST_RULES_OBJECT_ID = rid
    return _DEFAULT_RULES_INDEX


def get_all_extensions() -> list[str]:
    """获取当前规则中所有扩展名。"""
    extensions = set()
    for ext_list in get_effective_rules().values():
        extensions.update(ext_list)
    return sorted(extensions)


def get_category_for_extension(ext: str) -> str:
    """
    根据扩展名查找分类；未找到返回 "others"。
    """
    if not ext.startswith("."):
        ext = "." + ext
    ext = ext.lower()
    idx = get_default_extension_index()
    return idx.get(ext, "others")


def load_rules_from_dict(rules_dict: dict[str, list[str]]) -> dict[str, list[str]]:
    """
    验证并规范化用户自定义规则。

    Raises:
        ValueError: 如果规则格式不正确
    """
    if not isinstance(rules_dict, dict):
        raise ValueError("规则必须是字典类型")

    normalized_rules: dict[str, list[str]] = {}
    for category, extensions in rules_dict.items():
        if not isinstance(category, str):
            raise ValueError(f"分类名称必须是字符串: {category}")
        if not validate_category_name(category):
            raise ValueError(
                f"分类名称不安全或非法（含路径字符等）: {category!r}"
            )

        if not isinstance(extensions, (list, tuple)):
            raise ValueError(f"分类 '{category}' 的扩展名必须是列表")

        normalized_exts: list[str] = []
        for ext in extensions:
            if not isinstance(ext, str):
                raise ValueError(f"扩展名必须是字符串: {ext}")
            ext = ext.strip().lower()
            if not ext.startswith("."):
                ext = "." + ext
            normalized_exts.append(ext)

        normalized_rules[category] = normalized_exts

    return normalized_rules


def merge_rules(
    base_rules: dict[str, list[str]],
    custom_rules: dict[str, list[str]],
) -> dict[str, list[str]]:
    """
    合并自定义规则到基础规则中（深拷贝，不修改原始数据）。
    """
    # 深拷贝：每个分类的扩展名列表也创建新列表
    merged = {k: list(v) for k, v in base_rules.items()}

    for category, extensions in custom_rules.items():
        if not validate_category_name(category):
            raise ValueError(f"合并规则中存在非法分类名: {category!r}")
        if category in merged:
            existing = set(merged[category])
            new_exts = [e for e in extensions if e.lower() not in existing]
            merged[category].extend(new_exts)
        else:
            merged[category] = list(extensions)

    return merged
