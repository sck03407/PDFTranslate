from __future__ import annotations

import os
import uuid
from argparse import Namespace
from datetime import datetime
from datetime import timedelta
from datetime import timezone
from unittest.mock import patch

from fastapi.testclient import TestClient

from pdf2zh_next.config.cli_env_model import CLIEnvSettingsModel
from pdf2zh_next.http_api import _resolve_launch_port
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


def test_resolve_launch_port_falls_forward_when_default_is_busy(monkeypatch):
    def fake_can_bind_port(_host, port):
        return port != 7860

    monkeypatch.setattr("pdf2zh_next.http_api._can_bind_port", fake_can_bind_port)

    assert _resolve_launch_port(7860) == 7861


def test_startup_output_history_cleanup_uses_retention_days(monkeypatch, tmp_path):
    monkeypatch.setattr("pdf2zh_next.http_api.get_gui_output_root_dir", lambda: tmp_path)

    expired_dir = tmp_path / str(uuid.uuid4())
    expired_dir.mkdir()
    recent_dir = tmp_path / str(uuid.uuid4())
    recent_dir.mkdir()

    expired_timestamp = (
        datetime.now(timezone.utc) - timedelta(days=9)
    ).timestamp()
    recent_timestamp = (
        datetime.now(timezone.utc) - timedelta(days=1)
    ).timestamp()
    os.utime(expired_dir, (expired_timestamp, expired_timestamp))
    os.utime(recent_dir, (recent_timestamp, recent_timestamp))

    app = create_app(
        _settings(output_history_retention_days=7),
        run_startup_cleanup=True,
    )

    assert expired_dir.exists() is False
    assert recent_dir.exists() is True
    assert app.state.startup_cleanup["deleted"] == 1


def test_admin_cleanup_endpoint_removes_history(monkeypatch, tmp_path):
    monkeypatch.setattr("pdf2zh_next.http_api.get_gui_output_root_dir", lambda: tmp_path)

    old_dir = tmp_path / str(uuid.uuid4())
    old_dir.mkdir()
    recent_dir = tmp_path / str(uuid.uuid4())
    recent_dir.mkdir()

    app = create_app(_settings())
    with TestClient(app) as client:
        response = client.post(
            "/api/output-history/cleanup",
            auth=("manager", "manager-pass"),
            json={"remove_all": True},
        )

    assert response.status_code == 200
    assert response.json()["deleted"] == 2
    assert old_dir.exists() is False
    assert recent_dir.exists() is False


def test_regular_user_can_translate_but_cannot_see_settings(monkeypatch, tmp_path):
    monkeypatch.setattr("pdf2zh_next.http_api.get_gui_output_root_dir", lambda: tmp_path)
    app = create_app(_settings(max_queue_size=1))

    with TestClient(app) as client:
        session = client.get("/api/session", auth=("worker", "worker-pass"))
        settings = client.get("/api/settings", auth=("worker", "worker-pass"))

    assert session.status_code == 200
    assert session.json()["settings_visible"] is False
    assert settings.status_code == 403


def test_docker_default_login_env_maps_to_regular_and_admin_roles(monkeypatch):
    for key in list(os.environ):
        if key.startswith("PDF2ZH_"):
            monkeypatch.delenv(key)
    monkeypatch.setenv("PDF2ZH_REQUIRE_GUI_LOGIN", "true")
    monkeypatch.setenv("PDF2ZH_USER_USERNAME", "user")
    monkeypatch.setenv("PDF2ZH_USER_PASSWORD", "pdftranslate")
    monkeypatch.setenv("PDF2ZH_ADMIN_USERNAME", "admin")
    monkeypatch.setenv("PDF2ZH_ADMIN_PASSWORD", "admin")

    from pdf2zh_next.config.main import ConfigManager

    manager = ConfigManager()
    with patch("argparse.ArgumentParser.parse_args", return_value=Namespace()):
        settings = manager.load_cli_config_for_gui().to_settings_model_for_gui()
    app = create_app(settings)

    with TestClient(app) as client:
        regular = client.get("/api/session", auth=("user", "pdftranslate"))
        admin = client.get("/api/session", auth=("admin", "admin"))

    assert regular.status_code == 200
    assert regular.json()["user"]["role"] == "user"
    assert regular.json()["settings_visible"] is False
    assert admin.status_code == 200
    assert admin.json()["user"]["role"] == "admin"
    assert admin.json()["settings_visible"] is True
