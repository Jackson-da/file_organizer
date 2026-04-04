"""
tests/test_utils.py - 工具模块单元测试
"""

import os
import tempfile
import pytest
import shutil
from pathlib import Path
from unittest.mock import patch, MagicMock

from organizer.utils import (
    get_file_extension,
    ensure_dir_exists,
    safe_move_file,
    copy_file,
    format_file_size,
    load_config,
    save_config,
    is_hidden_file,
    validate_folder_path
)


# ============================================================================
# 测试 get_file_extension
# ============================================================================

class TestGetFileExtension:
    """测试 get_file_extension 函数"""

    def test_common_extensions(self, temp_dir):
        """测试常见扩展名"""
        assert get_file_extension(temp_dir / 'file.jpg') == '.jpg'
        assert get_file_extension(temp_dir / 'file.pdf') == '.pdf'
        assert get_file_extension(temp_dir / 'file.mp4') == '.mp4'

    def test_multiple_dots(self, temp_dir):
        """测试多个点号的文件名"""
        assert get_file_extension(temp_dir / 'file.backup.jpg') == '.jpg'
        assert get_file_extension(temp_dir / 'my.document.pdf') == '.pdf'

    def test_no_extension(self, temp_dir):
        """测试无扩展名"""
        assert get_file_extension(temp_dir / 'filename') == ''

    def test_case_insensitive(self, temp_dir):
        """测试大小写"""
        assert get_file_extension(temp_dir / 'file.JPG') == '.jpg'
        assert get_file_extension(temp_dir / 'file.PDF') == '.pdf'

    def test_hidden_file(self, temp_dir):
        """测试隐藏文件"""
        assert get_file_extension(temp_dir / '.gitignore') == ''


# ============================================================================
# 测试 ensure_dir_exists
# ============================================================================

class TestEnsureDirExists:
    """测试 ensure_dir_exists 函数"""

    def test_creates_new_directory(self, temp_dir):
        """测试创建新目录"""
        new_dir = temp_dir / 'new_subdir'
        result = ensure_dir_exists(new_dir)
        assert result is True
        assert new_dir.exists()
        assert new_dir.is_dir()

    def test_nested_directories(self, temp_dir):
        """测试创建嵌套目录"""
        nested_dir = temp_dir / 'level1' / 'level2' / 'level3'
        result = ensure_dir_exists(nested_dir)
        assert result is True
        assert nested_dir.exists()

    def test_existing_directory(self, temp_dir):
        """测试已存在的目录"""
        result = ensure_dir_exists(temp_dir)
        assert result is True
        assert temp_dir.exists()

    def test_creates_with_special_chars(self, temp_dir):
        """测试创建带特殊字符的目录"""
        special_dir = temp_dir / '目录测试' / '特殊@字符'
        result = ensure_dir_exists(special_dir)
        assert result is True
        assert special_dir.exists()


# ============================================================================
# 测试 safe_move_file
# ============================================================================

class TestSafeMoveFile:
    """测试 safe_move_file 函数"""

    def test_basic_move(self, temp_dir):
        """测试基本移动"""
        source = temp_dir / 'source.txt'
        source.write_text('content')
        target_dir = temp_dir / 'target'

        success, error = safe_move_file(source, target_dir)
        assert success is True
        assert error is None
        assert not source.exists()
        assert (target_dir / 'source.txt').exists()

    def test_move_to_existing_dir(self, temp_dir):
        """测试移动到已存在的目录"""
        source = temp_dir / 'file.txt'
        source.write_text('content')
        target_dir = temp_dir / 'existing'
        target_dir.mkdir()

        success, error = safe_move_file(source, target_dir)
        assert success is True
        assert (target_dir / 'file.txt').exists()

    def test_filename_conflict_rename(self, temp_dir):
        """测试文件名冲突时自动重命名"""
        source = temp_dir / 'file.txt'
        source.write_text('new content')
        target_dir = temp_dir / 'target'
        target_dir.mkdir()
        (target_dir / 'file.txt').write_text('existing content')

        success, error = safe_move_file(source, target_dir)
        assert success is True
        assert not source.exists()
        assert (target_dir / 'file.txt').exists()
        assert (target_dir / 'file_1.txt').exists()

    def test_overwrite_existing(self, temp_dir):
        """测试覆盖已存在文件"""
        source = temp_dir / 'file.txt'
        source.write_text('new content')
        target_dir = temp_dir / 'target'
        target_dir.mkdir()
        target_file = target_dir / 'file.txt'
        target_file.write_text('old content')

        success, error = safe_move_file(source, target_dir, overwrite=True)
        assert success is True
        assert target_file.read_text() == 'new content'

    def test_move_nonexistent_file(self, temp_dir):
        """测试移动不存在的文件"""
        source = temp_dir / 'nonexistent.txt'
        target_dir = temp_dir / 'target'

        success, error = safe_move_file(source, target_dir)
        assert success is False
        assert error is not None
        assert '不存在' in error

    def test_unicode_filename(self, temp_dir):
        """测试 Unicode 文件名"""
        source = temp_dir / '文件.txt'
        source.write_text('content', encoding='utf-8')
        target_dir = temp_dir / 'target'

        success, error = safe_move_file(source, target_dir)
        assert success is True
        assert (target_dir / '文件.txt').exists()


# ============================================================================
# 测试 copy_file
# ============================================================================

