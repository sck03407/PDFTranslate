# PDFTranslate

`PDFTranslate` 是当前工作区准备发布到 GitHub 的仓库名。

这个工作区由两层组成：

- `PDFMathTranslate-next/`
  - 应用层，负责 CLI、Gradio WebUI、配置、术语表、Windows 便携打包，以及对 BabelDOC 的调用。
- `BabelDOC/`
  - 底层 PDF 解析、翻译、排版重建引擎源码。

当前仓库目标不是重写上游，而是在保留 `PDFMathTranslate-next + BabelDOC` 主链路的前提下，整理出一个适合服装资料内部使用、适合首次 GitHub 提交的可维护版本。

## 当前状态

- 默认 PDF 输出模式已切到 `No Watermark`。
- 便携版启动链路已补上两项稳定性修复：
  - 兼容 `UTF-8 BOM` 的 `config.v3.toml`；
  - 当 `7860` 端口被占用时，自动回退到下一个可用本地端口。
- 对外项目名统一使用 `PDFTranslate`。
- GitHub 仓库级配置已收口到根目录 `.github/`，当前仅保留手动发布工作流 `.github/workflows/fashion-release.yml`。
- `2026-06-07` 首发前最终清理已完成：
  - 已移除 `PDFMathTranslate-next/.git` 与 `BabelDOC/.git`；
  - 已移除两个子项目内部不再生效的上游 `.github` 配置；
  - 已移除 `PDFMathTranslate-next/dist`、`PDFMathTranslate-next/.verify_env`、`PDFMathTranslate-next/.doctemp`、`PDFMathTranslate-next/.pytest_cache`；
  - 已清理全仓 `__pycache__` 等 Python 缓存目录。
- 两个嵌套 Git 仓库的原始历史已备份到仓库根目录外：
  - `E:\PDFMathTranslate-preclean-backup-20260607-1\`
- 当前 `E:\PDFMathTranslate` 仍未执行 `git init`，可以直接作为新的 GitHub 根仓库继续初始化并上传。

## 命名说明

为了降低首次整理成本，当前保留以下上游兼容命名，不在这次首提中强行改动：

- Python 包名仍为 `pdf2zh_next`
- CLI 入口仍为 `pdf2zh` / `pdf2zh_next`
- 应用层目录仍为 `PDFMathTranslate-next/`
- 引擎层目录仍为 `BabelDOC/`

也就是说，这次调整的是“仓库/项目展示名”，不是立即重构内部 import、包发布名和目录结构。

## 建议阅读顺序

1. [PDFTranslate-GitHub-First-Commit-Checklist.md](/E:/PDFMathTranslate/PDFTranslate-GitHub-First-Commit-Checklist.md)
2. [PDFMathTranslate-fashion-translation-plan.md](/E:/PDFMathTranslate/PDFMathTranslate-fashion-translation-plan.md)
3. [PDFMathTranslate-next/README.md](/E:/PDFMathTranslate/PDFMathTranslate-next/README.md)
4. [PDFMathTranslate-next/docs/zh/SAFE_CLEANUP_CHECKLIST_2026-06-07.md](/E:/PDFMathTranslate/PDFMathTranslate-next/docs/zh/SAFE_CLEANUP_CHECKLIST_2026-06-07.md)

## 输出目录清理

- `PDFMathTranslate-next` 的 WebUI 输出默认保存在 `pdf2zh_files/<session_id>/`。
- 当前仓库已规划为一套共用策略：
  - GUI 设置页提供 `清理 pdf2zh_files` 按钮；
  - 启动 GUI 时可自动清理 N 天前的历史会话目录；
  - Windows 本地运行与 Docker 容器挂载目录共用同一组配置项和清理逻辑。

### Docker 挂载示例

```powershell
docker run -d `
  -p 7860:7860 `
  -v E:\pdf2zh-output:/app/pdf2zh_files `
  pdfmathtranslate-fashion:local
```

如果你希望在容器启动时也自动清理历史输出，可额外传入：

```powershell
docker run -d `
  -p 7860:7860 `
  -v E:\pdf2zh-output:/app/pdf2zh_files `
  -e PDF2ZH_AUTO_CLEANUP_OUTPUT_HISTORY=true `
  -e PDF2ZH_OUTPUT_HISTORY_RETENTION_DAYS=7 `
  pdfmathtranslate-fashion:local
```

## 开源许可

- `PDFMathTranslate-next/` 与 `BabelDOC/` 相关代码均受 AGPL 体系约束。
- 首次对外发布前，请保留原始 LICENSE、鸣谢与来源说明。
