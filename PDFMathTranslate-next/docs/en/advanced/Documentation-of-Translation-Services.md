[**Advanced**](./introduction.md) > **Documentation of Translation Services** _(current)_

---

### Viewing Available Translate Services via Command Line

You can confirm the available translate services and their usage by printing the help message in the command line.

```bash
pdf2zh_next -h
```

At the end of the help message, you can view detailed information about the different translation services.


---

### Translation Engine Support Policy

#### Tier 1 (Official Support)

**Tier 1 translation engines** are the engines that this repository currently intends to keep usable in its own public release workflow. Issues found in these engines should be reported through this repository.


Currently supported Tier 1 translation engines include:
1. OpenAI
2. AliyunDashScope
3. DeepSeek
4. SiliconFlow
5. Zhipu
6. OpenAICompatible

Additional note:

- `SiliconFlowFree` is still bundled in this customized branch and remains selectable from the administrator Settings page.
- It is best treated as a free trial or fallback path rather than a stable SLA-backed service.

#### Tier 2 (Community Support)

**Tier 2 translation engines** are best-effort community-supported engines.  
When these engines encounter issues, fixes may depend on contributor availability and release priorities in this repository.

All engines that are supported by the program but not explicitly listed under Tier 1 are considered Tier 2 translation engines.

#### Deprecated Engines

The following translation engines have been **deprecated** and will no longer be maintained or supported:

1. Bing
2. Google
