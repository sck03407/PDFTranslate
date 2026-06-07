[**开始使用**](./getting-started.md) > **如何安装** > **Windows EXE** _(current)_

---

### 通过 .exe 文件安装 PDFTranslate

***第一步*** | 从你自己的 GitHub Releases 页面下载 `pdf2zh-<version>-with-assets-win64.zip`。

> [!TIP]
> **`pdf2zh-<version>-with-assets-win64.zip` 和 `pdf2zh-<version>-win64.zip` 有什么区别？**
>
> - 如果你是首次下载并使用 PDFTranslate，建议下载 `pdf2zh-<version>-with-assets-win64.zip`。
> - 相比 `pdf2zh-<version>-win64.zip`，`pdf2zh-<version>-with-assets-win64.zip` 包含了资源文件（如字体和模型）。
> - 不含资源的版本在运行时也会动态下载资源，但可能会因网络问题导致下载失败。

***步骤 2*** | 解压 `pdf2zh-<version>-with-assets-win64.zip` 并进入 `pdf2zh` 文件夹。解压需要一些时间，请耐心等待。

***步骤 3*** | 进入 `pdf2zh` 文件夹，然后双击 `pdf2zh.exe`。

> [!TIP]
> **无法运行 .exe 文件**
>
> 如果您在运行 pdf2zh.exe 时遇到问题，请安装 `https://aka.ms/vs/17/release/vc_redist.x64.exe` 后重试。

***步骤 4*** | 双击 exe 文件后，终端窗口会弹出。大约半分钟到一分钟后，默认浏览器会打开一个网页。如果未自动打开，可以尝试手动访问 `http://localhost:7860/`。

> [!TIP]
> 如果 `7860` 端口已被其他程序占用，当前工作区里的便携版会自动回退到下一个可用本地端口，终端会打印实际访问地址。

> [!NOTE]
>
> 如果在使用 WebUI 过程中遇到任何问题，请参考 [此网页](./USAGE_webui.md)。

***步骤 5*** | 尽情享受吧！

> [!TIP]
> **你可以通过命令行使用 .exe 文件**
>
> 通过命令行使用 .exe 文件的步骤如下：
>
> - 打开终端并导航至包含 .exe 文件的文件夹：
>
> ```bash
> cd /path/pdf2zh_next/build
> ```
>
> - 调用 .exe 文件：
>
> ```bash
> ./pdf2zh_next.exe "document.pdf"
> ```
>
> 你可以正常使用其他命令行参数：
>
> ```bash
> ./pdf2zh_next.exe "document.pdf" --lang-in en --lang-out ja
> ```
>
> 如需了解更多关于命令行使用的信息，请参考这篇文章。

> [!NOTE]
> **本服装行业化分支的 Windows 绿色便携目录**
>
> - 如果你需要面向服装资料的桌面便携版，请在源码目录执行 `script/build_fashion_portable.ps1`。
> - 绿色打包脚本默认优先使用同级目录下的 `..\BabelDOC` 源码，因此你本地构建会优先保持在稳定的 `BabelDOC 0.6.3` 版本线上。
> - 如果你希望直接使用 `funstory-ai/BabelDOC` 的最新源码来生成新包，可执行 `script/build_fashion_portable.ps1 -BabelDOCSource github-latest`。
> - 如果你希望指定上游某个分支、标签或提交，可执行 `script/build_fashion_portable.ps1 -BabelDOCSource github-ref -BabelDOCGitRef <ref>`。
> - 生成后的便携目录内会包含：
>   - `Start-Fashion.bat`：推荐入口，默认以原始自定义模式启动，并预载服装词表资源；如需切换模型或接口，可直接在 GUI 的 `Service` 中选择并保存；
>   - `README-Fashion-Portable.txt`：桌面用户快速说明。
>   - `BABELDOC-BUILD-INFO.txt`：记录本次打包使用的 BabelDOC 来源和版本。
>   - `config\\fashion-customer-glossary-template.csv`：默认已挂到 GUI 入口里的客户术语模板，可直接编辑补品牌/客户术语，也可以在 GUI 的 `Customer Glossary Template` 表格里添加、删除并保存。
> - 便携版打包时会预恢复 BabelDOC 离线资源，最终桌面文件夹里不再额外保留 `offline_assets_*.zip` 压缩包。
> - 当前便携版已经兼容 `UTF-8` 与 `UTF-8 BOM` 两种 `config.v3.toml` 写法，不会再因为首行 BOM 导致配置解析失败。
> - 这套便携目录默认显示 `PDFTranslate`，更适合普通 Windows 办公电脑内部分发和桌面双击使用。

<div align="right"> 
<h6><small>本页面的部分内容由 GPT 翻译，可能包含错误。</small></h6>
