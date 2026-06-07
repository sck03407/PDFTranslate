# PDFTranslate 服装行业化改造程序记录

> 状态说明（2026-06-07）：
> 本文档保留为 2026-06-06 的阶段性程序记录。
> 当前仓库对外项目名已统一为 `PDFTranslate`。
> 当前代码与绿色便携版已经继续演进，已移除 `ArgosTranslate` 相关实现，以及 GUI 中“服装低成本本地翻译 / 服装高质量在线翻译”预设入口。
> 当前便携包与 Docker 构建链路已经进一步支持在“本地固定 `BabelDOC v0.6.3`”与“上游 `funstory-ai/BabelDOC` 最新源码 / 指定源码”之间切换。
> 后续请以当前 `README.md`、`docs/zh/advanced/advanced.md`、`docs/zh/getting-started/INSTALLATION_winexe.md` 与便携包内说明为准。

日期：2026-06-06

## 目标

在保留 `PDFMathTranslate-next + BabelDOC` 现成链路的前提下，只做服装行业化的外层改造，满足以下交付目标：

- 保留 BabelDOC 的 PDF 解析、排版重建、双语/单语输出能力；
- 以普通 Windows 办公电脑可用为硬件目标；
- 提供本地低成本英中翻译模式；
- 保留高质量在线 API 模式；
- 默认无顶部遮挡水印；
- 补充服装术语表、默认服装提示词、GUI 预设、示例配置；
- 生成 Windows 绿色便携目录并完成桌面启动验证；
- 修正文档。

## 设计边界

- 未改动 `BabelDOC` 核心排版、解析、重排逻辑；
- 主要修改集中在 `PDFMathTranslate-next` 外层：
  - 配置模型；
  - GUI；
  - 术语表/提示词；
  - 翻译引擎适配；
  - 打包与便携启动脚本；
  - 文档。

## 主要程序改动

### 1. 默认输出与服装预设

已落地：

- `pdf2zh_next/config/model.py`
  - `PDFSettings.watermark_output_mode` 默认改为 `no_watermark`。
  - 增加：
    - `disable_builtin_fashion_glossary`
    - `disable_builtin_fashion_prompt`
    - `install_fashion_local_model`
- `pdf2zh_next/fashion_defaults.py`
  - 新增服装系统提示词；
  - 新增内置服装术语表路径与生效逻辑；
  - 新增 GUI 预设：
    - `Fashion - Low Cost Local`
    - `Fashion - High Quality Online`
  - 本地低成本预设已从原先依赖 `Ollama` 的路线调整为轻量离线 `ArgosTranslate` 路线；
  - 在线高质量预设统一到 `OpenAI-compatible` 付费 API 路线。

### 2. 内置服装术语能力

已落地：

- `pdf2zh_next/assets/glossaries/fashion-en-zh.csv`
  - 继续保留为兼容用的汇总词表；
- `pdf2zh_next/assets/glossaries/fashion-01-garment-parts.csv`
- `pdf2zh_next/assets/glossaries/fashion-02-measurements.csv`
- `pdf2zh_next/assets/glossaries/fashion-03-materials.csv`
- `pdf2zh_next/assets/glossaries/fashion-04-construction.csv`
- `pdf2zh_next/assets/glossaries/fashion-05-quality.csv`
- `pdf2zh_next/assets/glossaries/fashion-06-care-labels.csv`
  - 内置词表已经升级为分类术语包；
  - 覆盖服装部位、测量、面料、车缝工艺、质检和洗护标签；
  - 汇总后约 310 条术语；
- `pdf2zh_next/high_level.py`
  - 统一通过 `get_effective_glossary_paths()` 合并内置术语表与用户上传术语表；
  - 统一通过 `get_effective_custom_system_prompt()` 注入默认服装提示词；
- `pdf2zh_next/translator/utils.py`
  - 术语支持判断不再只看 `support_llm`；
  - 新增对本地轻量离线 `ArgosTranslate` 的术语兼容放行。

### 3. 本地低成本轻量翻译模式

已落地：

- `pdf2zh_next/config/translate_engine_model.py`
  - 新增 `ArgosTranslateSettings`；
- `pdf2zh_next/offline_models.py`
  - 新增轻量离线模型安装与定位逻辑；
  - 默认模型包：
    - `https://argos-net.com/v1/translate-en_zh-1_9.argosmodel`
- `pdf2zh_next/translator/translator_impl/argostranslate.py`
  - 新增本地轻量 EN->ZH 翻译器；
  - 基于：
    - `CTranslate2`
    - `SentencePiece`
    - Argos 模型包
  - 在翻译前对服装术语做占位保护，翻译后回填；
  - 可在无独显的办公电脑上运行；
- `pdf2zh_next/main.py`
  - 新增：
    - `--install-fashion-local-model`
  - 可直接执行一次离线模型安装后退出。

### 4. GUI 行业化调整

已落地：

- `pdf2zh_next/gui.py`
  - 新增“Translation preset”下拉；
  - 恢复 `SiliconFlowFree` 在 GUI 服务下拉中的可选项；
  - 默认 GUI 品牌名曾调整为 `BridgeGroup Translate`，后续首发前统一收口为 `PDFTranslate`；
  - 设置页支持自定义：
    - `Brand Name`
    - `Brand Link`
  - 新增：
    - `Use built-in fashion glossary`
    - `Use built-in fashion prompt`
  - 将“LLM 专属控件”和“术语支持控件”拆开控制：
    - 默认服装提示词仅在支持 LLM 的服务上显示；
    - 服装术语表在 `ArgosTranslate` 本地模式与 LLM 模式均可用；
  - 预设切换可自动改写服务、无水印、并发、术语提取等设置；
  - 读取保存配置时，也能正确回显服装预设状态。
