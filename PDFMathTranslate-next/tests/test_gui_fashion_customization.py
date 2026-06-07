import sys
from pathlib import Path

from pdf2zh_next.config.cli_env_model import CLIEnvSettingsModel


def _gui(monkeypatch):
    monkeypatch.setattr(sys, "argv", ["pytest"])
    import pdf2zh_next.gui as gui

    return gui


def _base_ui_inputs(**overrides):
    inputs = {
        "brand_name": "PDFTranslate",
        "brand_url": "",
        "service": "OpenAICompatible",
        "lang_from": "English",
        "lang_to": "Simplified Chinese",
        "page_range": "All",
        "page_input": "",
        "prompt": "",
        "ignore_cache": False,
        "no_mono": False,
        "no_dual": False,
        "dual_translate_first": False,
        "use_alternating_pages_dual": False,
        "watermark_output_mode": "No Watermark",
        "rate_limit_mode": "Custom",
        "custom_qps": 4,
        "custom_pool_workers": None,
        "min_text_length": 5,
        "rpc_doclayout": "",
        "enable_auto_term_extraction": True,
        "primary_font_family": "Auto",
        "skip_clean": False,
        "disable_rich_text_translate": False,
        "enhance_compatibility": False,
        "split_short_lines": False,
        "short_line_split_factor": 0.8,
        "translate_table_text": True,
        "skip_scanned_detection": False,
        "ocr_workaround": False,
        "max_pages_per_part": 0,
        "formular_font_pattern": "",
        "formular_char_pattern": "",
        "auto_enable_ocr_workaround": False,
        "only_include_translated_page": False,
        "merge_alternating_line_numbers": True,
        "remove_non_formula_lines": True,
        "non_formula_line_iou_threshold": 0.9,
        "figure_table_protection_threshold": 0.9,
        "skip_formula_offset_calculation": False,
        "term_service": "Follow main translation engine",
        "term_rate_limit_mode": "Custom",
        "term_rpm_input": 240,
        "term_concurrent_threads": 20,
        "term_custom_qps": 4,
        "term_custom_pool_workers": None,
        "custom_system_prompt_input": "",
        "glossaries": None,
        "save_auto_extracted_glossary": False,
        "use_builtin_fashion_prompt": True,
        "use_builtin_fashion_glossary": True,
        "openai_compatible_model": "gpt-4o-mini",
        "openai_compatible_base_url": "https://example.invalid/v1",
        "openai_compatible_api_key": "dummy-key",
        "openai_compatible_timeout": None,
        "openai_compatible_temperature": None,
        "openai_compatible_reasoning_effort": None,
        "openai_compatible_send_temperature": None,
        "openai_compatible_send_reasoning_effort": None,
        "openai_compatible_enable_json_mode": None,
    }
    inputs.update(overrides)
    return inputs


def _build_settings(tmp_path: Path, ui_inputs: dict, gui):
    input_pdf = tmp_path / "input.pdf"
    input_pdf.write_bytes(b"%PDF-1.4\n")
    output_dir = tmp_path / "out"
    output_dir.mkdir()
    return gui._build_translate_settings(
        CLIEnvSettingsModel(), input_pdf, output_dir, gui.SaveMode.never, ui_inputs
    )


def test_gui_build_settings_tracks_builtin_fashion_switches(tmp_path, monkeypatch):
    gui = _gui(monkeypatch)

    settings = _build_settings(
        tmp_path,
        _base_ui_inputs(
            use_builtin_fashion_prompt=False,
            use_builtin_fashion_glossary=False,
        ),
        gui,
    )

    assert settings.translation.disable_builtin_fashion_prompt is True
    assert settings.translation.disable_builtin_fashion_glossary is True
    assert settings.pdf.watermark_output_mode == "no_watermark"


def test_gui_build_settings_includes_default_customer_glossary(tmp_path, monkeypatch):
    gui = _gui(monkeypatch)

    settings = _build_settings(
        tmp_path,
        _base_ui_inputs(service="OpenAICompatible"),
        gui,
    )

    assert settings.translation.glossaries is not None
    assert "fashion-customer-glossary-template.csv" in settings.translation.glossaries


def test_gui_build_settings_merges_configured_and_uploaded_glossaries(
    tmp_path, monkeypatch
):
    gui = _gui(monkeypatch)
    configured_glossary = tmp_path / "configured.csv"
    configured_glossary.write_text("source,target\nfit,版型\n", encoding="utf-8")
    uploaded_glossary = tmp_path / "uploaded.csv"
    uploaded_glossary.write_text("source,target\nplacket,门襟\n", encoding="utf-8")
    input_pdf = tmp_path / "input.pdf"
    input_pdf.write_bytes(b"%PDF-1.4\n")
    output_dir = tmp_path / "out"
    output_dir.mkdir()

    settings = gui._build_translate_settings(
        CLIEnvSettingsModel(
            openaicompatible=True,
            openaicompatible_detail={
                "openai_compatible_base_url": "https://example.invalid/v1",
                "openai_compatible_api_key": "dummy-key",
                "openai_compatible_model": "gpt-4o-mini",
            },
            translation={"glossaries": str(configured_glossary)},
        ),
        input_pdf,
        output_dir,
        gui.SaveMode.never,
        _base_ui_inputs(
            service="OpenAICompatible",
            glossaries=str(uploaded_glossary),
        ),
    )

    assert settings.translation.glossaries is not None
    assert str(configured_glossary.resolve()) in settings.translation.glossaries
    assert str(uploaded_glossary) in settings.translation.glossaries


def test_gui_build_settings_persists_branding(tmp_path, monkeypatch):
    gui = _gui(monkeypatch)

    settings = _build_settings(
        tmp_path,
        _base_ui_inputs(
            brand_name="My Custom Translate",
            brand_url="https://example.com",
        ),
        gui,
    )

    assert settings.gui_settings.brand_name == "My Custom Translate"
    assert settings.gui_settings.brand_url == "https://example.com"


def test_gui_exposes_siliconflowfree_service(monkeypatch):
    gui = _gui(monkeypatch)

    assert "SiliconFlowFree" in gui.available_services


def test_gui_exposes_custom_openai_compatible_service(monkeypatch):
    gui = _gui(monkeypatch)

    assert "CustomOpenAICompatible" in gui.available_services


def test_gui_no_longer_exposes_argostranslate_service(monkeypatch):
    gui = _gui(monkeypatch)

    assert "ArgosTranslate" not in gui.available_services


def test_gui_customer_glossary_template_roundtrip(tmp_path, monkeypatch):
    gui = _gui(monkeypatch)

    monkeypatch.setattr(
        gui,
        "ensure_default_customer_glossary_template",
        lambda: tmp_path / "fashion-customer-glossary-template.csv",
    )

    rows = [["mock neck", "高领", "zh"], ["self fabric", "本布", "zh"]]
    table_update, status_update = gui.save_customer_glossary_template(rows)

    assert table_update["value"] == rows
    assert "fashion-customer-glossary-template.csv" in status_update["value"]
