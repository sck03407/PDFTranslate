from __future__ import annotations

import re
import time
from pathlib import Path
from types import SimpleNamespace

from fastapi.testclient import TestClient

from pdf2zh_next.config.cli_env_model import CLIEnvSettingsModel
from pdf2zh_next.http_api import create_app


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
        assert client.get("/api/session").status_code == 401

        login_response = client.post(
            "/api/login",
            json={"username": "worker", "password": "worker-pass"},
        )
        assert login_response.status_code == 200

        cookie_session = client.get("/api/session")
        assert cookie_session.status_code == 200
        assert cookie_session.json()["user"]["role"] == "user"
        assert cookie_session.json()["settings_visible"] is False

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

    assert glossary.status_code == 403
    assert cleanup.status_code == 403


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
