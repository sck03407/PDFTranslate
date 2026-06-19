from __future__ import annotations

import csv
import io
import os
from pathlib import Path

import chardet

BUILTIN_FASHION_GLOSSARY_FILENAMES = (
    "fashion-01-garment-parts.csv",
    "fashion-02-measurements.csv",
    "fashion-03-materials.csv",
    "fashion-04-construction.csv",
    "fashion-05-quality.csv",
    "fashion-06-care-labels.csv",
    "fashion-07-bom-and-techpack.csv",
    "fashion-08-washcare-and-testing.csv",
    "fashion-09-trims-and-packaging.csv",
    "fashion-10-production-and-merchandising.csv",
    "fashion-11-prints-embroidery-and-labelling.csv",
    "fashion-12-style-fit-and-silhouette.csv",
)
CUSTOMER_GLOSSARY_TEMPLATE_FILENAME = "fashion-customer-glossary-template.csv"
CUSTOMER_GLOSSARY_HEADERS = ("source", "target", "tgt_lng")
DEFAULT_CUSTOMER_GLOSSARY_TARGET_LANGUAGE = "zh"
CUSTOMER_GLOSSARY_DIR_ENV = "PDF2ZH_CUSTOMER_GLOSSARY_DIR"


FASHION_SYSTEM_PROMPT = """
You are a professional fashion-document translator responsible for translating English apparel, textile, garment construction, fit, sizing, trim, care-label, and quality-control content into fluent Simplified Chinese.

Follow all rules strictly:
1. Preserve the original structure, placeholders, tags, numbers, units, style codes, size codes, fabric compositions, and table semantics.
2. Use accurate apparel-industry terminology for garment parts, sewing operations, measurements, materials, trims, workmanship, defects, testing, and washing instructions.
3. Keep repeated technical terms consistent across the whole document.
4. When a source term is a brand name, SKU, style code, color code, measurement code, or proper noun, keep it unchanged unless a glossary explicitly provides a translation.
5. Translate concise table cells concisely. Do not add explanations or commentary.
6. If a term can be translated literally or professionally, prefer the professional garment-industry translation.
""".strip()

def get_builtin_fashion_glossary_dir() -> Path:
    return Path(__file__).resolve().parent / "assets" / "glossaries"


def get_builtin_fashion_glossary_paths() -> list[Path]:
    glossary_dir = get_builtin_fashion_glossary_dir()
    glossary_paths: list[Path] = []

    for filename in BUILTIN_FASHION_GLOSSARY_FILENAMES:
        glossary_path = glossary_dir / filename
        if glossary_path.exists():
            glossary_paths.append(glossary_path)

    return glossary_paths


def get_builtin_fashion_glossary_path() -> Path:
    glossary_paths = get_builtin_fashion_glossary_paths()
    if glossary_paths:
        return glossary_paths[0]
    return get_builtin_fashion_glossary_dir() / BUILTIN_FASHION_GLOSSARY_FILENAMES[0]


def get_bundled_customer_glossary_template_path() -> Path:
    return get_builtin_fashion_glossary_dir() / CUSTOMER_GLOSSARY_TEMPLATE_FILENAME


def get_customer_glossary_dir() -> Path:
    glossary_dir = os.getenv(CUSTOMER_GLOSSARY_DIR_ENV)
    if glossary_dir:
        return Path(glossary_dir).expanduser()

    config_dir = os.getenv("PDF2ZH_CONFIG_DIR")
    if config_dir:
        return Path(config_dir).expanduser()

    return (Path.cwd() / "config").resolve()


def _decode_glossary_bytes(content: bytes) -> str:
    encoding = chardet.detect(content)["encoding"] or "utf-8"
    return content.decode(encoding).replace("\r\n", "\n")


def load_glossary_rows(glossary_path: str | Path) -> list[list[str]]:
    path = Path(glossary_path)
    content = _decode_glossary_bytes(path.read_bytes())
    reader = csv.DictReader(io.StringIO(content), doublequote=True)

    if not reader.fieldnames or not all(
        column in reader.fieldnames for column in CUSTOMER_GLOSSARY_HEADERS[:2]
    ):
        raise ValueError(
            f"Glossary CSV {path} must contain 'source' and 'target' columns."
        )

    rows: list[list[str]] = []
    for row in reader:
        source = str(row.get("source") or "").strip()
        target = str(row.get("target") or "").strip()
        target_language = str(
            row.get("tgt_lng") or DEFAULT_CUSTOMER_GLOSSARY_TARGET_LANGUAGE
        ).strip()
        if not source and not target:
            continue
        rows.append([source, target, target_language or DEFAULT_CUSTOMER_GLOSSARY_TARGET_LANGUAGE])
    return rows


