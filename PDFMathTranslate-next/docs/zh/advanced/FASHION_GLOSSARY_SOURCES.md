[**高级选项**](./introduction.md) > **服装术语来源与扩展建议**

---

# 服装术语来源与扩展建议

当前分支内置的服装术语不再只是一个零散的 CSV，而是拆成了 12 个分类词包：

- `fashion-01-garment-parts.csv`
- `fashion-02-measurements.csv`
- `fashion-03-materials.csv`
- `fashion-04-construction.csv`
- `fashion-05-quality.csv`
- `fashion-06-care-labels.csv`
- `fashion-07-bom-and-techpack.csv`
- `fashion-08-washcare-and-testing.csv`
- `fashion-09-trims-and-packaging.csv`
- `fashion-10-production-and-merchandising.csv`
- `fashion-11-prints-embroidery-and-labelling.csv`
- `fashion-12-style-fit-and-silhouette.csv`

这些词包会在启用“Use built-in fashion glossary”时自动加载；如果你另外提供 `--glossaries`，系统会把你的企业词表叠加进去。

当前内置 EN->ZH 服装术语总量已扩充到 2300+ 条，重点覆盖 tech pack、BOM、洗水单、包装资料、成分唛、常见测试语句、生产跟单、印花绣花、唛标说明、款式品类、版型廓形、纸样打版、面料性能和合规测试。

## 为什么普通机器翻译 / 轻量非 LLM 路线更依赖术语包

即使你不用大型在线模型，而是选用普通机器翻译、免费服务或其他轻量路线，下面这些内容仍然很容易失真：

- 服装工艺缩写，例如 `HPS`、`POM`、`SPI`
- tech pack 常见连字符写法，例如 `front-placket`、`care-label`
- 面料、辅料、质检和洗护中的行业固定说法

所以当前实现把词表做成了两层：

- 内置分类术语包：覆盖通用服装资料的高频词
- 客户自定义词表：通过 `examples/fashion-customer-glossary-template.csv` 继续补品牌叫法、客户缩写、面料成分句式和特殊工艺词

## 词表整理原则

- 术语表是“人工整理后的预设词库”，不是对某个外部来源的整段照搬。
- 重点优先覆盖 tech pack、尺寸表、工艺说明、面料成分、辅料说明、AQL/QC 和洗护标签中的高频词。
- 对容易出现多写法的术语，优先收录服装资料里最常见的英文形式。

## 主要公开参考来源

以下公开资料用于校对分类范围、术语命名和洗护/材料用语方向：

1. NIST `Apparel Manufacturing Glossary for Application Protocol Development`
   - [https://www.nist.gov/node/739811](https://www.nist.gov/node/739811)
   - 主要参考服装制造、部位、工艺与质检相关术语。

2. Fashionpedia
   - [https://fashionpedia.github.io/home/](https://fashionpedia.github.io/home/)
   - 主要参考服装品类、部位和属性命名体系。

3. Textile Exchange Materials Matrix
   - [https://textileexchange.org/materials-matrix/](https://textileexchange.org/materials-matrix/)
   - 主要参考纤维、材料和可持续材料名称分类。

4. FTC Labeling Guide
   - [https://www.ftc.gov/business-guidance/resources/threading-your-way-through-labeling-requirements-under-textile-wool-acts](https://www.ftc.gov/business-guidance/resources/threading-your-way-through-labeling-requirements-under-textile-wool-acts)
   - 主要参考纤维名称、标签字段和服装标签合规表达。

5. 国家标准信息公共服务平台 `GB 5296.4-2012 消费品使用说明 第4部分：纺织品和服装`
   - [https://openstd.samr.gov.cn/bzgk/gb/newGbInfo?hcno=78E12DC297A27F3AB95C25986FD71586](https://openstd.samr.gov.cn/bzgk/gb/newGbInfo?hcno=78E12DC297A27F3AB95C25986FD71586)
   - 主要参考中文服装标签与维护说明的合规表述范围。

## 建议维护方式

推荐后续把新增术语分成两层维护：

- 企业公共层：放进内网统一词表，适合所有品牌通用术语
- 客户/品牌层：按项目单独维护 CSV，避免把客户私有叫法混进公共默认词包
