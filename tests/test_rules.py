"""
tests/test_rules.py - 规则模块单元测试
"""

import os
import pytest
from organizer.rules import (
    DEFAULT_RULES,
    get_all_extensions,
    get_category_for_extension,
    load_rules_from_dict,
    merge_rules,
    validate_category_name
)


# ============================================================================
# 测试默认规则
# ============================================================================

class TestDefaultRules:
    """测试默认规则"""

    def test_default_rules_is_dict(self):
        """验证默认规则是字典"""
        assert isinstance(DEFAULT_RULES, dict)

    def test_default_rules_has_expected_categories(self):
        """验证包含所有预期的分类"""
        expected_categories = {
            'images', 'documents', 'videos', 'audio',
            'archives', 'code', 'executables', 'fonts',
            '3d_models', 'design'
        }
        assert set(DEFAULT_RULES.keys()) == expected_categories

    def test_default_rules_values_are_lists(self):
        """验证所有规则的扩展名都是列表"""
        for category, extensions in DEFAULT_RULES.items():
            assert isinstance(extensions, list)
            assert all(isinstance(ext, str) for ext in extensions)

    def test_extensions_start_with_dot(self):
        """验证所有扩展名都以点号开头"""
        for category, extensions in DEFAULT_RULES.items():
            for ext in extensions:
                assert ext.startswith('.'), f"扩展名 {ext} 应以点号开头"


# ============================================================================
# 测试 get_all_extensions
# ============================================================================

class TestGetAllExtensions:
    """测试 get_all_extensions 函数"""

    def test_returns_list(self):
        """验证返回类型是列表"""
        result = get_all_extensions()
        assert isinstance(result, list)

    def test_all_extensions_unique(self):
        """验证扩展名不重复"""
        result = get_all_extensions()
        assert len(result) == len(set(result))

    def test_extensions_sorted(self):
        """验证扩展名已排序"""
        result = get_all_extensions()
        assert result == sorted(result)

    def test_common_extensions_present(self):
        """验证常见扩展名存在"""
        result = get_all_extensions()
        common_exts = ['.jpg', '.pdf', '.mp4', '.mp3', '.zip', '.py', '.exe']
        for ext in common_exts:
            assert ext in result


# ============================================================================
# 测试 get_category_for_extension
# ============================================================================

class TestGetCategoryForExtension:
    """测试 get_category_for_extension 函数"""

    def test_image_extensions(self):
        """测试图片扩展名"""
        assert get_category_for_extension('.jpg') == 'images'
        assert get_category_for_extension('.png') == 'images'
        assert get_category_for_extension('jpg') == 'images'

    def test_document_extensions(self):
        """测试文档扩展名"""
        assert get_category_for_extension('.pdf') == 'documents'
        assert get_category_for_extension('.docx') == 'documents'

    def test_video_extensions(self):
        """测试视频扩展名"""
        assert get_category_for_extension('.mp4') == 'videos'
        assert get_category_for_extension('.mkv') == 'videos'

    def test_case_insensitive(self):
        """测试大小写不敏感"""
        assert get_category_for_extension('.JPG') == 'images'
        assert get_category_for_extension('.PDF') == 'documents'
        assert get_category_for_extension('.PY') == 'code'

    def test_unknown_extension(self):
        """测试未知扩展名"""
        assert get_category_for_extension('.xyz') == 'others'
        assert get_category_for_extension('.unknown') == 'others'

    def test_no_extension(self):
        """测试无扩展名文件"""
        assert get_category_for_extension('') == 'others'
        assert get_category_for_extension('noextension') == 'others'


# ============================================================================
# 测试 load_rules_from_dict
# ============================================================================

