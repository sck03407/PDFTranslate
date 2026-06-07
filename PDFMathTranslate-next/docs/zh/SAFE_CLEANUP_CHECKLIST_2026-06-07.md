# PDFTranslate 安全清理清单（2026-06-07）

本清单只针对两类内容执行删除：

- 已确认无代码引用、无文档构建引用、且属于生成物 / 中间产物 / 本地缓存的内容；
- 在新的根仓库首发结构下不会生效、仅属于上游嵌套仓库遗留的 GitHub 元数据。

这样做是为了避免误删仍可能被手工使用的源码资产，同时把首发仓库中容易误导维护者的无效配置一起收口。

## 项目边界

- `PDFMathTranslate-next/`：应用层项目，负责 CLI、GUI、配置、打包与 BabelDOC 调用。
- 同级 `../BabelDOC/`：本地稳定保留的底层 PDF 翻译与重排引擎源码，当前固定为 `v0.6.3`。

## 本轮已删除

- `../PDFMathTranslate-next/.git`
- `../BabelDOC/.git`
  - 两个嵌套 Git 仓库目录已从工作区移除，避免根仓库首提时被识别成嵌套仓库。
- `PDFMathTranslate-next/.github/`
- `BabelDOC/.github/`
  - 两个子项目内部的上游 GitHub 配置已移除。
  - 新根仓库上传后，GitHub 只识别根目录 `.github/`，子目录中的 `.github` 不会作为仓库级工作流或模板生效。
- `.doctemp/`
  - 文档翻译中间产物目录。
  - 全仓检索无引用，不参与程序运行，也不参与 MkDocs 构建。
- `.verify_env/`
  - 本地临时虚拟环境。
  - 仅用于本机测试，不属于仓库源码。
- `dist/`
  - 本地历史构建产物目录。
  - 便携包已改为重新生成，旧产物可直接清理。
- `.pytest_cache/`
  - `pytest` 缓存目录。
- `pdf2zh_files/`
  - GUI / 预览 / 运行时输出目录。
- 全仓 `__pycache__/`
  - Python 字节码缓存目录。
- 全仓 `.ruff_cache/` 与 `.mypy_cache/`
  - 代码检查和类型检查缓存目录。

## 历史备份位置

- `E:\PDFMathTranslate-preclean-backup-20260607-1\PDFMathTranslate-next.git`
- `E:\PDFMathTranslate-preclean-backup-20260607-1\BabelDOC.git`
  - 两个原始嵌套 Git 历史已备份到仓库根目录外，避免进入首发仓库正文。

## 本轮明确保留

- `../BabelDOC/`
  - 作为本地稳定打包源，继续保留 `v0.6.3`。
- `script/Dockerfile.Demo`
- `script/Dockerfile.China`
  - 当前没有自动工作流引用，但仍属于可手工使用的备用发布资产，不能按“无用文件”直接删除。
- `examples/`
- `pdf2zh_next/assets/glossaries/`
  - 仍被 README、安装文档、便携包脚本和运行逻辑直接使用。

## 当前发布策略

- 当前 `E:\PDFMathTranslate` 外层目录还未初始化为 Git 仓库。
- 当前目录状态已经适合直接作为新的 `PDFTranslate` 根仓库上传到 GitHub。

- 本地 Windows 便携包默认优先使用同级 `../BabelDOC/` 稳定源码。
- 如需直接切到上游最新源码：
  - `script/build_fashion_portable.ps1 -BabelDOCSource github-latest`
  - `script/build_fashion_docker.ps1 -BabelDOCSource github-latest`
- 如需指定上游分支 / 标签 / 提交：
  - `-BabelDOCSource github-ref -BabelDOCGitRef <ref>`
- GitHub 发布工作流：
  - 根目录 `.github/workflows/fashion-release.yml`
