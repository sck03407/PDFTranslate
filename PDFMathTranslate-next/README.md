<div align="center">

<img src="./docs/images/banner.png" width="320px"  alt="banner"/>

<h2 id="title">PDFTranslate</h2>

<p>
  <a href="./LICENSE">
    <img src="https://img.shields.io/badge/license-AGPL--3.0-blue"></a>
</p>

</div>

PDF scientific paper translation and bilingual comparison. `PDFTranslate` is based on [BabelDOC](https://github.com/funstory-ai/BabelDOC), while keeping the upstream-compatible `pdf2zh-next` / `pdf2zh_next` runtime naming for now.

- 📊 Preserve formulas, charts, table of contents, and annotations _([preview](#preview))_.
- 🌐 Support [multiple languages](./docs/en/supported_languages.md) and diverse [translation services](./docs/en/advanced/Documentation-of-Translation-Services.md).
- 🤖 Provides a [command line tool](./docs/en/getting-started/USAGE_commandline.md), [interactive user interface](./docs/en/getting-started/USAGE_webui.md), and [Docker](./docs/en/getting-started/INSTALLATION_docker.md).

> [!WARNING]
>
> This project is provided "as is" under the [AGPL v3](./LICENSE) license, and no guarantees are provided for the quality and performance of the program. **The entire risk of the program's quality and performance is borne by you.** If the program is found to be defective, you will be responsible for all necessary service, repair, or correction costs.
>
> This repository is being organized for a first standalone release. Before publishing new issue or community links, please finish replacing any remaining upstream-facing contact channels with your own repository settings.

For details on how to contribute, please consult the [Contribution Guide](./docs/en/community/Contribution-Guide.md).

<h2 id="preview">Preview</h2>

<div align="center">
<!-- <img src="./docs/images/preview.gif" width="80%"  alt="preview"/> -->
<img src="https://s.immersivetranslate.com/assets/r2-uploads/images/babeldoc-preview.png" width="80%"/>
</div>

<h2 id="demo">Online Service 🌟</h2>

This repository is currently focused on self-hosted and local-use delivery. If you later provide a public demo or hosted service, replace this section with your own service entry and support policy.

<h2 id="install">Installation and Usage</h2>

### Installation

1. [**Windows EXE**](./docs/en/getting-started/INSTALLATION_winexe.md) <small>Recommended for Windows</small>
2. [**Docker**](./docs/en/getting-started/INSTALLATION_docker.md) <small>Recommended for Linux</small>
3. [**uv** (a Python package manager)](./docs/en/getting-started/INSTALLATION_uv.md) <small>Recommended for macOS</small>

---

### Usage

1. [Using **WebUI**](./docs/en/getting-started/USAGE_webui.md)
2. [Using **Zotero Plugin**](https://github.com/guaguastandup/zotero-pdf2zh) (Third party program)
3. [Using **Commandline**](./docs/en/getting-started/USAGE_commandline.md)

For different use cases, we provide distinct methods to use our program. Check out [this page](./docs/en/getting-started/getting-started.md) for more information.

<h2 id="fashion">Fashion Translation Customization</h2>

This repository includes a fashion-document customization that keeps the existing BabelDOC layout reconstruction pipeline intact while improving apparel-focused defaults:

- `No Watermark` is now the default PDF output mode.
- `PDFTranslate` is the default GUI brand and can be changed by administrators from the React Settings page.
- A bundled English-to-Chinese fashion glossary pack is automatically included for supported workflows unless you disable it.
- A starter customer glossary template is auto-layered in WebUI jobs for supported workflows and can be edited by administrators.
- The built-in pack now covers garment parts, measurements, fabrics, trims, BOM / tech pack wording, QC, care-label wording, testing, production, print, embroidery, labelling, style, fit, and packaging terms, with more than 3700 EN->ZH entries in total.
- A bundled fashion translation system prompt is automatically included for LLM-capable workflows unless you disable it.
- `SiliconFlowFree` remains available as a free online relay option, alongside the paid `SiliconFlow` API workflow.
- `pdf2zh --gui` starts a FastAPI backend with a React/Vite frontend. The old Gradio runtime path has been removed.
- The same WebUI build is used by local runs, Docker, the Windows portable package, and the Tauri desktop app.
- GitHub Actions can build a Windows Tauri desktop installer with the portable backend bundled as a resource: embedded Python, `pdf2zh_next`, dependencies, BabelDOC offline assets, and config templates.
- The Windows portable package remains available as the zip/folder distribution for users who prefer a no-installer package.
- Administrators can clean `pdf2zh_files` history from the Settings page, and startup can automatically remove session folders older than a configurable number of days.
- Docker enables username/password login by default: regular users only see translation and download workflows, while administrators can see the Settings page and tune LAN queue / QPS limits.
- Portable builds now tolerate `UTF-8 BOM` in `config.v3.toml`.
- If local port `7860` is already occupied, the GUI now automatically falls forward to the next available local port.

For command-line use, you can also start from the example files:

- [examples/fashion-online-high-quality.toml](./examples/fashion-online-high-quality.toml)
- [examples/fashion-customer-glossary-template.csv](./examples/fashion-customer-glossary-template.csv)

For Windows desktop delivery, this branch also includes a portable builder:

```powershell
powershell -ExecutionPolicy Bypass -File .\script\build_fashion_portable.ps1
```

Default behavior prefers the sibling `..\BabelDOC` source tree, so local packaged builds stay pinned to your stable `BabelDOC 0.6.3` source checkout when it is present.
You can also build directly from the latest upstream source:

```powershell
powershell -ExecutionPolicy Bypass -File .\script\build_fashion_portable.ps1 -BabelDOCSource github-latest
```

Or from a specific upstream ref:

```powershell
powershell -ExecutionPolicy Bypass -File .\script\build_fashion_portable.ps1 -BabelDOCSource github-ref -BabelDOCGitRef main
```

The portable folder now includes:

- `Start-Fashion.bat`
- `README-Fashion-Portable.txt`
- `BABELDOC-BUILD-INFO.txt`

Desktop packaging note:

- The Windows Tauri installer uses the same portable Python/FastAPI backend as a bundled resource and starts it locally before the React WebUI calls the API.
- Local Tauri development builds still support `PDFTRANSLATE_BACKEND_BIN`, `PDFTRANSLATE_RUNTIME_DIR`, or a `pdf2zh` command on `PATH` as overrides.
- This is packaging-only: BabelDOC remains a Python dependency/source checkout selected by the portable builder, so the PDF parsing and layout reconstruction layer is not forked for desktop packaging.
- BabelDOC syncs stay manageable as long as the packaging scripts keep the current source-selection model: stable local `..\BabelDOC`, latest upstream source, or a specific upstream ref.

For container builds, this branch also includes:

```powershell
powershell -ExecutionPolicy Bypass -File .\script\build_fashion_docker.ps1
```

To persist translation outputs on the host, you can mount `pdf2zh_files` directly:

```powershell
docker run -d `
  -p 7860:7860 `
  -v E:\pdf2zh-output:/app/pdf2zh_files `
  pdfmathtranslate-fashion:local
```

If you want the container to automatically clean old session folders on startup, add:

```powershell
docker run -d `
  -p 7860:7860 `
  -v E:\pdf2zh-output:/app/pdf2zh_files `
  -e PDF2ZH_AUTO_CLEANUP_OUTPUT_HISTORY=true `
  -e PDF2ZH_OUTPUT_HISTORY_RETENTION_DAYS=7 `
  pdfmathtranslate-fashion:local
```

And a root-level GitHub Actions manual workflow at `../.github/workflows/fashion-release.yml` that can build a Windows portable zip, a Windows self-contained Tauri installer with the bundled backend resource, shell-style macOS/Linux Tauri bundles, and a GHCR Docker image from either the local-stable BabelDOC line or the latest `funstory-ai/BabelDOC` source.

<h2 id="usage">Advanced Options</h2>

For detailed explanations, please refer to [Advanced Usage](./docs/en/advanced/advanced.md) for a full list of each option.

<h2 id="downstream">Secondary Development (APIs)</h2>

<!-- <!-- For downstream applications, please refer to our document about [API Details](./docs/APIS.md) for futher information about: -->

- [Python API](./docs/en/advanced/API/python.md), how to use the program in other Python programs
<!-- - [HTTP API](./docs/APIS.md#api-http), how to communicate with a server with the program installed -->

<h2 id="langcode">Language Code</h2>

If you don't know what code to use to translate to the language you need, check out [this documentation](./docs/en/advanced/Language-Codes.md)

<h2 id="acknowledgement">Acknowledgements</h2>

- [Immersive Translation](https://immersivetranslate.com) sponsors monthly Pro membership redemption codes for active contributors to this project, see details at: [CONTRIBUTOR_REWARD.md](https://github.com/funstory-ai/BabelDOC/blob/main/docs/CONTRIBUTOR_REWARD.md)

- OpenAI-compatible paid APIs, Ollama and other upstream-configurable translation engines remain available in this customized branch.

- 1.x version: [Byaidu/PDFMathTranslate](https://github.com/Byaidu/PDFMathTranslate)


- backend: [BabelDOC](https://github.com/funstory-ai/BabelDOC)

- PDF Library: [PyMuPDF](https://github.com/pymupdf/PyMuPDF)

- PDF Parsing: [Pdfminer.six](https://github.com/pdfminer/pdfminer.six)

- Layout Parsing: [DocLayout-YOLO](https://github.com/opendatalab/DocLayout-YOLO)

- PDF Standards: [PDF Explained](https://zxyle.github.io/PDF-Explained/), [PDF Cheat Sheets](https://pdfa.org/resource/pdf-cheat-sheets/)

- Multilingual Font: see [BabelDOC-Assets](https://github.com/funstory-ai/BabelDOC-Assets)

- [Asynchronize](https://github.com/multimeric/Asynchronize/tree/master?tab=readme-ov-file)

- [Rich logging with multiprocessing](https://github.com/SebastianGrans/Rich-multiprocess-logging/tree/main)


<h2 id="conduct">Before submit your code</h2>

We welcome the active participation of contributors to make PDFTranslate better. Before you are ready to submit your code, please refer to our [Code of Conduct](./docs/en/CODE_OF_CONDUCT.md) and [Contribution Guide](./docs/en/community/Contribution-Guide.md).

<h2 id="contrib">Contributors</h2>

