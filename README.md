# 📁 文件整理工具

[![Python](https://img.shields.io/badge/Python-3.9+-blue.svg)](https://www.python.org/)
[![Streamlit](https://img.shields.io/badge/Streamlit-1.28+-red.svg)](https://streamlit.io/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Tests](https://img.shields.io/badge/Tests-125%20passed-brightgreen)](tests/)
[![CI](https://img.shields.io/badge/CI-GitHub%20Actions-brightgreen)](.github/workflows/ci.yml)

在本地按**文件扩展名**把指定文件夹**根目录下的文件**移动到分类子文件夹（如 `images`、`documents`）。界面使用 **Streamlit**，规则从 **YAML** 读取。

---

## ✨ 功能特性

| 功能 | 说明 |
|------|------|
| **多种选文件夹方式** | 支持快捷路径按钮、系统文件管理器浏览、手动输入路径 |
| **按扩展名分类** | 将根目录文件移入对应子文件夹；子目录内的文件不会递归整理 |
| **扫描统计** | 选择文件夹后展示文件数量、总大小、类型分布等 |
| **预览与确认** | 先点「预览」生成表格（相对路径、目标分类），支持分页；再点「确认整理」才执行移动 |
| **规则可配置** | 默认读取项目根目录 `config.yaml` 中的 `rules`；无效或缺失时使用包内 `organizer/default_rules.yaml` |
| **结果汇总** | 整理完成后展示移动数量、跳过数量、错误信息及按分类统计 |
| **安全优先** | 符号链接保护、路径穿越防护、权限检查、重名文件自动编号 |

---

## 🚀 快速开始

### 环境要求

- Python 3.9+

### 安装依赖

```bash
pip install -r requirements.txt
```

### 运行应用

```bash
streamlit run app.py
```

### 使用流程

1. **选择文件夹**：点击快捷路径按钮、或点击「📂 浏览...」打开系统文件管理器、或手动输入路径
2. **查看统计**：页面展示文件数量、总大小、类型分布
3. **预览计划**：点击 **「预览」** 查看整理计划表格
4. **确认整理**：确认无误后点击 **「确认整理」** 执行移动

> ⚠️ 整理操作需要对该文件夹有写入权限。

---

## ⚙️ 配置文件

### 规则文件位置（优先级）

1. 环境变量 **`FILE_ORGANIZER_CONFIG`** 指向的 YAML 文件
2. 项目根目录（与 `app.py` 同级）下的 **`config.yaml`**
3. 若上述配置不存在，使用 **`organizer/default_rules.yaml`** 作为后备

### `rules` 写法示例

```yaml
rules:
  images:
    - .jpg
    - .png
  documents:
    - .pdf
    - .docx
```

> 💡 修改 `config.yaml` 后，保存文件并**重新触发页面运行**，程序会根据文件修改时间自动重新加载规则。

### 安全限制

分类名会作为子文件夹名称，程序会对分类名做安全校验：
- 不允许使用 Windows 保留名（如 `CON`, `PRN`, `AUX`）
- 不允许使用路径分隔符、`..` 等非法字符
- 不允许指向根目录

---

## 📋 默认支持的分类

| 类型 | 示例扩展名 |
|------|------------|
| 图片 | .jpg, .png, .gif, .webp |
| 文档 | .pdf, .docx, .txt, .xlsx |
| 视频 | .mp4, .avi, .mkv |
| 音频 | .mp3, .wav, .flac |
| 压缩包 | .zip, .rar, .7z |
| 代码 | .py, .js, .html, .json |
| 可执行 | .exe, .msi, .jar |
| 字体 | .ttf, .otf, .woff |
| 设计 | .psd, .ai, .fig |

无扩展名或规则未覆盖的扩展名不会被移动，仍留在原目录。

---

## 📂 项目结构

```
文件分类/
├── .github/
│   └── workflows/
│       └── ci.yml              # GitHub Actions CI 配置
├── app.py                       # Streamlit Web 界面
├── config.yaml                  # 用户自定义规则配置
├── requirements.txt             # 依赖列表
├── pyproject.toml               # 工具配置 (Black, isort, mypy, pytest)
├── README.md                    # 本文件
├── organizer/
│   ├── __init__.py           # 包导出
│   ├── core.py               # 核心逻辑：扫描、预览、分类
│   ├── rules.py              # 规则加载、缓存、校验
│   ├── utils.py              # 文件操作工具函数
│   └── default_rules.yaml    # 内置后备规则
└── tests/
    ├── conftest.py            # pytest fixtures
    ├── test_app.py           # UI 层测试
    ├── test_core.py          # 核心功能测试
    ├── test_rules.py         # 规则系统测试
    └── test_utils.py         # 工具函数测试
```

---

## 🧪 运行测试

```bash
# 运行所有测试
pytest tests/ -v

# 运行指定文件
pytest tests/test_core.py -v

# 生成覆盖率报告
pytest tests/ --cov=organizer --cov-report=html
```

---

## 🔧 开发工具

本项目使用以下开发工具维护代码质量：

```bash
# 安装开发依赖
pip install black isort flake8 mypy

# 代码格式化
black .

# 检查导入顺序
isort --check-only .

# 代码风格检查
flake8 .

# 类型检查
mypy organizer app.py
```

### 持续集成 (CI)

项目使用 GitHub Actions 自动运行：
- Black 代码格式检查
- isort 导入顺序检查
- flake8 代码检查
- pytest 测试（支持 Python 3.9-3.12）
- mypy 类型检查

---

## 🔌 API 编程使用

```python
from organizer import (
    analyze_folder,
    organize_folder,
    get_effective_rules,
    preview_organization,
)

# 分析文件夹
analysis = analyze_folder("/path/to/folder")

# 生成预览
df, meta = preview_organization("/path/to/folder")

# 执行整理（dry_run=True 不实际移动）
result = organize_folder("/path/to/folder", dry_run=True)
print(f"将移动 {result.moved_files} 个文件")
```

---

## 🛡️ 安全特性

- ✅ **符号链接保护**：检测并跳过符号链接文件
- ✅ **路径穿越防护**：验证目标路径在允许范围内
- ✅ **权限检查**：操作前验证读写权限
- ✅ **重名自动编号**：避免文件覆盖（file_1.txt, file_2.txt）
- ✅ **预览确认机制**：先预览再执行，降低误操作风险

---

## 🤝 贡献指南

欢迎提交 Issue 和 Pull Request！

1. Fork 本仓库
2. 创建功能分支：`git checkout -b feature/新功能`
3. 确保代码通过所有检查：`pytest tests/`、`black .`、`isort --check .`
4. 提交更改：`git commit -m "feat: 添加新功能"`
5. 推送分支：`git push origin feature/新功能`
6. 创建 Pull Request

---

## 📄 License

MIT License
