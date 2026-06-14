[**Getting Started**](./getting-started.md) > **Installation** > **Docker** _(current)_

---

### Install PDFMathTranslate via docker

#### What is docker?

[Docker](https://docs.docker.com/get-started/docker-overview/) is an open platform for developing, shipping, and running applications. Docker enables you to separate your applications from your infrastructure so you can deliver software quickly. With Docker, you can manage your infrastructure in the same ways you manage your applications. By taking advantage of Docker's methodologies for shipping, testing, and deploying code, you can significantly reduce the delay between writing code and running it in production.

#### Installation

<h4>1. Build the customized image from this repository:</h4>

```powershell
powershell -ExecutionPolicy Bypass -File .\script\build_fashion_docker.ps1
```

This creates a local image tag named `pdfmathtranslate-fashion:local` by default.

<h4>2. Run the local image:</h4>

```bash
docker run -d -p 7860:7860 pdfmathtranslate-fashion:local
```

By default, the WebUI is regular-user focused and only shows PDF upload, translation, preview, and download. The settings entry is hidden.

The image uses `/app/config/distribution.toml` as the administrator distribution config. You can mount a host config directory and edit only this file to control the settings entry, password, LAN concurrency, queue size, QPS, and worker counts:

```powershell
docker run -d `
  -p 7860:7860 `
  -v E:\pdftranslate-config:/app/config `
  -v E:\pdf2zh-output:/app/pdf2zh_files `
  pdfmathtranslate-fashion:local
```

For first use, copy `PDFMathTranslate-next/config/distribution.toml` from this repository to `E:\pdftranslate-config\distribution.toml`.

For a temporary administrator run that exposes the settings entry and protects it with a password, environment variables still work:

```powershell
docker run -d `
  -p 7860:7860 `
  -e PDF2ZH_SHOW_SETTINGS_TAB=true `
  -e PDF2ZH_SETTINGS_ADMIN_PASSWORD="change-me" `
  pdfmathtranslate-fashion:local
```

> [!TIP]
>
> For shared LAN use, the default `max_concurrent_jobs = 1` runs only one PDF translation job at a time and queues extra users. Keep this value on low-resource servers, and keep `qps` / `pool_max_workers` around 2-4 to reduce the chance of overload.
> For Docker deployment, also consider host-level resource limits such as `--cpus 2 --memory 4g --restart unless-stopped`. This keeps oversized PDFs or abnormal jobs more contained inside the container.

To persist the `pdf2zh_files` output directory on the host:

```powershell
docker run -d `
  -p 7860:7860 `
  -v E:\pdf2zh-output:/app/pdf2zh_files `
  pdfmathtranslate-fashion:local
```

To enable the same automatic cleanup policy used by Windows/local runs:

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
> - If you later publish your own image to GHCR, replace the image name above with your own `ghcr.io/<owner>/<repo>:tag`.
> - To build from the latest upstream `funstory-ai/BabelDOC` source instead of the pinned local-stable line, run `script/build_fashion_docker.ps1 -BabelDOCSource github-latest`.

<h4>2. Enter this URL in your default browser to open the WebUI page:</h4>

```
http://localhost:7860/
```

> [!NOTE]
> If you encounter any issues during use WebUI, please refer to [Usage --> WebUI](./USAGE_webui.md).

> [!NOTE]
> If you encounter any issues during use command line, please refer to [Usage --> Command Line](./USAGE_commandline.md).

> [!NOTE]
> **Fashion-branch source build options**
>
> - For a local Docker build that stays on your stable BabelDOC line, run `script/build_fashion_docker.ps1`.
> - To build from the latest upstream `funstory-ai/BabelDOC` source, run `script/build_fashion_docker.ps1 -BabelDOCSource github-latest`.
> - To publish a Docker image and a Windows portable zip from GitHub Actions, use the root-level `.github/workflows/fashion-release.yml`.
<!--
If you later publish official cloud deployment templates for this repository,
replace this comment block with your own Heroku/Render/Zeabur/Koyeb links.
Do not point cloud deployment buttons back to upstream repositories.
-->
