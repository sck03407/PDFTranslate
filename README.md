# PDFTranslate

[![License: AGPL-3.0](https://img.shields.io/badge/license-AGPL--3.0-blue.svg)](PDFMathTranslate-next/LICENSE)

PDFTranslate 是面向服装、纺织、BOM、Tech Pack、洗护标签、尺寸表和质检资料的 PDF 翻译定制版。

本仓库基于 `PDFMathTranslate-next` 与 `BabelDOC`：保留原有 PDF 解析、版式重建、单语/双语输出、CLI 和 WebUI 能力，在应用层补充服装行业默认配置、专业术语库、中文界面、Windows 便携包、Docker 部署和 GitHub Release 工作流。

> 当前定位：本地或内网自托管工具。仓库不提供公共云翻译服务；如部署到公网，请自行完成账号、密码、网络隔离、日志和文件合规评估。

## 主要功能

- 保留 PDF 原版式，支持单语译文 PDF 与双语对照 PDF。
- 默认 PDF 输出模式为 `no_watermark`，不生成遮挡正文的顶部水印。
- WebUI 使用 FastAPI 后端与 React/Vite 前端，默认中文界面。
- 内置 12 类 EN->ZH 服装行业术语包，覆盖服装部位、尺寸、面料、工艺、质检、洗护、BOM、Tech Pack、辅料、包装、生产跟单、印绣花、版型和合规测试等场景。
- 支持客户/品牌专属术语 CSV，并支持自动抽取候选术语。
- 支持多翻译引擎配置，包括 SiliconFlowFree、SiliconFlow、OpenAI-compatible、Ollama、Xinference、DeepL、Google、Bing 等上游兼容服务。
- Docker 默认启用普通用户/管理员登录，普通用户只看到上传、翻译、预览和下载流程。
- Windows 便携包内置 Python 运行环境、配置模板、BabelDOC 离线资源和启动脚本，适合发给不安装 Python 的普通用户。
- 可选 Tauri 桌面壳复用同一套 WebUI，但当前 Tauri 包仍需要外部或已安装的 `pdf2zh` 后端；完整离线桌面分发优先使用 Windows 便携包。

## 项目结构

```text
PDFTranslate/
├── PDFMathTranslate-next/        # 应用层：CLI、FastAPI/React WebUI、配置、打包和 Docker
├── BabelDOC/                     # PDF 解析、翻译中间层、排版重建引擎
├── .github/workflows/            # 手动发布 Windows 便携包、Tauri 壳包和 Docker 镜像
├── PDFMathTranslate-fashion-translation-plan.md
└── README.md
```

为保持与上游生态兼容，当前仍保留以下内部命名：

- Python 包名：`pdf2zh_next`
- CLI 入口：`pdf2zh`、`pdf2zh2`、`pdf2zh_next`
- 应用层目录：`PDFMathTranslate-next/`
- 引擎层目录：`BabelDOC/`

## 快速开始

### 从源码运行 WebUI

推荐 Python `3.10` 到 `3.13`，当前便携包与 Docker 默认使用 Python `3.13.3`。

Windows PowerShell：

```powershell
cd PDFMathTranslate-next
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -U pip
pip install -e ..\BabelDOC
pip install -e .
pdf2zh_next --gui
```

macOS / Linux：

```bash
cd PDFMathTranslate-next
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -U pip
pip install -e ../BabelDOC
pip install -e .
pdf2zh_next --gui
```

浏览器打开：

```text
http://localhost:7860/
```

如果 `7860` 端口被占用，当前 GUI 启动链路会自动尝试下一个可用本地端口，并在终端输出实际地址。

### 命令行翻译

```bash
cd PDFMathTranslate-next
pdf2zh_next example.pdf
```

使用高质量在线配置模板：

```bash
pdf2zh_next --config-file examples/fashion-online-high-quality.toml example.pdf
```

使用前请把 `examples/fashion-online-high-quality.toml` 中的 API 地址、模型名和 API Key 改成自己的服务配置。

## Docker 部署

从源码构建本地镜像：

```powershell
cd PDFMathTranslate-next
powershell -ExecutionPolicy Bypass -File .\script\build_fashion_docker.ps1
```

运行镜像：

```bash
docker run -d -p 7860:7860 pdfmathtranslate-fashion:local
```

Docker 镜像默认启用登录：

- 普通用户：`user` / `pdftranslate`
- 管理员：`admin` / `admin`

生产或内网共享部署时请立即修改默认密码，并建议挂载配置和输出目录：

```bash
docker run -d \
  -p 7860:7860 \
  -e PDF2ZH_USER_PASSWORD="change-user-password" \
  -e PDF2ZH_ADMIN_PASSWORD="change-admin-password" \
  -v /absolute/path/pdftranslate-config:/app/config \
  -v /absolute/path/pdf2zh-output:/app/pdf2zh_files \
  pdfmathtranslate-fashion:local
```

局域网多人共用时，建议保持 `max_concurrent_jobs = 1`，让大文件翻译任务排队执行，避免低配机器同时处理多个 PDF 时耗尽 CPU、内存或上游 API 额度。

## Windows 便携包

生成便携目录和 zip：

```powershell
cd PDFMathTranslate-next
powershell -ExecutionPolicy Bypass -File .\script\build_fashion_portable.ps1
```

默认输出：

```text
PDFMathTranslate-next/dist/pdftranslate-portable/
PDFMathTranslate-next/dist/pdftranslate-portable.zip
```

便携包用户双击 `Start-Fashion.bat` 启动。管理员可编辑便携目录中的 `config/distribution.toml`，控制品牌名、登录账号、局域网并发、队列、QPS、worker 数、输出目录清理和水印模式。

## 配置与术语库

推荐优先使用 `PDFMathTranslate-next/config/distribution.toml` 作为分发配置模板。配置优先级为：

```text
CLI / GUI > 环境变量 > distribution.toml > 用户配置文件 > 默认配置
```

常用配置项：

- `PDF2ZH_CONFIG_DIR`：配置目录。
- `PDF2ZH_OUTPUT_DIR`：WebUI 输出目录，默认使用 `pdf2zh_files/`。
- `PDF2ZH_CUSTOMER_GLOSSARY_DIR`：客户术语模板目录。
- `PDF2ZH_REQUIRE_GUI_LOGIN`：是否要求登录。
- `PDF2ZH_USER_PASSWORD` / `PDF2ZH_ADMIN_PASSWORD`：Docker 或内网部署的登录密码。

术语 CSV 至少需要包含：

```csv
source,target,tgt_lng
front placket,前门襟,zh
bartack,打枣,zh
```

内置服装术语包位于 `PDFMathTranslate-next/pdf2zh_next/assets/glossaries/`。客户术语模板可从 `PDFMathTranslate-next/examples/fashion-customer-glossary-template.csv` 开始维护。

## GitHub Release

仓库提供手动触发的发布工作流：

```text
.github/workflows/fashion-release.yml
```

该工作流可以构建：

- Windows 便携 zip。
- Windows / macOS / Linux 的 Tauri 桌面壳包。
- GHCR Docker 镜像。

注意：当前 Tauri 产物是桌面壳，会通过 `PDFTRANSLATE_BACKEND_BIN` 或系统 `PATH` 中的 `pdf2zh` 启动本地 FastAPI 后端；它还不是内置 Python 后端的一体安装包。如需完整离线桌面安装包，应复用 Windows 便携后端作为 Tauri sidecar 或 bundled resource。

## 质量与路线

当前版本优先保证服装资料翻译的可用链路：

- 无水印默认输出。
- 服装术语库与客户术语叠加。
- WebUI、CLI、Docker、Windows 便携包共用同一翻译核心。
- 输出目录按会话隔离，支持历史会话清理。

后续重点方向：

- 使用真实服装 PDF 样本建立回归测试集。
- 增强术语冲突检测、候选术语审核和术语命中报告。
- 验证 Argos Translate、OPUS-MT 等低配置离线翻译路线。
- 完善一体化 Tauri 后端打包。

详细设计见 [PDFMathTranslate-fashion-translation-plan.md](PDFMathTranslate-fashion-translation-plan.md)。

## 文档入口

- [PDFMathTranslate-next README](PDFMathTranslate-next/README.md)
- [中文 WebUI 使用说明](PDFMathTranslate-next/docs/zh/getting-started/USAGE_webui.md)
- [中文命令行使用说明](PDFMathTranslate-next/docs/zh/getting-started/USAGE_commandline.md)
- [中文 Docker 使用说明](PDFMathTranslate-next/docs/zh/getting-started/INSTALLATION_docker.md)
- [高级配置说明](PDFMathTranslate-next/docs/zh/advanced/advanced.md)
- [翻译服务说明](PDFMathTranslate-next/docs/zh/advanced/Documentation-of-Translation-Services.md)
- [服装术语来源与扩展建议](PDFMathTranslate-next/docs/zh/advanced/FASHION_GLOSSARY_SOURCES.md)

## 开源许可与鸣谢

本仓库遵循 AGPL-3.0 许可。关闭或移除输出 PDF 中的遮挡水印，不代表可以删除开源许可证、版权声明或上游鸣谢。

感谢以下项目和社区：

- [PDFMathTranslate-next](https://github.com/PDFMathTranslate-next/PDFMathTranslate-next)
- [BabelDOC](https://github.com/funstory-ai/BabelDOC)
- [PDFMathTranslate 1.x](https://github.com/Byaidu/PDFMathTranslate)
- [PyMuPDF](https://github.com/pymupdf/PyMuPDF)
- [pdfminer.six](https://github.com/pdfminer/pdfminer.six)
- [DocLayout-YOLO](https://github.com/opendatalab/DocLayout-YOLO)
