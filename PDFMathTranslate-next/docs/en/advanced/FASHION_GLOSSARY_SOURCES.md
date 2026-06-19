[**Advanced**](./introduction.md) > **Fashion Glossary Sources**

---

# Fashion Glossary Sources

This branch no longer relies on a single loose CSV for fashion terminology. The built-in terminology is split into 12 glossary packs:

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

These packs are loaded automatically when `Use built-in fashion glossary` is enabled. If you also pass `--glossaries`, your customer or company glossary is layered on top of the built-in pack.

The bundled EN->ZH fashion glossary now contains 3700+ entries focused on common tech pack, BOM, detailed garment parts, measurements/POM, wash-care, testing, packaging, production merchandising, print, embroidery, labelling, garment categories, fit, silhouette, pattern-making, fabric-performance, delivery workflow, and compliance-testing samples.

## Why lightweight non-LLM workflows need a stronger glossary pack

Even if you are not using a large online model, lighter translation workflows are still more likely to drift on:

- apparel abbreviations such as `HPS`, `POM`, and `SPI`
- hyphenated tech-pack wording such as `front-placket` and `care-label`
- industry-fixed wording for fabrics, trims, QC, and care labels

That is why the current branch uses two layers:

- a built-in classified glossary pack for shared apparel terminology
- a customer-specific glossary template in `examples/fashion-customer-glossary-template.csv` for brand wording, abbreviations, and fabric-composition phrases

## Curation rules

- The glossary pack is a manually curated preset, not a bulk copy of any single external document.
- Priority is given to high-frequency terms in tech packs, measurement charts, workmanship notes, material descriptions, trim lists, AQL/QC documents, and care labels.
- Where multiple English spellings are common, the pack keeps the most common apparel-document form.

## Public reference sources

These public sources were used to cross-check categories, naming directions, and apparel-label wording:

1. NIST `Apparel Manufacturing Glossary for Application Protocol Development`
   - [https://www.nist.gov/node/739811](https://www.nist.gov/node/739811)
   - Used mainly for garment-part, construction, and QC terminology scope.

2. Fashionpedia
   - [https://fashionpedia.github.io/home/](https://fashionpedia.github.io/home/)
   - Used mainly for clothing-category, part, and attribute naming.

3. Textile Exchange Materials Matrix
   - [https://textileexchange.org/materials-matrix/](https://textileexchange.org/materials-matrix/)
   - Used mainly for fiber and material classification directions.

4. FTC labeling guide
   - [https://www.ftc.gov/business-guidance/resources/threading-your-way-through-labeling-requirements-under-textile-wool-acts](https://www.ftc.gov/business-guidance/resources/threading-your-way-through-labeling-requirements-under-textile-wool-acts)
   - Used mainly for fiber-name and label-field wording direction.

5. China national standard info platform `GB 5296.4-2012 Instructions for Use of Products - Part 4: Textile and Apparel`
   - [https://openstd.samr.gov.cn/bzgk/gb/newGbInfo?hcno=78E12DC297A27F3AB95C25986FD71586](https://openstd.samr.gov.cn/bzgk/gb/newGbInfo?hcno=78E12DC297A27F3AB95C25986FD71586)
   - Used mainly for Chinese wording direction in apparel labels and care instructions.

## Recommended maintenance model

It is best to keep future additions in two layers:

- company-wide shared terminology
- customer or brand-specific CSV files per project

This keeps private customer wording out of the global built-in pack while still letting the shared glossary stay strong.
