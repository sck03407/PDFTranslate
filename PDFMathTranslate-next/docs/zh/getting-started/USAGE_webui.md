[**开始使用**](./getting-started.md) > **如何安装** > **WebUI** _(当前)_

---

### 通过 Webui 使用 PDFMathTranslate

#### 如何打开 WebUI 页面：

有多种方法可以打开 WebUI 界面。如果您使用的是 **Windows**，请参考 [这篇文章](./INSTALLATION_winexe.md)；

1. 已安装 Python（3.10 <= 版本 <= 3.13），推荐使用 Python 3.13.3

2. 安装我们的软件包：

3. 在浏览器中开始使用：

    ```bash
    pdf2zh_next --gui
    ```

4. 如果浏览器未自动启动，请访问

    ```bash
    http://localhost:7860/
    ```

    将 `PDF` 文件拖入窗口并点击 `Translate`。

默认 WebUI 面向普通用户，首页只保留上传 PDF、翻译、预览和下载流程，不显示设置入口。

管理员如需调整服务、品牌、术语表、高级 PDF 参数或局域网并发限制，推荐修改配置目录中的 `distribution.toml`，例如：

```toml
[gui_settings]
show_settings_tab = true
settings_admin_password = "change-me"
max_concurrent_jobs = 1
max_queue_size = 8

[translation]
qps = 4
pool_max_workers = 4
```

也可以在启动时临时加入：

```bash
pdf2zh_next --gui --show-settings-tab --settings-admin-password "change-me"
```

或者使用环境变量：`PDF2ZH_SHOW_SETTINGS_TAB=true` 和 `PDF2ZH_SETTINGS_ADMIN_PASSWORD=change-me`。

5. 如果您通过 docker 部署 PDFMathTranslate，并使用 ollama 作为 PDFMathTranslate 的后端 `LLM`，则应在 "Ollama host" 中填写

   ```bash
   http://host.docker.internal:11434
   ```

<!-- <img src="./../../images/gui.gif" width="500"/> -->
<img src='./../../images/gui.gif' width="500"/>

### 环境变量

您可以通过环境变量设置源语言和目标语言：

- `PDF2ZH_LANG_FROM`: 设置源语言。默认为 "English"。
- `PDF2ZH_LANG_TO`: 设置目标语言。默认为 "Simplified Chinese"。

## 预览

<img src="./../../images/before.png" width="500"/>
<img src="./../../images/after.png" width="500"/>

<div align="right"> 
<h6><small>本页面的部分内容由 GPT 翻译，可能包含错误。</small></h6>
