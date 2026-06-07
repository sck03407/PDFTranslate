# SiliconFlow

[SiliconFlow](https://siliconflow.cn) 在这个定制分支中仍可作为付费 API 翻译服务使用。

`SiliconFlowFree` 免费在线中转接口也继续保留在这个定制分支中，并且可以直接在 GUI 的服务下拉框中选择。

需要注意的是，`SiliconFlowFree` 仍属于免费中转路径，可用性和速率可能波动；如果你需要更稳定的正式生产环境，建议改用 `SiliconFlow` 付费 API。

另外，这个分支已经增加了 `CustomOpenAICompatible` 服务入口。如果你有自己的第三方 OpenAI 兼容接口，也可以直接在 GUI 中填写：

- 自定义第三方服务名称
- API 基础 URL
- 模型名
- API 密钥

这样就不需要再把供应商硬编码进程序。

### 如何使用

1. 在 [SiliconFlow](https://siliconflow.cn) 注册账号

2. 在 [SiliconFlow API Key](https://cloud.siliconflow.cn/me/account/ak) 创建 API 密钥。然后，点击密钥进行复制。

#### 命令行

```bash
pdf2zh_next --siliconflow --siliconflow-model "Pro/deepseek-ai/DeepSeek-V3" --siliconflow-api-key <your-api-key> example.pdf
```

#### Web 界面

1. "翻译选项" - **"服务"** 下拉列表：选择 "SiliconFlow"
2. "翻译选项" - **"SiliconFlow API 基础 URL"**：保持默认
3. "翻译选项" - **"要使用的 SiliconFlow 模型"**：输入 "Pro/deepseek-ai/DeepSeek-V3" 或其他模型
4. "翻译选项" - **"SiliconFlow 服务的 API 密钥"**：粘贴您的 API 密钥
5. 点击页面底部的翻译按钮开始翻译
6. 翻译完成后，您可以在页面底部的 "已翻译" 部分找到翻译好的 PDF 文件。

#### Web 界面（SiliconFlowFree）

1. "翻译选项" - **"服务"** 下拉列表：选择 "SiliconFlowFree"
2. 根据需要调整并发与水印等参数
3. 点击翻译按钮开始翻译

> [!WARNING]
> 如果你在 `SiliconFlowFree` 下看到自动术语提取阶段出现 `Expecting ',' delimiter` 之类的 JSON 解析警告，通常不是 PDF 本身损坏，而是免费中转返回的内容不是严格 JSON。当前分支已默认对 `SiliconFlowFree` 关闭自动术语提取，避免主翻译过程中反复报这一类警告；如需术语提取，建议改用 `SiliconFlow`、`OpenAICompatible` 或新的 `CustomOpenAICompatible`。
