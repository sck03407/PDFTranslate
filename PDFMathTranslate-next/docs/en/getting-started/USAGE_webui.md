[**Getting Started**](./getting-started.md) > **Installation** > **WebUI** _(current)_

---

### Use PDFMathTranslate via Webui

#### How to open the WebUI page:

There are several methods to open the WebUI interface. If you are using **Windows**, please refer to [this article](./INSTALLATION_winexe.md);

1. Python installed (3.10 <= version <= 3.13); Python 3.13.3 is recommended.

2. Install our package:

3. Start using in browser:

    ```bash
    pdf2zh_next --gui
    ```

4. If your browswer has not been started automatically, goto

    ```bash
    http://localhost:7860/
    ```

    Choose a PDF file and start the translation.

By default, the WebUI uses a `Python/FastAPI backend + React/Vite frontend`. It reuses the existing PDFMathTranslate-next / BabelDOC translation core and does not modify the BabelDOC layer, so upstream BabelDOC updates remain easier to sync. The Tauri desktop app and Docker container use the same frontend build.

The optional Tauri desktop shell starts a local FastAPI backend from `PDFTRANSLATE_BACKEND_BIN` or `pdf2zh` on the system `PATH`. Use the Windows portable package when you need a self-contained offline Windows distribution.

The default interface is regular-user focused and shows PDF upload, translation status, and download. Docker administrators see the settings entry after login; local runs without account login behave as single-user administrator sessions.

Administrators who need to adjust services, branding, glossaries, advanced PDF options, or LAN concurrency limits should prefer editing `distribution.toml` in the config directory:

```toml
[gui_settings]
require_gui_login = true
user_username = "user"
user_password = "change-user-password"
admin_username = "admin"
admin_password = "change-admin-password"
max_concurrent_jobs = 1
max_queue_size = 8

[translation]
qps = 4
pool_max_workers = 4
```

You can also require login temporarily at startup:

```bash
pdf2zh_next --gui --require-gui-login --user-password "user-pass" --admin-password "admin-pass"
```

The Docker image enables account login by default. The default regular user is `user` / `pdftranslate` and can only use the translation home page. The default administrator is `admin` / `admin` and can see the settings entry after login. Change these defaults with `PDF2ZH_USER_PASSWORD` and `PDF2ZH_ADMIN_PASSWORD` when deploying.

5. If you deploy PDFMathTranslate with docker, and you are using ollama as PDFMathTranslate's backend LLM, you should fill "Ollama host" with

   ```bash
   http://host.docker.internal:11434
   ```

### Environment Variables

You can set the source and target languages using environment variables:

- `PDF2ZH_LANG_FROM`: Sets the source language. Defaults to "English".
- `PDF2ZH_LANG_TO`: Sets the target language. Defaults to "Simplified Chinese".

## Preview

<img src="./../../images/before.png" width="500"/>
<img src="./../../images/after.png" width="500"/>
