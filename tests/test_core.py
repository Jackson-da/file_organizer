"""
tests/test_core.py - 核心模块单元测试
"""

import pytest
import shutil
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

from organizer.core import (
    OrganizeResult,
    categorize_file,
    scan_folder,
    organize_folder,
    get_folder_stats
)
from organizer.rules import DEFAULT_RULES


# ============================================================================
# 测试 categorize_file
# ============================================================================

class TestCategorizeFile:
    """测试 categorize_file 函数"""

    def test_categorize_jpg_image(self):
        """测试 JPG 图片分类"""
        assert categorize_file('.jpg', DEFAULT_RULES) == 'images'
        assert categorize_file('.JPG', DEFAULT_RULES) == 'images'
        assert categorize_file('.jpeg', DEFAULT_RULES) == 'images'

    def test_categorize_pdf_document(self):
        """测试 PDF 文档分类"""
        assert categorize_file('.pdf', DEFAULT_RULES) == 'documents'
        assert categorize_file('.PDF', DEFAULT_RULES) == 'documents'

    def test_categorize_mp4_video(self):
        """测试 MP4 视频分类"""
        assert categorize_file('.mp4', DEFAULT_RULES) == 'videos'
        assert categorize_file('.mkv', DEFAULT_RULES) == 'videos'

    def test_categorize_mp3_audio(self):
        """测试 MP3 音频分类"""
        assert categorize_file('.mp3', DEFAULT_RULES) == 'audio'
        assert categorize_file('.wav', DEFAULT_RULES) == 'audio'

    def test_categorize_zip_archive(self):
        """测试 ZIP 压缩包分类"""
        assert categorize_file('.zip', DEFAULT_RULES) == 'archives'
        assert categorize_file('.rar', DEFAULT_RULES) == 'archives'
        assert categorize_file('.7z', DEFAULT_RULES) == 'archives'

    def test_categorize_py_code(self):
        """测试 Python 代码分类"""
        assert categorize_file('.py', DEFAULT_RULES) == 'code'
        assert categorize_file('.js', DEFAULT_RULES) == 'code'

    def test_categorize_executables(self):
        """测试可执行文件分类"""
        assert categorize_file('.exe', DEFAULT_RULES) == 'executables'
        assert categorize_file('.msi', DEFAULT_RULES) == 'executables'
        assert categorize_file('.dll', DEFAULT_RULES) == 'executables'

    def test_categorize_fonts(self):
        """测试字体文件分类"""
        assert categorize_file('.ttf', DEFAULT_RULES) == 'fonts'
        assert categorize_file('.otf', DEFAULT_RULES) == 'fonts'
        assert categorize_file('.woff', DEFAULT_RULES) == 'fonts'

    def test_categorize_3d_models(self):
        """测试 3D 模型分类"""
        assert categorize_file('.obj', DEFAULT_RULES) == '3d_models'
        assert categorize_file('.fbx', DEFAULT_RULES) == '3d_models'
        assert categorize_file('.stl', DEFAULT_RULES) == '3d_models'

    def test_categorize_design_files(self):
        """测试设计文件分类"""
        assert categorize_file('.ai', DEFAULT_RULES) == 'design'
        assert categorize_file('.sketch', DEFAULT_RULES) == 'design'
        assert categorize_file('.fig', DEFAULT_RULES) == 'design'
        assert categorize_file('.xd', DEFAULT_RULES) == 'design'
        assert categorize_file('.psd', DEFAULT_RULES) in ('images', 'design')

    def test_categorize_unknown_extension(self):
        """测试未知扩展名返回 None"""
        assert categorize_file('.xyz', DEFAULT_RULES) is None
        assert categorize_file('.unknown', DEFAULT_RULES) is None
        assert categorize_file('.123', DEFAULT_RULES) is None

    def test_categorize_empty_extension(self):
        """测试空扩展名"""
        assert categorize_file('', DEFAULT_RULES) is None
        assert categorize_file('.', DEFAULT_RULES) is None

    def test_categorize_with_custom_rules(self, sample_rules):
        """测试自定义规则"""
        assert categorize_file('.jpg', sample_rules) == 'images'
        assert categorize_file('.pdf', sample_rules) == 'documents'
        assert categorize_file('.xyz', sample_rules) == 'custom'
        assert categorize_file('.abc', sample_rules) == 'custom'
        assert categorize_file('.mp3', sample_rules) is None

    def test_categorize_case_insensitive(self):
        """测试大小写不敏感"""
        assert categorize_file('.JPG', DEFAULT_RULES) == 'images'
        assert categorize_file('.PDF', DEFAULT_RULES) == 'documents'
        assert categorize_file('.MP4', DEFAULT_RULES) == 'videos'
        assert categorize_file('.Py', DEFAULT_RULES) == 'code'


