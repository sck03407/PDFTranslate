from __future__ import annotations

import re
import time
from pathlib import Path
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from pdf2zh_next.config.cli_env_model import CLIEnvSettingsModel
from pdf2zh_next.http_api import create_app


@pytest.fixture(autouse=True)
def isolated_runtime_config(tmp_path: Path, monkeypatch):
    config_dir = tmp_path / "config"
    monkeypatch.setattr("pdf2zh_next.http_api.DEFAULT_CONFIG_DIR", config_dir)
    monkeypatch.setattr(
        "pdf2zh_next.http_api.DEFAULT_CONFIG_FILE",
        config_dir / "config.v3.toml",
    )


def _settings(**gui_overrides):
    return CLIEnvSettingsModel(
        gui_settings={
            "require_gui_login": True,
            "user_username": "worker",
            "user_password": "worker-pass",
            "admin_username": "manager",
            "admin_password": "manager-pass",
            **gui_overrides,
        }
    ).to_settings_model_for_gui()


def test_fastapi_gui_requires_login_and_hides_settings_from_regular_user():
    app = create_app(_settings())

    with TestClient(app) as client:
        assert client.get("/").status_code == 200
        anonymous_session = client.get("/api/session")
        assert anonymous_session.status_code == 401
        assert "www-authenticate" not in anonymous_session.headers

        login_response = client.post(
            "/api/login",
            json={"username": "worker", "password": "worker-pass"},
        )
        assert login_response.status_code == 200

        cookie_session = client.get("/api/session")
        assert cookie_session.status_code == 200
        assert cookie_session.json()["user"]["role"] == "user"
        assert cookie_session.json()["settings_visible"] is False
        logout_response = client.post("/api/logout")
        assert logout_response.status_code == 200
        assert client.get("/api/session").status_code == 401

        user_session = client.get(
            "/api/session",
            auth=("worker", "worker-pass"),
        )
        assert user_session.status_code == 200
        assert user_session.json()["settings_visible"] is False

        user_settings = client.get(
            "/api/settings",
            auth=("worker", "worker-pass"),
        )
        assert user_settings.status_code == 403

        admin_session = client.get(
            "/api/session",
            auth=("manager", "manager-pass"),
        )
        assert admin_session.status_code == 200
        assert admin_session.json()["settings_visible"] is True


def test_fastapi_gui_serves_react_frontend_assets():
    settings = CLIEnvSettingsModel().to_settings_model_for_gui()
    app = create_app(settings)

    with TestClient(app) as client:
        index = client.get("/")

    assert index.status_code == 200
    assert '<div id="root"></div>' in index.text
    script_match = re.search(r'src="(/assets/[^"]+\.js)"', index.text)
    style_match = re.search(r'href="(/assets/[^"]+\.css)"', index.text)
    assert script_match is not None
    assert style_match is not None

    with TestClient(app) as client:
        script = client.get(script_match.group(1))
        style = client.get(style_match.group(1))
        fallback = client.get("/settings")
        missing_api = client.get("/api/does-not-exist")

    assert script.status_code == 200
    assert "PDFTranslate" in script.text
    assert style.status_code == 200
    assert ".app-shell" in style.text
    assert fallback.status_code == 200
    assert '<div id="root"></div>' in fallback.text
    assert missing_api.status_code == 404


def test_desktop_shutdown_endpoint_requires_runtime_token(monkeypatch):
    monkeypatch.delenv("PDFTRANSLATE_SHUTDOWN_TOKEN", raising=False)
    app_without_token = create_app(CLIEnvSettingsModel().to_settings_model_for_gui())

    with TestClient(app_without_token) as client:
        unavailable = client.post("/api/desktop/shutdown")

    assert unavailable.status_code == 404

    monkeypatch.setenv("PDFTRANSLATE_SHUTDOWN_TOKEN", "desktop-secret")
    app = create_app(CLIEnvSettingsModel().to_settings_model_for_gui())

    with TestClient(app) as client:
        denied = client.post(
            "/api/desktop/shutdown",
            headers={"x-pdftranslate-shutdown-token": "wrong"},
        )
        accepted = client.post(
            "/api/desktop/shutdown",
            headers={"x-pdftranslate-shutdown-token": "desktop-secret"},
        )

    assert denied.status_code == 403
    assert accepted.status_code == 200
    assert app.state.shutdown_requested is True


