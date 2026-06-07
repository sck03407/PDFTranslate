# SiliconFlow

[SiliconFlow](https://siliconflow.cn) can still be used as a paid API-based translation service in this customized branch.

The free `SiliconFlowFree` relay path is also kept in this customized branch and remains selectable in the GUI service dropdown.

Please note that `SiliconFlowFree` is still a free relay path, so availability and rate limits may fluctuate. For a more stable production workflow, prefer the paid `SiliconFlow` API.

### Usage

1. Register an account at [SiliconFlow](https://siliconflow.cn)

2. Create an API key at [SiliconFlow API Key](https://cloud.siliconflow.cn/me/account/ak). Then, click on the key to copy it.

#### cli

```bash
pdf2zh_next --siliconflow --siliconflow-model "Pro/deepseek-ai/DeepSeek-V3" --siliconflow-api-key <your-api-key> example.pdf
```

#### webui

1. "Translation Options" - **"Service"** dropdown list: Select "SiliconFlow"
2. "Translation Options" - **"Base URL for SiliconFlow API"**: Keep default
3. "Translation Options" - **"SiliconFlow model to use"**: Enter "Pro/deepseek-ai/DeepSeek-V3" or other models
4. "Translation Options" - **"API key for SiliconFlow service"**: Paste your API key
5. Click the Translate button at the bottom of the page to start translation
6. After translation is complete, you can find the translated PDF file in the "Translated" section at the bottom of the page.

#### webui (SiliconFlowFree)

1. "Translation Options" - **"Service"** dropdown list: Select "SiliconFlowFree"
2. Adjust concurrency, watermark, and other options as needed
3. Click Translate to start

