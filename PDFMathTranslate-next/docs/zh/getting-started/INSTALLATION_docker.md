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

Docker 镜像默认开启登录：

- 普通用户：`user` / `pdftranslate`，只能看到上传 PDF、翻译、预览和下载流程。
- 管理员：`admin` / `admin`，登录后可看到设置入口并修改设置。

容器中的 `pdf2zh --gui` 默认启动 FastAPI 后端和 React/Vite 前端。普通用户看不到设置入口，后端也会拒绝普通用户访问设置、客户术语模板和输出历史清理接口。

首次部署请立即改默认密码，例如：

```powershell
docker run -d `
  -p 7860:7860 `
  -e PDF2ZH_USER_USERNAME="worker" `
  -e PDF2ZH_USER_PASSWORD="change-user-password" `
  -e PDF2ZH_ADMIN_USERNAME="manager" `
  -e PDF2ZH_ADMIN_PASSWORD="change-admin-password" `
  pdfmathtranslate-fashion:local
```

镜像默认使用 `/app/config/distribution.toml` 作为管理员分发配置。你可以把配置目录挂载到宿主机，只改这个文件来控制登录账号、局域网并发、队列、QPS 和 worker 数：

```powershell
docker run -d `
  -p 7860:7860 `
  -v E:\pdftranslate-config:/app/config `
  -v E:\pdf2zh-output:/app/pdf2zh_files `
  pdfmathtranslate-fashion:local
```

首次使用时，可以先从仓库的 `PDFMathTranslate-next/config/distribution.toml` 复制一份到 `E:\pdftranslate-config\distribution.toml`。

如果你希望临时关闭 Docker 登录，可以覆盖：

```powershell
docker run -d `
  -p 7860:7860 `
  -e PDF2ZH_REQUIRE_GUI_LOGIN=false `
  pdfmathtranslate-fashion:local
```

不启用账号登录时，WebUI 会按单机管理员模式运行；只有可信本机环境才建议这样部署。

> [!TIP]
>
> 局域网多人共用时，默认 `max_concurrent_jobs = 1`，即同一时间只跑一个 PDF 翻译任务，其他用户请求排队。低配服务器建议保持这个值，并把 `qps`、`pool_max_workers` 控制在 2-4 左右，避免多个大文件同时处理导致卡死。
> Docker 部署时也建议加宿主级资源限制，例如 `--cpus 2 --memory 4g --restart unless-stopped`。这样遇到超大 PDF 或异常任务时，风险更容易限制在容器内。

如果你希望把 `pdf2zh_files` 输出目录挂载到宿主机：

```powershell
docker run -d `
  -p 7860:7860 `
  -v E:\pdf2zh-output:/app/pdf2zh_files `
  pdfmathtranslate-fashion:local
```

如果你希望容器启动时也使用与 Windows / 本地运行相同的自动清理策略：

```powershell
docker run -d `
  -p 7860:7860 `
  -v E:\pdf2zh-output:/app/pdf2zh_files `
  -e PDF2ZH_AUTO_CLEANUP_OUTPUT_HISTORY=true `
  -e PDF2ZH_OUTPUT_HISTORY_RETENTION_DAYS=7 `
  pdfmathtranslate-fashion:local
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
> - 如果你希望通过 GitHub Actions 同时发布 Docker 镜像、Windows 便携包和 Tauri 桌面壳包，可使用仓库根目录的 `.github/workflows/fashion-release.yml`。当前 Tauri 产物不会内置 Python 后端；如需一体安装包，需要额外增加后端 sidecar/resource 打包步骤。
<!--
如果你后续为当前仓库提供官方云部署模板，再把这里替换成你自己的
Heroku / Render / Zeabur / Koyeb 链接，不要继续指回上游仓库。
-->

<div align="right"> 
<h6><small>本页面的部分内容由 GPT 翻译，可能包含错误。</small></h6>