class TestLoadRulesFromDict:
    """测试 load_rules_from_dict 函数"""

    def test_valid_rules(self, sample_rules):
        """测试有效规则"""
        result = load_rules_from_dict(sample_rules)
        assert isinstance(result, dict)
        assert 'images' in result
        assert '.jpg' in result['images']

    def test_normalize_extension_dots(self):
        """测试扩展名点号规范化"""
        rules = {'images': ['jpg', '.png', 'gif']}
        result = load_rules_from_dict(rules)
        assert all(ext.startswith('.') for ext in result['images'])

    def test_lowercase_normalization(self):
        """测试小写规范化"""
        rules = {'images': ['.JPG', '.PNG', '.GIF']}
        result = load_rules_from_dict(rules)
        assert '.jpg' in result['images']
        assert '.png' in result['images']
        assert '.gif' in result['images']

    def test_invalid_type_not_dict(self):
        """测试非字典输入"""
        with pytest.raises(ValueError, match="必须是字典类型"):
            load_rules_from_dict("not a dict")
        with pytest.raises(ValueError, match="必须是字典类型"):
            load_rules_from_dict([1, 2, 3])

    def test_invalid_category_type(self):
        """测试无效的分类名称类型"""
        rules = {123: ['.jpg']}
        with pytest.raises(ValueError, match="必须是字符串"):
            load_rules_from_dict(rules)

    def test_invalid_extension_type(self):
        """测试无效的扩展名类型"""
        rules = {'images': ['.jpg', 123]}
        with pytest.raises(ValueError, match="扩展名必须是字符串"):
            load_rules_from_dict(rules)

    def test_empty_rules_dict(self):
        """测试空规则字典"""
        result = load_rules_from_dict({})
        assert result == {}

    def test_rules_with_whitespace(self):
        """测试带空白的扩展名"""
        rules = {"images": [" .jpg ", " .png"]}
        result = load_rules_from_dict(rules)
        assert ".jpg" in result["images"]
        assert ".png" in result["images"]


# ============================================================================
# 测试 merge_rules
# ============================================================================

class TestMergeRules:
    """测试 merge_rules 函数"""

    def test_merge_adds_new_category(self):
        """测试合并添加新分类"""
        base = {'images': ['.jpg']}
        custom = {'documents': ['.pdf']}
        result = merge_rules(base, custom)
        assert 'images' in result
        assert 'documents' in result
        assert result['documents'] == ['.pdf']

    def test_merge_extends_existing(self):
        """测试合并扩展现有分类"""
        base = {'images': ['.jpg', '.png']}
        custom = {'images': ['.gif']}
        result = merge_rules(base, custom)
        assert '.jpg' in result['images']
        assert '.png' in result['images']
        assert '.gif' in result['images']

    def test_merge_avoid_duplicates(self):
        """测试合并避免重复"""
        base = {'images': ['.jpg', '.png']}
        custom = {'images': ['.jpg', '.gif']}
        result = merge_rules(base, custom)
        assert result['images'].count('.jpg') == 1


# ============================================================================
# 测试 validate_category_name
# ============================================================================

class TestValidateCategoryName:
    """测试分类名称验证"""

    def test_valid_category_names(self):
        """测试有效分类名"""
        assert validate_category_name("images") is True
        assert validate_category_name("my_folder") is True
        assert validate_category_name("docs_2024") is True

    def test_traversal_attempt(self):
        """测试路径遍历尝试被拒绝"""
        assert validate_category_name("..") is False
        assert validate_category_name("a/b") is False
        assert validate_category_name("../danger") is False

    @pytest.mark.skipif(os.name != "nt", reason="Windows 保留设备名")
    def test_windows_reserved_names(self):
        """测试 Windows 保留设备名被拒绝"""
        assert validate_category_name("CON") is False
        assert validate_category_name("PRN") is False
        assert validate_category_name("AUX") is False


# ============================================================================
# 测试合并规则时的验证
# ============================================================================

class TestMergeRulesValidation:
    """测试合并规则时的验证"""

    def test_merge_with_illegal_category_name(self):
        """测试合并包含非法分类名的规则"""
        with pytest.raises(ValueError, match="非法分类名"):
            merge_rules(DEFAULT_RULES, {"evil/name": [".x"]})

    def test_merge_with_traversal_in_name(self):
        """测试合并包含路径遍历的分类名"""
        with pytest.raises(ValueError, match="非法分类名"):
            merge_rules(DEFAULT_RULES, {"../danger": [".x"]})


# ============================================================================
# 集成测试
# ============================================================================

class TestRulesIntegration:
    """规则模块集成测试"""

    def test_complete_workflow(self):
        """测试完整工作流程"""
        custom_rules = {
            'my_images': ['.jpg', '.png'],
            'my_docs': ['.pdf']
        }
        rules = load_rules_from_dict(custom_rules)
        merged = merge_rules(DEFAULT_RULES, rules)
        assert get_category_for_extension('.jpg') == 'images'
        assert get_category_for_extension('.pdf') == 'documents'

    def test_empty_custom_rules(self):
        """测试空自定义规则"""
        result = merge_rules(DEFAULT_RULES, {})
        assert result is not None


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