# ============================================================================
# 测试 scan_folder
# ============================================================================

class TestScanFolder:
    """测试 scan_folder 函数"""

    def test_scan_empty_folder(self, temp_dir):
        """测试扫描空文件夹"""
        all_files, categorized_files = scan_folder(str(temp_dir))
        assert len(all_files) == 0
        assert len(categorized_files) == 0

    def test_scan_folder_with_mixed_files(self, temp_dir_with_files):
        """测试扫描包含混合文件的文件夹"""
        all_files, categorized_files = scan_folder(str(temp_dir_with_files))
        assert len(all_files) == 9
        assert len(categorized_files) == 8

    def test_scan_nonexistent_folder(self):
        """测试扫描不存在的文件夹"""
        all_files, categorized_files = scan_folder('/nonexistent/path')
        assert len(all_files) == 0
        assert len(categorized_files) == 0

    def test_scan_ignores_subdirectories(self, temp_dir_with_files):
        """测试扫描时忽略子目录中的文件"""
        all_files, categorized_files = scan_folder(str(temp_dir_with_files))
        file_names = {f.name for f in all_files}
        assert 'nested.jpg' not in file_names
        assert 'photo.jpg' in file_names

    def test_scan_with_custom_rules(self, temp_dir):
        """测试使用自定义规则扫描"""
        (temp_dir / 'test.xyz').touch()
        (temp_dir / 'test.abc').touch()
        custom_rules = {'custom': ['.xyz']}
        all_files, categorized_files = scan_folder(str(temp_dir), rules=custom_rules)

    def test_scan_returns_pathlib_paths(self, temp_dir_with_files):
        """测试返回的是 Path 对象"""
        all_files, categorized_files = scan_folder(str(temp_dir_with_files))
        assert all(isinstance(f, Path) for f in all_files)
        assert all(isinstance(f, Path) for f in categorized_files)


# ============================================================================
# 测试 organize_folder（真实文件操作）
# ============================================================================

