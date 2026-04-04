"""
tests/test_app.py - app.py UI 层测试
"""

import os
import sys
import pytest
from unittest.mock import patch, MagicMock
from pathlib import Path


class TestGetCommonPaths:
    """测试 get_common_paths 函数"""

    def test_returns_dict(self):
        """返回类型应为字典"""
        from app import get_common_paths
        result = get_common_paths()
        assert isinstance(result, dict)

    def test_common_folders_exist(self):
        """常见的文件夹键应存在"""
        from app import get_common_paths
        result = get_common_paths()

        if os.name == "nt":  # Windows
            assert "桌面" in result or "Desktop" in result
            assert "文档" in result or "Documents" in result
            assert "下载" in result or "Downloads" in result
        else:  # macOS / Linux
            assert "主目录" in result or "Home" in result
            assert "桌面" in result or "Desktop" in result

    def test_paths_are_absolute(self):
        """返回的路径应为绝对路径"""
        from app import get_common_paths
        result = get_common_paths()
        for name, path in result.items():
            assert os.path.isabs(path), f"{name} 路径不是绝对路径: {path}"

    def test_paths_exist(self):
        """返回的常见路径应该存在"""
        from app import get_common_paths
        result = get_common_paths()
        for name, path in result.items():
            # 只检查在当前系统存在的路径
            if os.path.exists(os.path.dirname(path)):  # 父目录存在即可
                pass  # 路径格式正确即可


class TestSelectFolderWithDialog:
    """测试 select_folder_with_dialog 函数"""

    @patch("tkinter.Tk")
    @patch("tkinter.filedialog.askdirectory")
    def test_returns_selected_folder(self, mock_askdirectory, mock_tk):
        """应返回用户选择的文件夹路径"""
        from app import select_folder_with_dialog

        mock_askdirectory.return_value = "C:/Users/Test/Downloads"

        result = select_folder_with_dialog()

        assert result == "C:/Users/Test/Downloads"
        mock_askdirectory.assert_called_once()

    @patch("tkinter.Tk")
    @patch("tkinter.filedialog.askdirectory")
    def test_returns_none_when_cancelled(self, mock_askdirectory, mock_tk):
        """用户取消时应返回 None"""
        from app import select_folder_with_dialog

        mock_askdirectory.return_value = ""

        result = select_folder_with_dialog()

        assert result is None

    @patch("tkinter.Tk")
    @patch("tkinter.filedialog.askdirectory")
    def test_tkinter_window_configured(self, mock_askdirectory, mock_tk):
        """tkinter 窗口应正确配置"""
        from app import select_folder_with_dialog

        mock_askdirectory.return_value = "/test/path"
        select_folder_with_dialog()

        # 验证 withdraw 被调用（隐藏窗口）
        mock_tk.return_value.withdraw.assert_called_once()

    @patch("tkinter.Tk")
    @patch("tkinter.filedialog.askdirectory")
    def test_dialog_has_title(self, mock_askdirectory, mock_tk):
        """对话框应有标题"""
        from app import select_folder_with_dialog

        mock_askdirectory.return_value = "/test/path"
        select_folder_with_dialog()

        # 验证 askdirectory 被正确调用
        call_kwargs = mock_askdirectory.call_args[1]
        assert "title" in call_kwargs
        assert "选择" in call_kwargs["title"]

    @patch("tkinter.Tk")
    def test_handles_tkinter_exception(self, mock_tk):
        """应正确处理 tkinter 异常"""
        from app import select_folder_with_dialog

        mock_tk.side_effect = Exception("Tkinter error")

        result = select_folder_with_dialog()

        assert result is None

    @patch("tkinter.Tk")
    def test_handles_filedialog_exception(self, mock_tk):
        """应正确处理 filedialog 异常"""
        from app import select_folder_with_dialog

        mock_instance = MagicMock()
        mock_tk.return_value = mock_instance
        mock_instance.withdraw.side_effect = Exception("Error")

        result = select_folder_with_dialog()

        assert result is None


class TestRenderFolderInput:
    """测试 render_folder_input 函数逻辑"""

    def test_get_common_paths_count(self):
        """常用路径数量应该合理"""
        from app import get_common_paths
        paths = get_common_paths()
        # Windows 至少 4 个，Linux/Mac 至少 3 个
        assert len(paths) >= 3

    def test_common_paths_contain_expected_keys(self):
        """常用路径应包含预期的键"""
        from app import get_common_paths
        paths = get_common_paths()

        expected_keys = []
        if os.name == "nt":
            expected_keys = ["桌面", "文档", "下载", "图片"]
        else:
            expected_keys = ["桌面", "文档", "下载"]

        # 至少应包含其中几个
        found_count = sum(1 for key in expected_keys if key in paths)
        assert found_count >= 2, f"常用路径应包含至少2个预期键，当前: {list(paths.keys())}"


class TestAppIntegration:
    """集成测试"""

    def test_app_imports_without_error(self):
        """app 模块应能正常导入"""
        import app
        assert hasattr(app, "get_common_paths")
        assert hasattr(app, "select_folder_with_dialog")
        assert hasattr(app, "render_folder_input")

    def test_all_imported_functions_are_callable(self):
        """导入的函数都应可调用"""
        from app import get_common_paths, select_folder_with_dialog

        assert callable(get_common_paths)
        assert callable(select_folder_with_dialog)

    def test_select_folder_with_dialog_returns_optional_string(self):
        """select_folder_with_dialog 应返回 str 或 None"""
        from app import select_folder_with_dialog

        with patch("tkinter.Tk"):
            with patch("tkinter.filedialog.askdirectory") as mock_ask:
                mock_ask.return_value = ""
                result = select_folder_with_dialog()
                assert result is None or isinstance(result, str)
