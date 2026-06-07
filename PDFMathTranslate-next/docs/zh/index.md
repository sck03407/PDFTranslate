<div align="center">

<img src="./images/banner.png" width="320px" alt="banner"/>

<h2 id="title">PDFTranslate</h2>

<p>
  <a href="./../../LICENSE">
    <img src="https://img.shields.io/badge/license-AGPL--3.0-blue" alt="license"></a>
</p>

</div>

`PDFTranslate` 是当前仓库面向首发整理后的对外项目名。

它基于 `PDFMathTranslate-next + BabelDOC` 现有主链路，面向服装资料翻译场景做了轻量行业化整理，并保留上游兼容的运行时命名 `pdf2zh-next` / `pdf2zh_next`。

- 保留公式、图表、目录、注释与版面重建能力
- 支持命令行、WebUI、Docker 与 Windows 便携打包
- 默认启用服装翻译增强，并将 PDF 输出模式切换为 `No Watermark`

> [!WARNING]
>
> 本项目基于 [AGPL v3](./../../LICENSE) 许可证按原样提供，不对程序质量和性能作任何保证。
>
> 当前仓库仍处于首发前整理阶段。若你准备公开发布，请继续把 Issue、讨论区、镜像地址、发布链接等仓库级入口替换成你自己的正式配置。

## 建议阅读顺序

1. [快速开始](./getting-started/getting-started.md)
2. [Windows EXE 安装](./getting-started/INSTALLATION_winexe.md)
3. [Docker 安装](./getting-started/INSTALLATION_docker.md)
4. [WebUI 使用](./getting-started/USAGE_webui.md)
5. [高级选项](./advanced/advanced.md)

## 当前定制重点

- 默认不输出遮挡内容的首页水印
- 内置 EN->ZH 服装术语词包与客户术语模板
- 默认 GUI 品牌名统一为 `PDFTranslate`
- Windows 便携版兼容 `UTF-8 BOM` 配置，并在 `7860` 端口被占用时自动回退

## 相关说明

- 如需查看英文主说明，请参阅仓库中的 [PDFMathTranslate-next/README.md](/E:/PDFMathTranslate/PDFMathTranslate-next/README.md)
- 如需了解本次首发整理背景，请参阅 [PDFMathTranslate-fashion-translation-plan.md](/E:/PDFMathTranslate/PDFMathTranslate-fashion-translation-plan.md)

<div align="right"> 
<h6><small>本页面的部分内容由 GPT 翻译，可能包含错误。</small></h6>