- `pdf2zh_next/gui_translation.yaml`
  - 增加中英文 GUI 文案：
    - 服装预设；
    - 内置服装术语；
    - 内置服装提示词。

### 5. 示例配置

已落地：

- `examples/fashion-local-low-cost.toml`
  - 已切换为 `ArgosTranslate` 本地轻量模式；
  - 默认关闭内置服装提示词；
  - 默认保留内置服装术语表；
  - 默认叠加同目录下的 `fashion-customer-glossary-template.csv`；
  - 默认把离线模型目录放在相对路径 `./offline_models/argostranslate`；
- `examples/fashion-online-high-quality.toml`
  - 保留在线高质量模式；
  - 默认叠加同目录下的 `fashion-customer-glossary-template.csv`；
  - 继续保留自动术语抽取与自动保存候选术语。
- `examples/fashion-customer-glossary-template.csv`
  - 提供客户/品牌专用词表模板；
  - 可与内置分类术语包叠加使用。

### 6. Windows 绿色便携打包

已落地：

- `pdf2zh_next/const.py`
  - 增加 `PDF2ZH_CONFIG_DIR` 环境变量支持，便于绿色版把配置收口到包内；
- `script/build_fashion_portable.ps1`
  - 新增 Windows 绿色便携目录构建脚本；
  - 构建前显式安装同级 `BabelDOC` 开源源码；
  - 构建结果包含：
    - 嵌入式 Python 运行时；
    - 项目依赖；
    - BabelDOC 离线资源包；
    - Argos EN->ZH 离线模型；
    - 默认本地服装配置；
    - 可在 GUI 中切换到在线高质量模式并持久保存；
    - 启动脚本：
      - `Start-Fashion.bat`
      - `Install-Fashion-Local-Model.bat`
    - 桌面快速说明：
      - `README-Fashion-Portable.txt`
- `pyproject.toml`
  - `babeldoc` 依赖基线提升到 `>=0.6.3,<0.7.0`；
  - 修正 `hatch` 打包包含范围，确保便携包中带齐 `pdf2zh_next/**` 主体代码，而不只是术语资源。

## 验证记录

### 1. 代码与测试

已执行：

- `python -m compileall pdf2zh_next`
  - 通过
- `.\.verify_env\Scripts\python.exe -m pytest tests\test_fashion_defaults.py tests\test_gui_fashion_presets.py tests\config\test_main.py -q`
  - 结果：`51 passed`

### 2. 本地轻量模式单句验证

已执行：

- `Front placket width should be 3 cm.`
  - 输出：`前门襟宽度应为3cm.`
- `Shell fabric: 100% cotton`
  - 输出：`面料:100%棉花`
- `Please check the front-placket width and move the care-label.`
  - 说明：连字符写法也能命中 `front placket` / `care label` 术语预设

说明：

- 术语表已在本地轻量模式中实际生效；
- 仍属于轻量机器翻译，最终术语质量建议继续用企业术语库迭代。

### 3. 本地轻量模式 PDF 烟雾验证

已执行：

- 输入：
  - `test/file/translate.cli.plain.text.pdf`
- 命令：
  - 使用 `ArgosTranslate` 本地轻量模式
  - 输出目录：`tmp_cli_out`
- 结果：
  - 成功生成：
    - 单语 PDF
    - 双语 PDF

### 4. Windows 绿色便携目录验证

已执行：

- 构建命令：
  - `powershell -ExecutionPolicy Bypass -File .\script\build_fashion_portable.ps1 -OutputDir "$env:USERPROFILE\Desktop\PDFMathTranslate-Fashion-Portable"`
- 结果：
  - 成功生成：
    - `C:\Users\Administrator\Desktop\PDFMathTranslate-Fashion-Portable`
    - `C:\Users\Administrator\Desktop\PDFMathTranslate-Fashion-Portable.zip`
- 桌面启动验证：
  - 通过 `Start-Fashion.bat` 单入口启动；
  - 本地 WebUI 探测返回 `HTTP 200`；
  - GUI 设置页默认显示：
    - `Fashion - Low Cost Local`
    - `ArgosTranslate`
    - 默认客户术语模板预览表
  - 说明桌面便携目录可正常启动。

## 本次修正文档

已更新：

- `README.md`
- `docs/en/advanced/Documentation-of-Translation-Services.md`
- `docs/en/advanced/TranslationServices/SiliconFlow.md`
- `docs/en/advanced/advanced.md`
- `docs/en/getting-started/INSTALLATION_winexe.md`
- `docs/zh/advanced/advanced.md`
- `docs/zh/advanced/Documentation-of-Translation-Services.md`
- `docs/zh/advanced/TranslationServices/SiliconFlow.md`
- `docs/zh/getting-started/INSTALLATION_winexe.md`

## 当前交付结果

当前仓库已经具备：

- 保留 `PDFMathTranslate-next + BabelDOC` 主链路；
- 仅在外层做服装行业化改造；
- 普通 Windows 办公电脑可用的本地轻量英中模式；
- 保留高质量在线 API 模式；
- 默认无顶部遮挡水印；
- 可双击启动的 Windows 绿色便携目录；
- 已完成程序修改记录与验证记录。

## 后续建议

- 继续扩充服装术语表到 500 条以上，并逐步按客户/品牌拆分子词库；
- 增加客户级术语表模板；
- 对本地轻量模式增加更多服装工艺/BOM/尺寸场景抽样评估；
- 后续如需更强本地质量，可再加第二档本地模型配置，但不建议替换当前轻量默认路线。