class TestCopyFile:
    """测试 copy_file 函数"""

    def test_basic_copy(self, temp_dir):
        """测试基本复制"""
        source = temp_dir / 'source.txt'
        source.write_text('content')
        target_dir = temp_dir / 'target'

        success, error = copy_file(source, target_dir)
        assert success is True
        assert source.exists()  # 源文件保留
        assert (target_dir / 'source.txt').exists()
        assert (target_dir / 'source.txt').read_text() == 'content'

    def test_preserves_metadata(self, temp_dir):
        """测试保留元数据"""
        source = temp_dir / 'file.txt'
        source.write_text('content')
        original_mtime = source.stat().st_mtime

        target_dir = temp_dir / 'target'
        copy_file(source, target_dir)
        copied = target_dir / 'file.txt'
        assert abs(copied.stat().st_mtime - original_mtime) < 1


# ============================================================================
# 测试 format_file_size
# ============================================================================

class TestFormatFileSize:
    """测试 format_file_size 函数"""

    def test_bytes(self):
        """测试字节"""
        assert format_file_size(0) == "0 B"
        assert format_file_size(100) == "100 B"
        assert format_file_size(1023) == "1023 B"

    def test_kilobytes(self):
        """测试千字节"""
        assert "KB" in format_file_size(1024)
        assert "KB" in format_file_size(2048)
        assert "1.0 KB" == format_file_size(1024)

    def test_megabytes(self):
        """测试兆字节"""
        assert "MB" in format_file_size(1024 ** 2)
        assert "1.0 MB" == format_file_size(1024 ** 2)

    def test_gigabytes(self):
        """测试吉字节"""
        assert "GB" in format_file_size(1024 ** 3)
        assert "GB" in format_file_size(2 * 1024 ** 3)


# ============================================================================
# 测试 validate_folder_path
# ============================================================================

class TestValidateFolderPath:
    """测试 validate_folder_path 函数"""

    def test_valid_folder(self, temp_dir):
        """测试有效文件夹"""
        valid, error = validate_folder_path(str(temp_dir))
        assert valid is True
        assert error is None

    def test_nonexistent_folder(self):
        """测试不存在的文件夹"""
        valid, error = validate_folder_path('/nonexistent/path/xyz')
        assert valid is False
        assert '不存在' in error

    def test_path_is_file(self, temp_dir):
        """测试路径是文件而非文件夹"""
        file_path = temp_dir / 'file.txt'
        file_path.write_text('content')

        valid, error = validate_folder_path(str(file_path))
        assert valid is False
        assert '不是文件夹' in error


# ============================================================================
# 测试 is_hidden_file
# ============================================================================

class TestIsHiddenFile:
    """测试 is_hidden_file 函数"""

    def test_regular_file(self, temp_dir):
        """测试普通文件"""
        file_path = temp_dir / 'visible.txt'
        file_path.touch()
        result = is_hidden_file(file_path)
        assert result is False

    def test_hidden_file_unix(self, temp_dir):
        """测试 Unix 隐藏文件"""
        file_path = temp_dir / '.hidden'
        file_path.touch()
        result = is_hidden_file(file_path)
        assert result is True


# ============================================================================
# 测试配置文件操作
# ============================================================================

class TestConfigOperations:
    """测试配置文件操作"""

    def test_save_and_load_config(self, temp_dir):
        """测试保存和加载配置"""
        config = {
            'rules': {
                'images': ['.jpg', '.png'],
                'documents': ['.pdf']
            },
            'settings': {
                'overwrite': False
            }
        }
        config_path = temp_dir / 'config.yaml'

        save_result = save_config(config, str(config_path))
        assert save_result is True
        assert config_path.exists()

        data, err = load_config(str(config_path))
        assert err is None
        assert data is not None
        assert 'rules' in data
        assert data['rules']['images'] == ['.jpg', '.png']

    def test_load_nonexistent_config(self, temp_dir):
        """测试加载不存在的配置文件"""
        data, err = load_config(str(temp_dir / 'nonexistent.yaml'))
        assert data is None
        assert err is not None
        assert '不存在' in err

    def test_load_invalid_yaml(self, temp_dir):
        """测试加载无效 YAML"""
        invalid_file = temp_dir / 'invalid.yaml'
        invalid_file.write_text("invalid: yaml: content: [")

        data, err = load_config(str(invalid_file))
        assert data is None
        assert err is not None


# ============================================================================
# 边界情况测试
# ============================================================================

class TestUtilsEdgeCases:
    """工具模块边界情况测试"""

    def test_move_file_with_long_path(self, temp_dir):
        """测试移动长路径文件"""
        long_name = 'a' * 200 + '.txt'
        source = temp_dir / long_name
        source.write_text('content')
        target_dir = temp_dir / 'target'

        success, error = safe_move_file(source, target_dir)
        assert success is True or (error is not None and len(error) > 0)

    def test_move_file_with_special_chars(self, temp_dir):
        """测试移动带特殊字符的文件"""
        special_names = [
            'file with spaces.txt',
            'file-with-dashes.txt',
            'file_with_underscores.txt',
        ]

        for name in special_names:
            source = temp_dir / name
            source.write_text('content')
            target_dir = temp_dir / 'target'
            safe_move_file(source, target_dir)

    def test_format_size_large_numbers(self):
        """测试格式化大数字"""
        assert 'GB' in format_file_size(10 ** 12)
        assert 'MB' in format_file_size(1024 * 1024)


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
