from __future__ import annotations

from pathlib import Path

from pdf2zh_next.config.cli_env_model import CLIEnvSettingsModel
from pdf2zh_next.fashion_defaults import combine_glossary_files
from pdf2zh_next.fashion_defaults import ensure_default_customer_glossary_template
from pdf2zh_next.fashion_defaults import load_customer_glossary_template_rows
from pdf2zh_next.fashion_defaults import save_customer_glossary_template_rows
from pdf2zh_next.http_api import _build_job_settings


def test_fastapi_job_settings_tracks_builtin_fashion_switches(tmp_path: Path):
    input_pdf = tmp_path / "input.pdf"
    input_pdf.write_bytes(b"%PDF-1.4\n")
    output_dir = tmp_path / "out"
    output_dir.mkdir()
    base_settings = CLIEnvSettingsModel(
        translation={
            "disable_builtin_fashion_prompt": True,
            "disable_builtin_fashion_glossary": True,
        }
    ).to_settings_model_for_gui()

    settings = _build_job_settings(
        base_settings,
        input_path=input_pdf,
        output_dir=output_dir,
        lang_in="en",
        lang_out="zh",
        pages=None,
        no_mono=False,
        no_dual=False,
        save_auto_extracted_glossary=False,
    )

    assert settings.translation.disable_builtin_fashion_prompt is True
    assert settings.translation.disable_builtin_fashion_glossary is True
    assert settings.pdf.watermark_output_mode == "no_watermark"


def test_fastapi_job_settings_includes_default_customer_glossary(
    tmp_path: Path,
    monkeypatch,
):
    input_pdf = tmp_path / "input.pdf"
    input_pdf.write_bytes(b"%PDF-1.4\n")
    output_dir = tmp_path / "out"
    output_dir.mkdir()
    customer_glossary = tmp_path / "fashion-customer-glossary-template.csv"
    customer_glossary.write_text(
        "source,target,tgt_lng\nself fabric,本布,zh\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(
        "pdf2zh_next.http_api.ensure_default_customer_glossary_template",
        lambda: customer_glossary,
    )

    settings = _build_job_settings(
        CLIEnvSettingsModel().to_settings_model_for_gui(),
        input_path=input_pdf,
        output_dir=output_dir,
        lang_in="en",
        lang_out="zh",
        pages=None,
        no_mono=False,
        no_dual=False,
        save_auto_extracted_glossary=False,
    )

    assert settings.translation.glossaries is not None
    assert str(customer_glossary) in settings.translation.glossaries


def test_combine_glossary_files_merges_configured_and_uploaded_glossaries(
    tmp_path: Path,
):
    configured_glossary = tmp_path / "configured.csv"
    configured_glossary.write_text("source,target\nfit,版型\n", encoding="utf-8")
    uploaded_glossary = tmp_path / "uploaded.csv"
    uploaded_glossary.write_text("source,target\nplacket,门襟\n", encoding="utf-8")

    merged = combine_glossary_files(
        str(configured_glossary),
        str(uploaded_glossary),
        str(configured_glossary),
    )

    assert merged == f"{configured_glossary},{uploaded_glossary}"


def test_customer_glossary_template_roundtrip(tmp_path: Path, monkeypatch):
    target = tmp_path / "fashion-customer-glossary-template.csv"
    source = tmp_path / "bundled.csv"
    source.write_text(
        "source,target,tgt_lng\nmock neck,高领,zh\n",
        encoding="utf-8",
    )
    monkeypatch.setattr("pdf2zh_next.fashion_defaults.DEFAULT_CONFIG_DIR", tmp_path)
    monkeypatch.setattr(
        "pdf2zh_next.fashion_defaults.get_bundled_customer_glossary_template_path",
        lambda: source,
    )

    assert ensure_default_customer_glossary_template() == target

    rows = [["mock neck", "高领", "zh"], ["self fabric", "本布", "zh"]]
    saved_path = save_customer_glossary_template_rows(rows)

    assert saved_path == target
    assert load_customer_glossary_template_rows() == rows