class TestOrganizeFolder:
    """测试 organize_folder 函数"""

    def test_organize_empty_folder_dry_run(self, temp_dir):
        """测试整理空文件夹（预览模式）"""
        result = organize_folder(str(temp_dir), dry_run=True)
        assert result.total_files == 0
        assert result.moved_files == 0
        assert result.skipped_files == 0
        assert len(result.errors) == 0

    def test_organize_folder_dry_run(self, temp_dir):
        """测试预览模式整理"""
        (temp_dir / 'photo.jpg').touch()
        (temp_dir / 'document.pdf').touch()
        (temp_dir / 'video.mp4').touch()
        (temp_dir / 'music.mp3').touch()
        (temp_dir / 'archive.zip').touch()
        (temp_dir / 'script.py').touch()

        result = organize_folder(str(temp_dir), dry_run=True)
        assert result.total_files == 6
        assert result.moved_files == 6
        assert result.categories['images'] == 1
        assert result.categories['documents'] == 1
        assert result.categories['videos'] == 1
        assert result.categories['audio'] == 1
        assert result.categories['archives'] == 1
        assert result.categories['code'] == 1
        assert (temp_dir / 'photo.jpg').exists()

    def test_organize_folder_actual_move(self, temp_dir):
        """测试实际整理（移动文件）"""
        jpg_file = temp_dir / 'photo.jpg'
        jpg_file.write_text('test content')
        pdf_file = temp_dir / 'document.pdf'
        pdf_file.write_text('test content')
        mp4_file = temp_dir / 'video.mp4'
        mp4_file.write_text('test content')

        result = organize_folder(str(temp_dir), dry_run=False)
        assert not jpg_file.exists()
        assert not pdf_file.exists()
        assert not mp4_file.exists()
        assert (temp_dir / 'images').exists()
        assert (temp_dir / 'documents').exists()
        assert (temp_dir / 'videos').exists()
        assert (temp_dir / 'images' / 'photo.jpg').exists()
        assert (temp_dir / 'documents' / 'document.pdf').exists()
        assert (temp_dir / 'videos' / 'video.mp4').exists()

    def test_organize_preserves_file_content(self, temp_dir):
        """测试移动文件后内容保持不变"""
        original_content = 'Hello, World! 这是测试内容。'
        jpg_file = temp_dir / 'data.jpg'
        jpg_file.write_text(original_content, encoding='utf-8')
        organize_folder(str(temp_dir), dry_run=False)
        moved_file = temp_dir / 'images' / 'data.jpg'
        assert moved_file.exists()
        assert moved_file.read_text(encoding='utf-8') == original_content

    def test_organize_filename_conflict(self, temp_dir):
        """测试文件名冲突处理"""
        images_dir = temp_dir / 'images'
        images_dir.mkdir()
        (images_dir / 'photo.jpg').write_text('existing')
        (temp_dir / 'photo.jpg').write_text('new')

        result = organize_folder(str(temp_dir), dry_run=False)
        assert (temp_dir / 'images' / 'photo.jpg').exists()
        assert (temp_dir / 'images' / 'photo_1.jpg').exists()

    def test_organize_uncategorized_files(self, temp_dir):
        """测试未分类文件的处理"""
        (temp_dir / 'known.jpg').touch()
        (temp_dir / 'unknown.xyz').touch()
        (temp_dir / 'another.abc').touch()

        result = organize_folder(str(temp_dir), dry_run=True)
        assert result.moved_files == 1
        assert result.skipped_files == 2

    def test_organize_nonexistent_folder(self):
        """测试整理不存在的文件夹"""
        result = organize_folder('/nonexistent/path')
        assert len(result.errors) > 0
        assert '不存在' in result.errors[0]

    def test_organize_path_is_file(self, temp_dir):
        """测试路径是文件而非文件夹"""
        file_path = temp_dir / 'file.txt'
        file_path.touch()
        result = organize_folder(str(file_path))
        assert len(result.errors) > 0
        assert '不是文件夹' in result.errors[0]

    def test_organize_result_statistics(self, temp_dir):
        """测试整理结果的统计信息"""
        (temp_dir / 'a.jpg').touch()
        (temp_dir / 'b.png').touch()
        (temp_dir / 'c.pdf').touch()
        (temp_dir / 'd.txt').touch()
        (temp_dir / 'e.mp4').touch()
        (temp_dir / 'f.xyz').touch()
        (temp_dir / 'g.xyz').touch()

        result = organize_folder(str(temp_dir), dry_run=True)
        assert result.total_files == 7
        assert result.moved_files == 5
        assert result.skipped_files == 2
        assert result.categories['images'] == 2
        assert result.categories['documents'] == 2
        assert result.categories['videos'] == 1

    def test_organize_with_custom_rules(self, temp_dir):
        """测试使用自定义规则整理"""
        (temp_dir / 'file.jpg').touch()
        (temp_dir / 'file.pdf').touch()
        (temp_dir / 'file.xyz').touch()

        custom_rules = {'my_images': ['.jpg'], 'my_docs': ['.pdf'], 'custom': ['.xyz']}
        result = organize_folder(str(temp_dir), rules=custom_rules, dry_run=True)
        assert result.categories['my_images'] == 1
        assert result.categories['my_docs'] == 1
        assert result.categories['custom'] == 1


# ============================================================================
# 测试 organize_folder（Mock 测试，不实际操作文件）
# ============================================================================

