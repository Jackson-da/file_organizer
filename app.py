"""
app.py - Streamlit 文件整理工具 Web 界面
"""

import logging
import os
from pathlib import Path
from typing import Any, Dict, Optional

import streamlit as st

from organizer import (
    FolderAnalysis,
    analyze_folder,
    format_file_size,
    get_default_extension_index,
    get_effective_rules,
    organize_folder,
    preview_organization,
    resolve_config_path,
    validate_folder_path,
)

logger = logging.getLogger(__name__)


def _paths_equal(a: str, b: str) -> bool:
    return os.path.normcase(os.path.normpath(a)) == os.path.normcase(
        os.path.normpath(b)
    )


def _folder_analysis_cache_key(folder_path: str) -> Optional[tuple]:
    try:
        p = Path(folder_path)
        if not p.is_dir():
            return None
        return (
            os.path.normcase(os.path.normpath(str(p.resolve()))),
            p.stat().st_mtime,
        )
    except OSError:
        return None


def get_cached_folder_analysis(
    folder_path: str,
    ext_index: Dict[str, str],
    session_state: Any,
) -> Optional[FolderAnalysis]:
    """按路径+mtime 缓存扫描结果，避免同页重复 iterdir。"""
    key = _folder_analysis_cache_key(folder_path)
    if key is None:
        return None
    ent = session_state.get("_folder_analysis_cache")
    if ent and ent.get("key") == key:
        return ent.get("analysis")
    analysis = analyze_folder(folder_path, ext_index)
    session_state["_folder_analysis_cache"] = {"key": key, "analysis": analysis}
    return analysis


# 页面配置
st.set_page_config(
    page_title="文件整理工具",
    page_icon="📁",
    layout="wide",
)


def init_session_state():
    """初始化会话状态（使用 setdefault 一次性设置默认值）"""
    defaults = {
        "last_result": None,
        "current_folder": None,
        "scan_results": None,
        "preview_df": None,
        "preview_source_folder": None,
        "preview_meta": None,
        "preview_generation": 0,
    }
    for key, value in defaults.items():
        st.session_state.setdefault(key, value)


def render_header():
    """渲染页面头部"""
    st.title("📁 本地文件整理工具")
    st.markdown("---")


def get_common_paths():
    """获取常用文件夹路径"""
    common = {}
    if os.name == "nt":
        common["桌面"] = os.path.join(os.path.expanduser("~"), "Desktop")
        common["文档"] = os.path.join(os.path.expanduser("~"), "Documents")
        common["下载"] = os.path.join(os.path.expanduser("~"), "Downloads")
        common["图片"] = os.path.join(os.path.expanduser("~"), "Pictures")
    else:
        common["主目录"] = os.path.expanduser("~")
        common["桌面"] = os.path.join(os.path.expanduser("~"), "Desktop")
        common["文档"] = os.path.join(os.path.expanduser("~"), "Documents")
        common["下载"] = os.path.join(os.path.expanduser("~"), "Downloads")
    return common


def select_folder_with_dialog() -> Optional[str]:
    """
    使用 tkinter 系统文件对话框选择文件夹。
    注意：仅在本地运行时有效，远程部署时不可用。
    """
    try:
        import tkinter as tk
        from tkinter import filedialog

        root = tk.Tk()
        root.withdraw()
        root.attributes("-topmost", True)
        folder = filedialog.askdirectory(title="选择要整理的文件夹")
        root.destroy()
        return folder if folder else None
    except Exception:
        logger.warning("打开文件夹选择器失败，请检查 tkinter 是否可用")
        return None


def render_folder_input() -> Optional[str]:
    """渲染文件夹输入区域"""
    common_paths = get_common_paths()

    st.subheader("📂 选择文件夹")

    # 快捷路径按钮 + 文件选择器
    cols = st.columns(len(common_paths) + 1)
    selected_common = None

    for i, (name, path) in enumerate(common_paths.items()):
        with cols[i]:
            if os.path.exists(path):
                if st.button(
                    f"📁 {name}",
                    use_container_width=True,
                    key=f"btn_{name}",
                ):
                    selected_common = path

    # 文件选择器按钮
    with cols[len(common_paths)]:
        if st.button(
            "📂 浏览...",
            use_container_width=True,
            key="btn_browse",
            help="点击打开系统文件管理器选择文件夹（仅本地运行有效）",
        ):
            folder = select_folder_with_dialog()
            if folder:
                return folder

    # 自定义路径输入
    folder_path = st.text_input(
        "📝 或输入自定义路径",
        placeholder=r"输入文件夹完整路径，如 C:\Users\YourName\Downloads",
        help="输入要整理的文件所在的文件夹路径",
    )

    if selected_common:
        return selected_common

    return folder_path if folder_path else None


