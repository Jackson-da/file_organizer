# 文件整理工具

在本地按**文件扩展名**把指定文件夹**根目录下的文件**移动到分类子文件夹（如 `images`、`documents`）。界面使用 **Streamlit**，规则从 **YAML** 读取。

## 功能特性

- **按扩展名分类**：将根目录文件移入对应子文件夹；子目录内的文件不会递归整理。
- **扫描统计**：选择文件夹后展示文件数量、总大小、类型分布等。
- **预览与确认**：先点「预览」生成表格（相对路径、目标分类），支持分页；再点「确认整理」才执行移动。
- **规则可配置**：默认读取项目根目录 `config.yaml` 中的 `rules`；无效或缺失时使用包内 `organizer/default_rules.yaml`。
- **结果汇总**：整理完成后展示移动数量、跳过数量、错误信息及按分类统计。

## 使用流程

1. 安装依赖：`pip install -r requirements.txt`
2. 启动应用：`streamlit run app.py`
3. 输入或快捷选择要整理的文件夹路径。
4. 查看页面上的扫描统计与类型分布。
5. 点击 **「预览」** 查看整理计划（可调整每页行数与页码）。
6. 确认无误后点击 **「确认整理」** 执行移动（需对该文件夹有写入权限）。

修改 `config.yaml` 中的 `rules` 后，保存文件并**重新触发页面运行**（例如再次操作控件或刷新会话），程序会根据文件修改时间重新加载规则。

## 配置文件

### 规则文件位置（优先级）

1. 环境变量 **`FILE_ORGANIZER_CONFIG`** 指向的 YAML 文件  
2. 项目根目录（与 `app.py` 同级）下的 **`config.yaml`**

若上述配置不存在、无法读取或 `rules` 不合法，则使用 **`organizer/default_rules.yaml`** 作为后备。

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

分类名会作为子文件夹名称，请勿使用路径分隔符、`..` 等在 Windows 上非法的名称；程序会对分类名做安全校验。

### `settings`（可选）

根目录 `config.yaml` 中可包含 `settings`（如 `overwrite_existing`、`include_hidden`、`log_level`）。当前版本整理逻辑仍以代码行为为准；后续可逐步对接这些项。

## 默认支持的分类（可改）

实际列表以你的 `config.yaml` / `default_rules.yaml` 为准，常见分类包括：

| 类型     | 示例扩展名 |
|----------|------------|
| 图片     | .jpg, .png, .gif, .webp |
| 文档     | .pdf, .docx, .txt, .xlsx |
| 视频     | .mp4, .avi, .mkv |
| 音频     | .mp3, .wav, .flac |
| 压缩包   | .zip, .rar, .7z |
| 代码     | .py, .js, .html, .json |
| 可执行   | .exe, .msi, .jar |
| 字体     | .ttf, .otf, .woff |
| 设计     | .psd, .ai, .fig |

无扩展名或规则未覆盖的扩展名不会被移动，仍留在原目录。

## 项目结构

```
文件分类/
├── app.py                      # Streamlit 入口
├── config.yaml                 # 主配置（rules / settings）
├── requirements.txt
├── README.md
├── organizer/
│   ├── __init__.py
│   ├── core.py                 # 扫描、预览表、organize_folder
│   ├── rules.py                # 从 YAML 加载规则、校验、索引
│   ├── utils.py                # 移动、路径校验、配置读写等
│   └── default_rules.yaml      # 内置后备规则
└── tests/
    ├── test_core.py
    ├── test_utils_and_rules.py
    └── test_organize_folder_mocked.py   # organize_folder mock 测试
```

## 运行测试

```bash
pytest tests/ -v
```

## 技术栈

- Python 3.8+
- Streamlit
- PyYAML
- Pandas（预览表格）
- pytest

## 开发与 API 说明（可选）

- 程序内可通过 `organizer.get_effective_rules()`、`organizer.reload_rules()`、`organizer.resolve_config_path()` 访问当前规则与配置路径。
- `organize_folder(path, rules=None, dry_run=False)` 中传入 `rules` 字典可覆盖默认 YAML 规则（便于测试或脚本调用）。

## License

MIT License