# 精简规则，便于断言分类名与调用次数
RULES_MIXED = {
    "images": [".jpg", ".png"],
    "docs": [".pdf"],
    "data": [".csv"],
}


@patch("organizer.core.safe_move_file")
class TestOrganizeFolderMocked:
    """safe_move_file 打桩，不执行真实 shutil.move"""

    def setup_method(self):
        self.temp_dir = tempfile.mkdtemp()
        self.root = Path(self.temp_dir)

    def teardown_method(self):
        if self.root.exists():
            shutil.rmtree(self.root)

    def test_empty_folder_no_moves(self, mock_move: MagicMock):
        """空目录：不应调用 safe_move_file"""
        mock_move.return_value = (True, None)
        result = organize_folder(str(self.temp_dir), rules=RULES_MIXED, dry_run=False)
        assert result.total_files == 0
        assert result.moved_files == 0
        mock_move.assert_not_called()

    def test_empty_folder_dry_run_no_moves(self, mock_move: MagicMock):
        """空目录 + dry_run：同样不调用移动"""
        result = organize_folder(str(self.temp_dir), rules=RULES_MIXED, dry_run=True)
        assert result.total_files == 0
        mock_move.assert_not_called()

    def test_mixed_extensions_mocked_no_disk_move(self, mock_move: MagicMock):
        """混合扩展名：仅归类文件会调用 safe_move_file"""
        mock_move.return_value = (True, None)
        (self.root / "a.jpg").write_text("a")
        (self.root / "b.pdf").write_text("b")
        (self.root / "c.csv").write_text("c")
        (self.root / "unknown.bin").write_bytes(b"x")

        result = organize_folder(str(self.temp_dir), rules=RULES_MIXED, dry_run=False)
        assert result.total_files == 4
        assert result.moved_files == 3
        assert result.skipped_files == 1
        assert mock_move.call_count == 3
        assert (self.root / "a.jpg").exists()  # 未真实移动

    def test_target_subdir_already_exists(self, mock_move: MagicMock):
        """目标子文件夹已存在：仍应调用 safe_move_file"""
        mock_move.return_value = (True, None)
        (self.root / "images").mkdir()
        (self.root / "pic.jpg").touch()

        result = organize_folder(str(self.temp_dir), rules=RULES_MIXED, dry_run=False)
        assert result.moved_files == 1
        mock_move.assert_called_once()

    def test_file_without_extension_skipped(self, mock_move: MagicMock):
        """无扩展名文件：不计入归类移动"""
        mock_move.return_value = (True, None)
        (self.root / "README").write_text("hello")
        (self.root / "note.txt").touch()

        result = organize_folder(str(self.temp_dir), rules=RULES_MIXED, dry_run=False)
        assert result.total_files == 2
        assert result.moved_files == 0
        mock_move.assert_not_called()

    def test_safe_move_failure_recorded(self, mock_move: MagicMock):
        """safe_move_file 返回失败：计入 errors"""
        mock_move.return_value = (False, "磁盘已满（模拟）")
        (self.root / "a.jpg").touch()

        result = organize_folder(str(self.temp_dir), rules=RULES_MIXED, dry_run=False)
        assert result.moved_files == 0
        assert len(result.errors) == 1
        assert "磁盘已满" in result.errors[0]

    def test_custom_rules_applied(self, mock_move: MagicMock):
        """验证自定义规则正确应用"""
        mock_move.return_value = (True, None)
        (self.root / "test.xyz").touch()
        custom_rules = {"custom": [".xyz"]}
        result = organize_folder(str(self.root), rules=custom_rules, dry_run=False)
        assert result.categories["custom"] == 1
        mock_move.assert_called_once()

    def test_multiple_files_same_category(self, mock_move: MagicMock):
        """同一分类多个文件应触发多次移动"""
        mock_move.return_value = (True, None)
        (self.root / "a.jpg").touch()
        (self.root / "b.jpg").touch()
        (self.root / "c.jpg").touch()

        result = organize_folder(str(self.root), rules=RULES_MIXED, dry_run=False)
        assert result.categories["images"] == 3
        assert mock_move.call_count == 3