def render_preview(folder_path: str):
    """渲染文件预览区域"""
    valid, error_msg = validate_folder_path(folder_path)

    if not valid:
        st.error(f"❌ {error_msg}")
        return

    st.session_state.current_folder = folder_path

    psf = st.session_state.preview_source_folder
    if psf is not None and not _paths_equal(psf, folder_path):
        st.session_state.preview_df = None
        st.session_state.preview_source_folder = None
        st.session_state.preview_meta = None

    ext_index = get_default_extension_index()
    analysis = get_cached_folder_analysis(
        folder_path,
        ext_index,
        st.session_state,
    )
    if analysis is None:
        st.error("❌ 无法列出文件夹内容，请检查路径与权限。")
        return

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric("📄 文件总数", len(analysis.all_files))

    with col2:
        st.metric("💾 文件总大小", format_file_size(analysis.total_size))

    with col3:
        st.metric("📂 子文件夹", len(analysis.subdirs))

    with col4:
        st.metric("📊 文件类型", len(analysis.file_types))

    if analysis.stat_failed:
        st.caption(
            f"⚠️ 有 {analysis.stat_failed} 个文件无法读取大小（已排除在总大小外）。"
        )
    if analysis.symlink_count:
        st.caption(
            f"ℹ️ 检测到 {analysis.symlink_count} 个符号链接文件，不参与移动整理。"
        )

    st.markdown("---")

    st.session_state.scan_results = {
        "all": analysis.all_files,
        "categorized": analysis.categorized_files,
    }

    st.subheader("📋 扫描预览")

    col1, col2 = st.columns(2)
    with col1:
        st.info(f"📄 检测到 {len(analysis.all_files)} 个文件")
    with col2:
        st.success(f"✅ 将整理 {len(analysis.categorized_files)} 个文件")

    if analysis.file_types:
        st.subheader("📊 文件类型分布")
        file_types = analysis.file_types
        sorted_types = sorted(
            file_types.items(),
            key=lambda x: x[1],
            reverse=True,
        )

        type_data = [
            {"扩展名": ext or "(无)", "数量": count}
            for ext, count in sorted_types
        ]
        st.table(type_data[:15])


