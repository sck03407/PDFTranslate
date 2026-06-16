import sys
import tempfile
import uuid
from pathlib import Path


def _gui(monkeypatch):
    monkeypatch.setattr(sys, "argv", ["pytest"])
    import pdf2zh_next.gui as gui

    return gui


def _empty_state():
    return {
        "session_id": None,
        "current_task": None,
        "results": {},
        "file_order": [],
        "display_map": {},
        "parent_map": {},
        "uploaded_files": [],
    }


def test_pdf_preview_allowed_paths_exclude_broad_filesystem_paths(monkeypatch):
    gui = _gui(monkeypatch)

    allowed_paths = [Path(path).resolve() for path in gui.pdf_preview_allowed_paths]
    root_paths = {Path(path.anchor).resolve() for path in allowed_paths if path.anchor}

    assert Path.cwd().resolve() not in allowed_paths
    assert Path.home().resolve() not in allowed_paths
    assert not root_paths.intersection(allowed_paths)


def test_pdf_preview_allowed_paths_keep_accepted_preview_locations(monkeypatch):
    gui = _gui(monkeypatch)

    allowed_paths = [Path(path).resolve() for path in gui.pdf_preview_allowed_paths]
    expected_paths = {
        gui.get_gui_output_root_dir().resolve(),
        Path(tempfile.gettempdir()).resolve(),
    }

    assert set(allowed_paths) == expected_paths


def test_resolve_launch_port_falls_forward_when_default_is_busy(monkeypatch):
    gui = _gui(monkeypatch)

    def fake_can_bind_port(_host, port):
        return port != 7860

    monkeypatch.setattr(gui, "_can_bind_port", fake_can_bind_port)

    assert gui._resolve_launch_port(7860) == 7861


def test_clean_output_history_keeps_current_session(monkeypatch, tmp_path):
    gui = _gui(monkeypatch)
    monkeypatch.setattr(gui, "get_gui_output_root_dir", lambda: tmp_path)

    current_session_id = str(uuid.uuid4())
    current_dir = tmp_path / current_session_id
    current_dir.mkdir()
    old_dir = tmp_path / str(uuid.uuid4())
    old_dir.mkdir()

    status_update = gui.clean_output_history({"session_id": current_session_id})

    assert current_dir.exists() is True
    assert old_dir.exists() is False
    assert status_update["visible"] is True
    assert "Kept the current session folder." in status_update["value"]


def test_startup_output_history_cleanup_uses_retention_days(monkeypatch, tmp_path):
    gui = _gui(monkeypatch)
    monkeypatch.setattr(gui, "get_gui_output_root_dir", lambda: tmp_path)

    expired_dir = tmp_path / str(uuid.uuid4())
    expired_dir.mkdir()
    recent_dir = tmp_path / str(uuid.uuid4())
    recent_dir.mkdir()

    import os
    from datetime import datetime
    from datetime import timedelta
    from datetime import timezone

    expired_timestamp = (
        datetime.now(timezone.utc) - timedelta(days=9)
    ).timestamp()
    recent_timestamp = (
        datetime.now(timezone.utc) - timedelta(days=1)
    ).timestamp()
    os.utime(expired_dir, (expired_timestamp, expired_timestamp))
    os.utime(recent_dir, (recent_timestamp, recent_timestamp))

    message = gui._run_startup_output_history_cleanup(
        gui.CLIEnvSettingsModel(
            gui_settings={
                "auto_cleanup_output_history": True,
                "output_history_retention_days": 7,
            }
        )
    )

    assert expired_dir.exists() is False
    assert recent_dir.exists() is True
    assert message is not None
    assert "older than 7 day(s)" in message


def test_settings_entry_is_hidden_by_default(monkeypatch):
    gui = _gui(monkeypatch)
    default_settings = gui.CLIEnvSettingsModel()

    assert gui._settings_entry_enabled(default_settings) is False
    assert gui._settings_unlock_required(default_settings) is False


def test_hidden_settings_sidebar_css_keeps_gradio_hide_class(monkeypatch):
    gui = _gui(monkeypatch)

    assert ".sidebar-nav.hide" in gui.custom_css
    assert "display: none !important" in gui.custom_css


def test_settings_entry_can_require_admin_password(monkeypatch):
    gui = _gui(monkeypatch)
    admin_settings = gui.CLIEnvSettingsModel(
        gui_settings={
            "show_settings_tab": True,
            "settings_admin_password": "secret",
        }
    )

    assert gui._settings_entry_enabled(admin_settings) is True
    assert gui._settings_unlock_required(admin_settings) is True
    assert gui.verify_settings_admin_password("secret", admin_settings) is True
    assert gui.verify_settings_admin_password("wrong", admin_settings) is False


def test_on_file_upload_empty_list_returns_all_declared_outputs(monkeypatch):
    gui = _gui(monkeypatch)
    state = _empty_state()

    result = gui.on_file_upload([], state)

    assert len(result) == 3
    assert result[0]["choices"] == []
    assert result[0]["value"] is None
    assert result[0]["visible"] is False
    assert result[1] is state
    assert result[2]["value"] == ""
    assert result[2]["visible"] is False


def test_on_file_upload_none_returns_all_declared_outputs(monkeypatch):
    gui = _gui(monkeypatch)
    state = _empty_state()

    result = gui.on_file_upload(None, state)

    assert len(result) == 3
    assert result[0]["choices"] == []
    assert result[0]["value"] is None
    assert result[0]["visible"] is False
    assert result[1] is state
    assert result[2]["value"] == ""
    assert result[2]["visible"] is False
