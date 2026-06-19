from __future__ import annotations

from pdf2zh_next.config.cli_env_model import CLIEnvSettingsModel
from pdf2zh_next.config.translate_engine_model import (
    TERM_EXTRACTION_ENGINE_METADATA_MAP,
)
from pdf2zh_next.config.translate_engine_model import DeepSeekSettings


def test_deepseek_thinking_field_declares_mode_dropdown():
    mode_field = DeepSeekSettings.model_fields["deepseek_thinking_mode"]

    assert mode_field.default is None
    assert mode_field.json_schema_extra["gui"] == {
        "widget": "dropdown",
        "choices": [
            ("Unset", None),
            ("enabled", "enabled"),
            ("disabled", "disabled"),
        ],
        "preserve_current_value": True,
    }


def test_deepseek_reasoning_effort_metadata_controls_visibility():
    field = DeepSeekSettings.model_fields["deepseek_reasoning_effort"]

    assert field.json_schema_extra["gui"] == {
        "widget": "dropdown",
        "choices": ["high", "max"],
        "default_on_show": "high",
        "visible_when": {
            "field": "deepseek_thinking_mode",
            "equals": "enabled",
        },
        "preserve_current_value": True,
    }


def test_term_deepseek_metadata_preserves_prefixed_visibility():
    term_model = TERM_EXTRACTION_ENGINE_METADATA_MAP[
        "DeepSeek"
    ].term_setting_model_type
    term_field = term_model.model_fields["term_deepseek_reasoning_effort"]

    assert term_field.json_schema_extra["gui"]["widget"] == "dropdown"
    assert term_field.json_schema_extra["gui"]["choices"] == ["high", "max"]
    assert term_field.json_schema_extra["gui"]["visible_when"] == {
        "field": "deepseek_thinking_mode",
        "equals": "enabled",
    }


def test_unforced_deepseek_omits_thinking_body():
    settings = CLIEnvSettingsModel(
        deepseek=True,
        deepseek_detail={
            "deepseek_api_key": "dummy-key",
            "deepseek_reasoning_effort": "max",
        },
    ).to_settings_model()
    settings.validate_settings()

    assert settings.translate_engine_settings._openai_extra_body is None
    assert settings.translate_engine_settings.openai_send_reasoning_effort is None
    assert settings.translate_engine_settings.openai_reasoning_effort is None


def test_disabled_deepseek_omits_reasoning_effort():
    settings = CLIEnvSettingsModel(
        deepseek=True,
        deepseek_detail={
            "deepseek_model": "deepseek-v4-flash",
            "deepseek_api_key": "dummy-key",
            "deepseek_thinking_mode": "disabled",
            "deepseek_reasoning_effort": "max",
        },
    ).to_settings_model()
    settings.validate_settings()

    assert settings.translate_engine_settings._openai_extra_body == {
        "thinking": {"type": "disabled"}
    }
    assert settings.translate_engine_settings.openai_send_reasoning_effort is None
    assert settings.translate_engine_settings.openai_reasoning_effort is None


def test_enabled_deepseek_sets_reasoning_effort():
    settings = CLIEnvSettingsModel(
        deepseek=True,
        deepseek_detail={
            "deepseek_model": "deepseek-v4-flash",
            "deepseek_api_key": "dummy-key",
            "deepseek_thinking_mode": "enabled",
            "deepseek_reasoning_effort": "max",
        },
    ).to_settings_model()
    settings.validate_settings()

    assert settings.translate_engine_settings._openai_extra_body == {
        "thinking": {"type": "enabled"}
    }
    assert settings.translate_engine_settings.openai_send_reasoning_effort is True
    assert settings.translate_engine_settings.openai_reasoning_effort == "max"


def test_term_deepseek_uses_same_thinking_mode_control():
    settings = CLIEnvSettingsModel(
        deepseek=True,
        deepseek_detail={
            "deepseek_model": "deepseek-v4-flash",
            "deepseek_api_key": "dummy-key",
        },
        term_deepseek=True,
        term_deepseek_detail={
            "term_deepseek_model": "deepseek-v4-flash",
            "term_deepseek_api_key": "dummy-key",
            "term_deepseek_thinking_mode": "enabled",
            "term_deepseek_reasoning_effort": "max",
        },
    ).to_settings_model()
    settings.validate_settings()

    assert settings.term_extraction_engine_settings._openai_extra_body == {
        "thinking": {"type": "enabled"}
    }
    assert settings.term_extraction_engine_settings.openai_send_reasoning_effort is True
    assert settings.term_extraction_engine_settings.openai_reasoning_effort == "max"


def test_deepseek_thinking_mode_rejects_unknown_value():
    settings = DeepSeekSettings(
        deepseek_api_key="dummy-key",
        deepseek_thinking_mode="auto",
    )

    try:
        settings.validate_settings()
    except ValueError as exc:
        assert str(exc) == "DeepSeek thinking mode must be enabled or disabled"
    else:
        raise AssertionError("Expected unknown thinking mode to fail")