def test_fastapi_gui_admin_can_patch_runtime_settings():
    app = create_app(_settings())

    with TestClient(app) as client:
        response = client.patch(
            "/api/settings",
            auth=("manager", "manager-pass"),
            json={
                "gui_settings": {"brand_name": "Internal PDFTranslate"},
                "translation": {"qps": 2, "pool_max_workers": 2},
                "pdf": {"translate_table_text": False},
            },
        )

    assert response.status_code == 200
    payload = response.json()
    assert payload["gui_settings"]["brand_name"] == "Internal PDFTranslate"
    assert payload["translation"]["qps"] == 2
    assert payload["translation"]["pool_max_workers"] == 2
    assert payload["pdf"]["translate_table_text"] is False


def test_fastapi_gui_admin_can_switch_translation_engine_settings():
    app = create_app(_settings())

    with TestClient(app) as client:
        response = client.patch(
            "/api/settings",
            auth=("manager", "manager-pass"),
            json={
                "translate_engine": "OpenAICompatible",
                "translate_engine_settings": {
                    "openai_compatible_model": "qwen-plus",
                    "openai_compatible_base_url": "https://example.test/v1",
                    "openai_compatible_api_key": "secret-key",
                    "openai_compatible_temperature": "0.2",
                    "openai_compatible_send_temperature": True,
                },
            },
        )
        readback = client.get(
            "/api/settings",
            auth=("manager", "manager-pass"),
        )

    assert response.status_code == 200
    assert response.json()["translate_engine"] == "OpenAICompatible"
    engine = next(
        item
        for item in readback.json()["translation_engines"]
        if item["name"] == "OpenAICompatible"
    )
    fields = {field["name"]: field for field in engine["fields"]}
    assert fields["openai_compatible_model"]["value"] == "qwen-plus"
    assert fields["openai_compatible_api_key"]["value"] == ""
    assert fields["openai_compatible_api_key"]["has_value"] is True


def test_fastapi_gui_admin_can_manage_users_and_change_password():
    app = create_app(_settings())

    with TestClient(app) as client:
        created = client.post(
            "/api/users",
            auth=("manager", "manager-pass"),
            json={"username": "alice", "password": "alice-pass", "role": "user"},
        )
        alice_session = client.get("/api/session", auth=("alice", "alice-pass"))
        changed = client.post(
            "/api/users/change-password",
            auth=("manager", "manager-pass"),
            json={
                "current_password": "manager-pass",
                "new_password": "new-manager-pass",
            },
        )
        old_admin = client.get("/api/session", auth=("manager", "manager-pass"))
        new_admin = client.get("/api/session", auth=("manager", "new-manager-pass"))
        deleted = client.delete(
            "/api/users/alice",
            auth=("manager", "new-manager-pass"),
        )
        alice_after_delete = client.get(
            "/api/session",
            auth=("alice", "alice-pass"),
        )

    assert created.status_code == 200
    assert alice_session.status_code == 200
    assert alice_session.json()["user"]["role"] == "user"
    assert changed.status_code == 200
    assert old_admin.status_code == 401
    assert new_admin.status_code == 200
    assert deleted.status_code == 200
    assert alice_after_delete.status_code == 401