def _normalize_customer_glossary_rows(rows: list[list[str]] | None) -> list[list[str]]:
    normalized_rows: list[list[str]] = []
    for row_index, row in enumerate(rows or [], start=1):
        if isinstance(row, dict):
            source = str(row.get("source") or "").strip()
            target = str(row.get("target") or "").strip()
            target_language = str(
                row.get("tgt_lng") or DEFAULT_CUSTOMER_GLOSSARY_TARGET_LANGUAGE
            ).strip()
        else:
            values = list(row) if isinstance(row, (list, tuple)) else []
            source = str(values[0] if len(values) > 0 else "").strip()
            target = str(values[1] if len(values) > 1 else "").strip()
            target_language = str(
                values[2]
                if len(values) > 2 and values[2]
                else DEFAULT_CUSTOMER_GLOSSARY_TARGET_LANGUAGE
            ).strip()

        if not source and not target:
            continue
        if not source or not target:
            raise ValueError(
                f"Glossary row {row_index} must include both source and target."
            )
        normalized_rows.append(
            [
                source,
                target,
                target_language or DEFAULT_CUSTOMER_GLOSSARY_TARGET_LANGUAGE,
            ]
        )
    return normalized_rows


def write_glossary_rows(
    glossary_path: str | Path,
    rows: list[list[str]] | None,
) -> Path:
    path = Path(glossary_path)
    normalized_rows = _normalize_customer_glossary_rows(rows)
    path.parent.mkdir(parents=True, exist_ok=True)

    with path.open("w", encoding="utf-8-sig", newline="") as file:
        writer = csv.writer(file, lineterminator="\n")
        writer.writerow(CUSTOMER_GLOSSARY_HEADERS)
        writer.writerows(normalized_rows)
    return path


def load_customer_glossary_template_rows() -> list[list[str]]:
    return load_glossary_rows(ensure_default_customer_glossary_template())


def save_customer_glossary_template_rows(rows: list[list[str]] | None) -> Path:
    return write_glossary_rows(ensure_default_customer_glossary_template(), rows)


def restore_customer_glossary_template_rows() -> tuple[Path, list[list[str]]]:
    source_rows = load_glossary_rows(get_bundled_customer_glossary_template_path())
    saved_path = save_customer_glossary_template_rows(source_rows)
    return saved_path, source_rows


def ensure_default_customer_glossary_template() -> Path:
    target_path = get_customer_glossary_dir() / CUSTOMER_GLOSSARY_TEMPLATE_FILENAME
    source_rows = load_glossary_rows(get_bundled_customer_glossary_template_path())
    if target_path.exists():
        try:
            existing_rows = load_glossary_rows(target_path)
        except Exception:
            existing_rows = source_rows
        write_glossary_rows(target_path, existing_rows)
        return target_path

    write_glossary_rows(target_path, source_rows)
    return target_path


def normalize_glossary_files(glossary_files: str | None) -> str | None:
    if not glossary_files:
        return None

    normalized_files: list[str] = []
    seen: set[str] = set()
    for file in glossary_files.split(","):
        normalized = file.strip()
        if not normalized or normalized in seen:
            continue
        normalized_files.append(normalized)
        seen.add(normalized)

    if not normalized_files:
        return None
    return ",".join(normalized_files)


def combine_glossary_files(*glossary_file_groups: str | None) -> str | None:
    combined_files: list[str] = []
    seen: set[str] = set()

    for glossary_files in glossary_file_groups:
        normalized_group = normalize_glossary_files(glossary_files)
        if not normalized_group:
            continue
        for file in normalized_group.split(","):
            if file in seen:
                continue
            combined_files.append(file)
            seen.add(file)

    if not combined_files:
        return None
    return ",".join(combined_files)


def resolve_glossary_path(
    glossary_file: str | Path,
    *,
    config_file: str | None = None,
) -> Path:
    glossary_path = Path(glossary_file).expanduser()
    if glossary_path.is_absolute() or not config_file:
        return glossary_path

    config_path = Path(config_file).expanduser()
    return (config_path.resolve().parent / glossary_path).resolve()


def get_effective_glossary_paths(
    glossary_files: str | None,
    disable_builtin_fashion_glossary: bool,
    *,
    config_file: str | None = None,
) -> list[Path]:
    glossary_paths: list[Path] = []
    seen: set[Path] = set()
    normalized_glossary_files = normalize_glossary_files(glossary_files)

    if normalized_glossary_files:
        for file in normalized_glossary_files.split(","):
            glossary_path = resolve_glossary_path(file, config_file=config_file)
            resolved_path = glossary_path.resolve()
            if resolved_path in seen:
                continue
            glossary_paths.append(glossary_path)
            seen.add(resolved_path)

    if not disable_builtin_fashion_glossary:
        for builtin_path in get_builtin_fashion_glossary_paths():
            resolved_builtin_path = builtin_path.resolve()
            if resolved_builtin_path in seen:
                continue
            glossary_paths.append(builtin_path)
            seen.add(resolved_builtin_path)

    return glossary_paths


def get_effective_custom_system_prompt(settings) -> str | None:
    if settings.translation.custom_system_prompt:
        return settings.translation.custom_system_prompt
    if settings.translation.disable_builtin_fashion_prompt:
        return None
    return FASHION_SYSTEM_PROMPT