def render_actions():
    """渲染操作按钮区域：预览 → 表格 → 确认整理"""
    st.markdown("---")
    st.subheader("⚙️ 整理操作")

    col_prev, col_confirm = st.columns(2)

    with col_prev:
        if st.button("🔍 预览", use_container_width=True):
            if st.session_state.current_folder:
                try:
                    with st.spinner("正在生成预览..."):
                        ext_index = get_default_extension_index()
                        cache = st.session_state.get("_folder_analysis_cache")
                        key = _folder_analysis_cache_key(
                            st.session_state.current_folder,
                        )
                        analysis = None
                        if (
                            cache
                            and cache.get("key") == key
                            and key is not None
                        ):
                            analysis = cache.get("analysis")
                        df, meta = preview_organization(
                            st.session_state.current_folder,
                            ext_index=ext_index,
                            analysis=analysis,
                        )
                        st.session_state.preview_df = df
                        st.session_state.preview_meta = meta
                        st.session_state.preview_source_folder = (
                            st.session_state.current_folder
                        )
                        st.session_state.preview_generation = (
                            st.session_state.get("preview_generation", 0) + 1
                        )
                    st.rerun()
                except Exception:
                    logger.exception("生成预览失败")
                    st.error("生成预览时发生意外错误，请查看日志或稍后重试。")
            else:
                st.warning("请先选择一个文件夹")

    with col_confirm:
        if st.button("✅ 确认整理", type="primary", use_container_width=True):
            if not st.session_state.current_folder:
                st.warning("请先选择一个文件夹")
            elif st.session_state.preview_df is None:
                st.warning("请先点击「预览」查看整理计划，再确认执行。")
            elif not _paths_equal(
                st.session_state.preview_source_folder,
                st.session_state.current_folder,
            ):
                st.warning("当前文件夹与预览时不一致，请重新点击「预览」。")
            else:
                try:
                    with st.spinner("正在移动文件..."):
                        result = organize_folder(
                            st.session_state.current_folder,
                            dry_run=False,
                        )
                        st.session_state.last_result = result
                        st.session_state.preview_df = None
                        st.session_state.preview_source_folder = None
                        st.session_state.preview_meta = None
                    st.rerun()
                except Exception:
                    logger.exception("整理文件失败")
                    st.error("整理过程中发生意外错误，请查看日志；部分文件可能已移动。")

    if st.session_state.preview_df is not None and not st.session_state.preview_df.empty:
        st.subheader("📋 整理预览")
        df = st.session_state.preview_df
        total = len(df)
        gen = st.session_state.get("preview_generation", 0)

        ctrl1, ctrl2 = st.columns(2)
        with ctrl1:
            page_size = st.selectbox(
                "每页行数",
                options=[25, 50, 100, 200],
                index=1,
                key=f"preview_ps_{gen}",
            )
        n_pages = max(1, (total + page_size - 1) // page_size)
        with ctrl2:
            page = st.number_input(
                "页码",
                min_value=1,
                max_value=n_pages,
                value=1,
                step=1,
                key=f"preview_pg_{gen}",
            )

        start = (int(page) - 1) * int(page_size)
        end = min(start + int(page_size), total)
        chunk = df.iloc[start:end]

        st.dataframe(
            chunk,
            use_container_width=True,
            hide_index=True,
        )
        st.caption(
            f"本页第 {start + 1}–{end} 条，共 {total} 条（第 {int(page)}/{n_pages} 页）。"
        )

        pm = st.session_state.preview_meta or {}
        if pm.get("truncated"):
            st.caption(
                f"预览数据仅包含前 {pm.get('dataframe_rows', 0)} 行（共扫描到 "
                f"{pm.get('total_rows', 0)} 个文件）；实际「确认整理」仍处理目录内全部可整理文件。"
            )
        st.caption(
            "「相对路径」相对于所选文件夹；「目标文件夹」为将归入的子文件夹名；"
            "「—」表示不在规则内；「（符号链接，不移动）」表示不移动。"
        )
    elif st.session_state.preview_df is not None and st.session_state.preview_df.empty:
        st.info("当前文件夹根目录下没有可扫描的文件，无需整理。")

    if st.session_state.last_result:
        render_result(st.session_state.last_result)


def render_result(result):
    """渲染整理结果"""
    st.markdown("---")
    st.subheader("📊 整理结果")

    if not result.errors:
        st.success("✅ 文件整理完成！")
    else:
        st.warning(f"⚠️ 完成，但有 {len(result.errors)} 个错误")

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric("处理文件", result.total_files)

    with col2:
        st.metric("已移动", result.moved_files)

    with col3:
        st.metric("已跳过", result.skipped_files)

    with col4:
        st.metric("错误数", len(result.errors))

    if result.categories:
        st.subheader("📁 分类统计")

        non_zero_categories = {
            k: v for k, v in result.categories.items() if v > 0
        }

        if non_zero_categories:
            sorted_categories = sorted(
                non_zero_categories.items(),
                key=lambda x: x[1],
                reverse=True,
            )

            category_data = [
                {"分类": cat, "文件数": count}
                for cat, count in sorted_categories
            ]
            st.table(category_data)

    if result.errors:
        st.subheader("❌ 错误详情")
        for error in result.errors:
            st.error(error)


def render_rules_help():
    """渲染规则说明"""
    with st.expander("📖 查看分类规则"):
        st.markdown("### 当前分类规则")
        cfg = resolve_config_path()
        st.caption(
            f"规则来源：优先 `{cfg}`；无效时使用包内 `default_rules.yaml`。"
            " 环境变量 `FILE_ORGANIZER_CONFIG` 可指定其它配置文件路径。"
        )

        for category, extensions in get_effective_rules().items():
            with st.expander(f"📁 {category}"):
                st.write(", ".join(extensions))


def render_config_section():
    """渲染配置说明"""
    with st.expander("⚙️ 自定义配置"):
        st.markdown(
            """
        ### 自定义规则

        你可以通过创建 `config.yaml` 文件来自定义分类规则：

        ```yaml
        rules:
          images:
            - .jpg
            - .png
          documents:
            - .pdf
            - .docx
        ```

        **说明**: 编辑项目根目录的 `config.yaml` 中的 `rules` 后，重新运行应用即可生效。
        """
        )


def main():
    """主函数"""
    logging.basicConfig(
        level=logging.WARNING,
        format="%(levelname)s %(name)s: %(message)s",
    )
    init_session_state()
    render_header()

    folder_path = render_folder_input()

    if folder_path and os.path.exists(folder_path) and os.path.isdir(folder_path):
        render_preview(folder_path)

    render_actions()

    st.markdown("---")
    col1, col2 = st.columns(2)
    with col1:
        render_rules_help()
    with col2:
        render_config_section()

    st.markdown("---")
    st.caption("📁 文件整理工具 v1.0.0 | 使用 Streamlit 构建")


if __name__ == "__main__":
    main()
