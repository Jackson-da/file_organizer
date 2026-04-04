"""
tests/conftest.py - pytest 配置和共享 fixtures
"""

import pytest
import tempfile
import shutil
from pathlib import Path


@pytest.fixture
def temp_dir():
    """创建临时目录 fixture"""
    path = tempfile.mkdtemp()
    yield Path(path)
    if Path(path).exists():
        shutil.rmtree(path)


@pytest.fixture
def temp_dir_with_files(temp_dir):
    """创建带测试文件的临时目录"""
    # 创建测试文件
    (temp_dir / 'photo.jpg').write_bytes(b'jpg content')
    (temp_dir / 'photo2.png').write_bytes(b'png content')
    (temp_dir / 'document.pdf').write_bytes(b'pdf content')
    (temp_dir / 'readme.txt').write_bytes(b'txt content')
    (temp_dir / 'video.mp4').write_bytes(b'mp4 content')
    (temp_dir / 'music.mp3').write_bytes(b'mp3 content')
    (temp_dir / 'archive.zip').write_bytes(b'zip content')
    (temp_dir / 'script.py').write_bytes(b'python content')
    (temp_dir / 'unknown.xyz').write_bytes(b'unknown content')

    # 创建子目录
    sub_dir = temp_dir / 'subdir'
    sub_dir.mkdir()
    (sub_dir / 'nested.jpg').write_bytes(b'nested jpg')

    return temp_dir


@pytest.fixture
def sample_rules():
    """示例自定义规则"""
    return {
        'images': ['.jpg', '.png', '.gif'],
        'documents': ['.pdf', '.docx'],
        'custom': ['.xyz', '.abc']
    }