def test_fastapi_gui_regular_user_cannot_manage_admin_resources():
    app = create_app(_settings())

    with TestClient(app) as client:
        glossary = client.get(
            "/api/glossaries/customer-template",
            auth=("worker", "worker-pass"),
        )
        cleanup = client.post(
            "/api/output-history/cleanup",
            auth=("worker", "worker-pass"),
            json={"remove_all": False},
        )
        users = client.get(
            "/api/users",
            auth=("worker", "worker-pass"),
        )

    assert glossary.status_code == 403
    assert cleanup.status_code == 403
    assert users.status_code == 403


def test_fastapi_gui_admin_can_update_customer_glossary_template(
    tmp_path: Path,
    monkeypatch,
):
    glossary_path = tmp_path / "fashion-customer-glossary-template.csv"
    monkeypatch.setattr(
        "pdf2zh_next.http_api.ensure_default_customer_glossary_template",
        lambda: glossary_path,
    )
    monkeypatch.setattr(
        "pdf2zh_next.fashion_defaults.ensure_default_customer_glossary_template",
        lambda: glossary_path,
    )

    app = create_app(_settings())

    with TestClient(app) as client:
        response = client.put(
            "/api/glossaries/customer-template",
            auth=("manager", "manager-pass"),
            json={"rows": [["mock neck", "高领", "zh"]]},
        )
        readback = client.get(
            "/api/glossaries/customer-template",
            auth=("manager", "manager-pass"),
        )

    assert response.status_code == 200
    assert response.json()["rows"] == [["mock neck", "高领", "zh"]]
    assert readback.status_code == 200
    assert readback.json()["rows"] == [["mock neck", "高领", "zh"]]


def test_fastapi_gui_translation_endpoint_uses_existing_high_level_stream(
    tmp_path: Path,
    monkeypatch,
):
    captured_settings = {}

    async def fake_translate_stream(settings, file_path):
        captured_settings["settings"] = settings
        output_dir = Path(settings.translation.output)
        output_dir.mkdir(parents=True, exist_ok=True)
        mono_pdf = output_dir / "input-mono.pdf"
        mono_pdf.write_bytes(b"%PDF-1.4\n")
        yield {"type": "progress", "progress": 30, "message": "working"}
        yield {
            "type": "finish",
            "translate_result": SimpleNamespace(
                mono_pdf_path=mono_pdf,
                dual_pdf_path=None,
                auto_extracted_glossary_path=None,
            ),
            "token_usage": {"main": {"total": 1}},
        }

    customer_glossary = tmp_path / "fashion-customer-glossary-template.csv"
    customer_glossary.write_text(
        "source,target,tgt_lng\nplacket,门襟,zh\n",
        encoding="utf-8",
    )
    monkeypatch.setattr("pdf2zh_next.http_api.get_gui_output_root_dir", lambda: tmp_path)
    monkeypatch.setattr(
        "pdf2zh_next.http_api.ensure_default_customer_glossary_template",
        lambda: customer_glossary,
    )
    monkeypatch.setattr(
        "pdf2zh_next.http_api.do_translate_async_stream",
        fake_translate_stream,
    )

    app = create_app(_settings())
    with TestClient(app) as client:
        response = client.post(
            "/api/translate",
            auth=("worker", "worker-pass"),
            files={"file": ("input.pdf", b"%PDF-1.4\n", "application/pdf")},
            data={"lang_in": "en", "lang_out": "zh"},
        )
        assert response.status_code == 200
        job_id = response.json()["id"]

        job = None
        for _ in range(20):
            job_response = client.get(
                f"/api/jobs/{job_id}",
                auth=("worker", "worker-pass"),
            )
            job = job_response.json()
            if job["status"] == "finished":
                break
            time.sleep(0.05)

        assert job is not None
        assert job["status"] == "finished"
        assert "mono" in job["files"]

        download = client.get(
            f"/api/jobs/{job_id}/files/mono",
            auth=("worker", "worker-pass"),
        )
        assert download.status_code == 200
        assert download.content.startswith(b"%PDF")
        assert str(customer_glossary) in captured_settings[
            "settings"
        ].translation.glossaries
