# PDFTranslate GitHub 首次提交清单

本清单面向当前工作区 `E:\PDFMathTranslate`，目标是把它整理成一个适合直接执行 `git init / git add / git commit / push` 的首发仓库。

更新状态（2026-06-07）：

- 首发前最终清理已完成。
- 当前外层目录 `E:\PDFMathTranslate` 还不是 Git 仓库。
- 可以直接从“首次上传流程”一节继续执行。

## 1. 仓库边界

建议把整个 `E:\PDFMathTranslate` 作为新的 GitHub 仓库根目录，仓库名使用：

```text
PDFTranslate
```

建议保留当前双目录结构：

- `PDFMathTranslate-next/`
- `BabelDOC/`

原因：

- 便携版打包脚本默认依赖同级 `BabelDOC/` 稳定源码；
- 当前代码、脚本、文档已经围绕这套结构联调过；
- 首次提交优先追求“可运行、可说明、可维护”，不建议一上来重构目录名和包名。

## 2. 本次首提建议保留

- 根目录：
  - `README.md`
  - `.gitignore`
  - `.github/workflows/fashion-release.yml`
  - `PDFTranslate-GitHub-First-Commit-Checklist.md`
  - `PDFMathTranslate-fashion-translation-plan.md`
- 应用层：
  - `PDFMathTranslate-next/` 全部源码、文档、脚本、示例、测试、LICENSE
- 引擎层：
  - `BabelDOC/` 全部源码与 LICENSE

## 3. 首次提交前必须处理的内容

以下事项已在 `2026-06-07` 实际完成，本节保留为状态记录，方便后续复核。

### 3.1 嵌套 Git 仓库已处理完成

原先工作区内存在两个独立 Git 仓库：

- `PDFMathTranslate-next/.git`
- `BabelDOC/.git`

如果不处理，直接在根目录执行 `git add .`，Git 会把它们识别成嵌套仓库，首次提交会很乱。

本轮实际处理结果：

1. 已备份这两个 `.git` 目录的原始历史。
2. 已从工作区删除这两个嵌套 `.git` 目录。

备份位置：

- `E:\PDFMathTranslate-preclean-backup-20260607-1\PDFMathTranslate-next.git`
- `E:\PDFMathTranslate-preclean-backup-20260607-1\BabelDOC.git`

当前状态：

- `PDFMathTranslate-next/.git` 已不存在
- `BabelDOC/.git` 已不存在
- 外层 `E:\PDFMathTranslate` 仍未 `git init`

### 3.3 子目录 `.github` 已收口完成

原先两个子项目各自保留了上游仓库的 GitHub 配置：

- `PDFMathTranslate-next/.github/`
- `BabelDOC/.github/`

但在新的根仓库结构中，GitHub 只会识别根目录 `E:\PDFMathTranslate\.github\`，不会把子目录里的 `.github` 当作仓库级工作流或模板。

本轮实际处理结果：

1. 已将当前仍需保留的手动发布工作流收口到根目录：
   - `E:\PDFMathTranslate\.github\workflows\fashion-release.yml`
2. 已删除两个子项目内部的 `.github` 遗留内容，避免首发后继续误导维护者。

当前状态：

- 根目录 `.github\workflows\fashion-release.yml` 保留
- `PDFMathTranslate-next/.github` 已清理
- `BabelDOC/.github` 已清理

### 3.2 本地构建与缓存产物已清理完成

本轮已删除这些本地产物：

- `PDFMathTranslate-next\dist\`
- `PDFMathTranslate-next\.verify_env\`
- `PDFMathTranslate-next\.doctemp\`
- `PDFMathTranslate-next\.pytest_cache\`
- `PDFMathTranslate-next\pdf2zh_files\`
- `PDFMathTranslate-next\gradio_files\`
- `PDFMathTranslate-next\tmp\`
- 全仓 `__pycache__\`
- 全仓 `.ruff_cache\`
- 全仓 `.mypy_cache\`

这些内容已经写入根 `.gitignore`，并且本轮已经物理清理完成，当前仓库目录适合直接首发。

## 4. 命名策略

本次首提对外项目名统一为：

```text
PDFTranslate
```

但暂不建议在第一次提交里同时改这些内部兼容名称：

- `pdf2zh_next`
- `pdf2zh-next`
- `pdf2zh`
- `PDFMathTranslate-next`

原因：

- 这些名称已经和代码 import、打包入口、文档链接、测试用例绑定；
- 强行同步重命名会把“仓库整理”变成“大规模重构”，风险明显上升；
- 更合适的做法是先把仓库成功首发，再分第二步做内部命名重构。

## 5. 本轮文档已经修正到位的重点

- 根仓库展示名已统一为 `PDFTranslate`
- GitHub 仓库级配置已收口到根目录 `.github/`
- 便携版说明已改为 `PDFTranslate Portable`
- 便携版已补充：
  - `config.v3.toml` 的 `UTF-8 BOM` 兼容说明
  - `7860` 端口占用时的自动回退说明

## 6. 推荐首次提交流程

当前工作区已经处理完嵌套 `.git` 与本地产物，可以直接在 `E:\PDFMathTranslate` 执行：

```powershell
git init
git add .
git commit -m "Initial import: PDFTranslate"
git branch -M main
git remote add origin <your-github-repo-url>
git push -u origin main
```

如果你打算走 GitHub 网页手动上传，也只上传当前 `E:\PDFMathTranslate` 根目录下的仓库内容即可：

- 不要把 `E:\PDFMathTranslate-preclean-backup-20260607-1\` 一起上传。
- 不要再把已经删除的 `dist`、`.verify_env`、嵌套 `.git` 等目录恢复回工作区。
- 如果网页上传时遇到文件量过大或目录层级不便处理，回到上面的 Git 命令流程会更稳妥。

## 7. 首次提交后建议马上补的第二批工作

- 补一个仓库级 `CHANGELOG.md`
- 补一个面向内部用户的 `PORTABLE_USAGE.md`
- 再评估是否要把 `PDFMathTranslate-next/` 目录改名为 `PDFTranslate-app/` 之类的更直观结构
- 如果准备公开发布，再统一梳理：
  - GitHub URL
  - README 徽章
  - 文档站链接
  - Docker / Release 命名
