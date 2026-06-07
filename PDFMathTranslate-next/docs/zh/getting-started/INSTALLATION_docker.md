[**开始使用**](./getting-started.md) > **如何安装** > **Docker** _(当前)_

---

### 通过 docker 安装 PDFMathTranslate

#### 什么是 docker？

[Docker](https://docs.docker.com/get-started/docker-overview/) 是一个用于开发、运输和运行应用程序的开放平台。Docker 使您能够将应用程序与基础设施分离，从而可以快速交付软件。通过 Docker，您可以用管理应用程序的方式来管理基础设施。利用 Docker 的代码运输、测试和部署方法，您可以显著减少编写代码与在生产环境中运行代码之间的延迟。

#### 如何安装

<h4>1. 从当前仓库源码构建定制镜像：</h4>

```powershell
powershell -ExecutionPolicy Bypass -File .\script\build_fashion_docker.ps1
```

默认会生成本地镜像标签 `pdfmathtranslate-fashion:local`。

<h4>2. 运行本地镜像：</h4>

```bash
docker run -d -p 7860:7860 pdfmathtranslate-fashion:local
```

> [!NOTE]
>
> - 如果你后续把镜像发布到自己的 GHCR，请将上面的镜像名替换成你自己的 `ghcr.io/<owner>/<repo>:tag`。
> - 如果你希望直接基于 `funstory-ai/BabelDOC` 最新源码构建，而不是本地固定稳定线，可执行 `script/build_fashion_docker.ps1 -BabelDOCSource github-latest`。

<h4>2. 在默认浏览器中输入此 URL 以打开 WebUI 页面：</h4>

```
http://localhost:7860/
```

> [!NOTE]
> 如果在使用 WebUI 时遇到任何问题，请参考 [如何使用 --> WebUI](./USAGE_webui.md)。

> [!NOTE]
> 如果在使用命令行时遇到任何问题，请参考 [如何使用 --> 命令行](./USAGE_commandline.md)。

> [!NOTE]
> **本服装分支的源码构建方式**
>
> - 如果你希望在本地构建并继续保持稳定的 BabelDOC 版本线，可执行 `script/build_fashion_docker.ps1`。
> - 如果你希望直接基于 `funstory-ai/BabelDOC` 最新源码构建 Docker 镜像，可执行 `script/build_fashion_docker.ps1 -BabelDOCSource github-latest`。
> - 如果你希望通过 GitHub Actions 同时发布 Docker 镜像和 Windows 便携包，可使用仓库根目录的 `.github/workflows/fashion-release.yml`。
<!--
如果你后续为当前仓库提供官方云部署模板，再把这里替换成你自己的
Heroku / Render / Zeabur / Koyeb 链接，不要继续指回上游仓库。
-->

<div align="right"> 
<h6><small>本页面的部分内容由 GPT 翻译，可能包含错误。</small></h6>