# ============================================================================
# 测试 get_folder_stats
# ============================================================================

class TestGetFolderStats:
    """测试 get_folder_stats 函数"""

    def test_stats_nonexistent_folder(self):
        """测试不存在的文件夹统计"""
        stats = get_folder_stats('/nonexistent/path')
        assert stats['exists'] is False
        assert 'error' in stats

    def test_stats_empty_folder(self, temp_dir):
        """测试空文件夹统计"""
        stats = get_folder_stats(str(temp_dir))
        assert stats['exists'] is True
        assert stats['total_files'] == 0
        assert stats['total_size'] == 0

    def test_stats_with_files(self, temp_dir):
        """测试有文件时的统计"""
        (temp_dir / 'a.jpg').write_bytes(b'x' * 100)
        (temp_dir / 'b.jpg').write_bytes(b'y' * 200)
        (temp_dir / 'c.pdf').write_bytes(b'z' * 50)

        stats = get_folder_stats(str(temp_dir))
        assert stats['total_files'] == 3
        assert stats['total_size'] == 350
        assert stats['file_types']['.jpg'] == 2
        assert stats['file_types']['.pdf'] == 1

    def test_stats_with_subdirectories(self, temp_dir):
        """测试包含子目录的统计"""
        sub_dir = temp_dir / 'subdir'
        sub_dir.mkdir()
        (temp_dir / 'root.jpg').touch()
        (sub_dir / 'nested.pdf').touch()

        stats = get_folder_stats(str(temp_dir))
        assert stats['total_files'] == 1
        assert 'subdir' in stats['subdirs']

    def test_stats_no_extension(self, temp_dir):
        """测试无扩展名文件统计"""
        (temp_dir / 'README').write_text('content')
        (temp_dir / 'Makefile').write_text('content')

        stats = get_folder_stats(str(temp_dir))
        assert stats['total_files'] == 2
        assert '' in stats['file_types']


# ============================================================================
# 测试 OrganizeResult 数据类
# ============================================================================

class TestOrganizeResult:
    """测试 OrganizeResult 数据类"""

    def test_default_values(self):
        """测试默认值"""
        result = OrganizeResult()
        assert result.total_files == 0
        assert result.moved_files == 0
        assert result.skipped_files == 0
        assert result.errors == []

    def test_custom_values(self):
        """测试自定义值"""
        result = OrganizeResult(
            total_files=10,
            moved_files=8,
            skipped_files=2,
            errors=['Error 1', 'Error 2'],
            categories={'images': 5, 'documents': 3}
        )
        assert result.total_files == 10
        assert result.moved_files == 8
        assert len(result.errors) == 2


# ============================================================================
# 集成测试
# ============================================================================

class TestCoreIntegration:
    """核心模块集成测试"""

    def test_full_workflow(self, temp_dir):
        """测试完整工作流程"""
        (temp_dir / 'photo1.jpg').write_bytes(b'photo1')
        (temp_dir / 'photo2.png').write_bytes(b'photo2')
        (temp_dir / 'doc.pdf').write_bytes(b'doc')
        (temp_dir / 'video.mp4').write_bytes(b'video')
        (temp_dir / 'unknown.xyz').write_bytes(b'unknown')

        # 扫描预览
        all_files, categorized = scan_folder(str(temp_dir))
        assert len(all_files) == 5
        assert len(categorized) == 4

        # 预览模式
        preview_result = organize_folder(str(temp_dir), dry_run=True)
        assert preview_result.moved_files == 4
        assert preview_result.skipped_files == 1

        # 实际执行
        result = organize_folder(str(temp_dir), dry_run=False)
        assert result.moved_files == 4
        assert len(result.errors) == 0

        # 验证文件位置
        assert (temp_dir / 'images' / 'photo1.jpg').exists()
        assert (temp_dir / 'images' / 'photo2.png').exists()
        assert (temp_dir / 'documents' / 'doc.pdf').exists()
        assert (temp_dir / 'videos' / 'video.mp4').exists()
        assert (temp_dir / 'unknown.xyz').exists()


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
