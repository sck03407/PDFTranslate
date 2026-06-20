from __future__ import annotations

import asyncio
import csv
import json
import logging
import os
import secrets
import socket
import time
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from typing import get_args

import uvicorn
from fastapi import Depends
from fastapi import FastAPI
from fastapi import File
from fastapi import Form
from fastapi import HTTPException
from fastapi import Request
from fastapi import Response
from fastapi import UploadFile
from fastapi import status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.responses import HTMLResponse
from fastapi.responses import JSONResponse
from fastapi.responses import StreamingResponse
from fastapi.security import HTTPBasic
from fastapi.security import HTTPBasicCredentials
from pydantic import BaseModel
from pydantic import Field

from pdf2zh_next.config.main import ConfigManager
from pdf2zh_next.config.model import SettingsModel
from pdf2zh_next.config.translate_engine_model import GUI_PASSWORD_FIELDS
from pdf2zh_next.config.translate_engine_model import TRANSLATION_ENGINE_METADATA
from pdf2zh_next.config.translate_engine_model import TRANSLATION_ENGINE_METADATA_MAP
from pdf2zh_next.const import DEFAULT_CONFIG_DIR
from pdf2zh_next.const import DEFAULT_CONFIG_FILE
from pdf2zh_next.fashion_defaults import combine_glossary_files
from pdf2zh_next.fashion_defaults import ensure_default_customer_glossary_template
from pdf2zh_next.fashion_defaults import get_builtin_fashion_glossary_paths
from pdf2zh_next.fashion_defaults import load_glossary_rows
from pdf2zh_next.fashion_defaults import restore_customer_glossary_template_rows
from pdf2zh_next.fashion_defaults import save_customer_glossary_template_rows
from pdf2zh_next.high_level import TranslationError
from pdf2zh_next.high_level import do_translate_async_stream
from pdf2zh_next.output_cleanup import cleanup_session_output_dirs
from pdf2zh_next.output_cleanup import get_gui_output_root_dir

logger = logging.getLogger(__name__)

WEB_FRONTEND_DIR = Path(__file__).resolve().parent / "web_frontend"
INDEX_HTML = WEB_FRONTEND_DIR / "index.html"
SESSION_COOKIE_NAME = "pdftranslate_session"
GUI_USERS_FILENAME = "gui-users.csv"
DESKTOP_SHUTDOWN_TOKEN_ENV = "PDFTRANSLATE_SHUTDOWN_TOKEN"
DESKTOP_SHUTDOWN_TOKEN_HEADER = "x-pdftranslate-shutdown-token"

security = HTTPBasic(auto_error=False)


class ApiUser(BaseModel):
    username: str | None
    role: str
    authenticated: bool

    @property
    def is_admin(self) -> bool:
        return self.role == "admin"


class RuntimeSettingsUpdate(BaseModel):
    gui_settings: dict[str, Any] = Field(default_factory=dict)
    translation: dict[str, Any] = Field(default_factory=dict)
    pdf: dict[str, Any] = Field(default_factory=dict)
    translate_engine: str | None = None
    translate_engine_settings: dict[str, Any] = Field(default_factory=dict)


class LoginRequest(BaseModel):
    username: str
    password: str


class PasswordChangeRequest(BaseModel):
    current_password: str = ""
    new_password: str


class ManagedUserUpdate(BaseModel):
    username: str
    password: str | None = None
    role: str = "user"


class CustomerGlossaryUpdate(BaseModel):
    rows: list[list[str]] = Field(default_factory=list)


class OutputCleanupRequest(BaseModel):
    remove_all: bool = False


@dataclass
class TranslationJob:
    id: str
    filename: str
    input_path: Path
    output_dir: Path
    settings: SettingsModel
    created_at: float
    updated_at: float
    status: str = "queued"
    progress: float = 0.0
    message: str = "Queued"
    events: list[dict[str, Any]] | None = None
    files: dict[str, str] | None = None
    token_usage: dict[str, Any] | None = None
    error: str | None = None

    def __post_init__(self) -> None:
        self.events = []
        self.files = {}
        self.token_usage = {}

    def snapshot(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "filename": self.filename,
            "status": self.status,
            "progress": self.progress,
            "message": self.message,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "files": self.files or {},
            "token_usage": self.token_usage or {},
            "error": self.error,
        }


def _clean_auth_value(value: str | None) -> str:
    return (value or "").strip()


def _resolve_auth_file_path(
    auth_file: str | None,
    *,
    config_file: str | None = None,
) -> Path | None:
    if not auth_file:
        return None
    path = Path(auth_file).expanduser()
    if path.is_absolute():
        return path
    if config_file:
        return Path(config_file).expanduser().resolve().parent / path
    return DEFAULT_CONFIG_DIR / path


def _parse_auth_file(
    auth_file: str | None,
    *,
    config_file: str | None = None,
) -> dict[str, tuple[str, str | None]]:
    path = _resolve_auth_file_path(auth_file, config_file=config_file)
    if path is None:
        return {}
    if not path.exists():
        logger.warning("Configured auth file does not exist: %s", path)
        return {}

    users: dict[str, tuple[str, str | None]] = {}
    for row in csv.reader(path.read_text(encoding="utf-8").splitlines()):
        if not row:
            continue
        if str(row[0]).lstrip().startswith("#"):
            continue
        parts = [str(part).strip() for part in row[:3]]
        if len(parts) < 2 or not parts[0] or not parts[1]:
            continue
        role = parts[2] if len(parts) >= 3 and parts[2] in {"admin", "user"} else None
        users[parts[0]] = (parts[1], role)
    return users


def _build_auth_users(settings: SettingsModel) -> dict[str, tuple[str, str]]:
    users: dict[str, tuple[str, str]] = {}
    gui_settings = settings.gui_settings

    if gui_settings.require_gui_login:
        regular_username = _clean_auth_value(gui_settings.user_username)
        regular_password = _clean_auth_value(gui_settings.user_password)
        admin_username = _clean_auth_value(gui_settings.admin_username)
        admin_password = _clean_auth_value(gui_settings.admin_password)
        if regular_username and regular_password:
            users[regular_username] = (regular_password, "user")
        if admin_username and admin_password:
            users[admin_username] = (admin_password, "admin")

    for username, (password, configured_role) in _parse_auth_file(
        gui_settings.auth_file,
        config_file=settings.config_file,
    ).items():
        role = configured_role or (
            "admin"
            if username == _clean_auth_value(gui_settings.admin_username)
            else "user"
        )
        users[username] = (password, role)

    return users


def _auth_required(settings: SettingsModel) -> bool:
    return bool(settings.gui_settings.require_gui_login or settings.gui_settings.auth_file)


def _unauthorized() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Authentication required",
    )


def _make_current_user_dependency(settings: SettingsModel):
    auth_users = _build_auth_users(settings)
    auth_required = _auth_required(settings)
    sessions: dict[str, ApiUser] = {}

    if auth_required and not auth_users:
        raise RuntimeError(
            "GUI login is enabled, but no valid GUI users are configured."
        )

    def authenticate(username: str, password: str) -> ApiUser | None:
        configured = auth_users.get(username)
        if not configured:
            return None
        expected_password, role = configured
        if not secrets.compare_digest(password, expected_password):
            return None
        return ApiUser(
            username=username,
            role=role,
            authenticated=True,
        )

    async def current_user(
        request: Request,
        credentials: HTTPBasicCredentials | None = Depends(security),
    ) -> ApiUser:
        if not auth_required:
            return ApiUser(username=None, role="admin", authenticated=False)
        if credentials is not None:
            user = authenticate(credentials.username, credentials.password)
            if user is None:
                raise _unauthorized()
            return user

        session_token = request.cookies.get(SESSION_COOKIE_NAME)
        if session_token:
            session_user = sessions.get(session_token)
            if session_user:
                return session_user
        raise _unauthorized()

    current_user.sessions = sessions
    current_user.authenticate = authenticate
    current_user.auth_required = auth_required
    current_user.auth_users = auth_users

    return current_user


def _require_admin(user: ApiUser) -> ApiUser:
    if not user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Administrator permission required",
        )
    return user


def _frontend_file(filename: str | Path) -> FileResponse:
    path = (WEB_FRONTEND_DIR / filename).resolve()
    if not path.is_relative_to(WEB_FRONTEND_DIR.resolve()) or not path.exists():
        raise HTTPException(status_code=404, detail="Asset not found")
    return FileResponse(path)


def _frontend_index() -> HTMLResponse:
    if not INDEX_HTML.exists():
        raise HTTPException(status_code=404, detail="Frontend is missing")
    return HTMLResponse(INDEX_HTML.read_text(encoding="utf-8"))


def _serialize_value(value: Any) -> Any:
    if value is None or isinstance(value, str | int | float | bool):
        return value
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, dict):
        return {str(key): _serialize_value(item) for key, item in value.items()}
    if isinstance(value, list | tuple | set):
        return [_serialize_value(item) for item in value]
    return str(value)


def _serialize_event(event: dict[str, Any]) -> dict[str, Any]:
    serialized = _serialize_value(event)
    if not isinstance(serialized, dict):
        return {"type": "message", "message": str(serialized)}
    serialized.pop("translate_result", None)
    return serialized


def _event_progress(event: dict[str, Any], fallback: float) -> float:
    for key in ("progress", "percent", "completed_percent"):
        value = event.get(key)
        if isinstance(value, int | float):
            return max(0.0, min(float(value), 100.0))
    return fallback


def _safe_filename(filename: str | None) -> str:
    name = Path(filename or "document.pdf").name
    if not name.lower().endswith(".pdf"):
        name = f"{Path(name).stem or 'document'}.pdf"
    return name


def _first_existing_result_path(result: Any, *attribute_names: str) -> Path | None:
    for attribute_name in attribute_names:
        value = getattr(result, attribute_name, None)
        if value and Path(value).exists():
            return Path(value)
    return None


def _translation_result_files(result: Any) -> dict[str, str]:
    candidates = {
        "mono": ("no_watermark_mono_pdf_path", "mono_pdf_path"),
        "dual": ("no_watermark_dual_pdf_path", "dual_pdf_path"),
        "glossary": ("auto_extracted_glossary_path",),
    }
    files: dict[str, str] = {}
    for key, attribute_names in candidates.items():
        path = _first_existing_result_path(result, *attribute_names)
        if path:
            files[key] = str(path)
    return files


def _selected_engine_name(settings: SettingsModel) -> str | None:
    if settings.translate_engine_settings is None:
        return None
    return settings.translate_engine_settings.translate_engine_type


def _engine_supports_customer_glossary(settings: SettingsModel) -> bool:
    engine_name = _selected_engine_name(settings)
    if not engine_name:
        return False
    metadata = TRANSLATION_ENGINE_METADATA_MAP.get(engine_name)
    return bool(metadata and metadata.support_llm)


def _default_customer_glossary_file(settings: SettingsModel) -> str | None:
    if not _engine_supports_customer_glossary(settings):
        return None
    return str(ensure_default_customer_glossary_template())


def _with_default_customer_glossary(settings: SettingsModel) -> None:
    default_glossary = _default_customer_glossary_file(settings)
    if default_glossary:
        settings.translation.glossaries = combine_glossary_files(
            settings.translation.glossaries,
            default_glossary,
        )


def _run_startup_output_history_cleanup(settings: SettingsModel) -> dict[str, Any] | None:
    if not settings.gui_settings.auto_cleanup_output_history:
        return None
    result = cleanup_session_output_dirs(
        base_dir=get_gui_output_root_dir(),
        older_than_days=settings.gui_settings.output_history_retention_days,
    )
    if result.deleted_dirs:
        logger.info(
            "Removed %s expired WebUI output session(s) older than %s day(s).",
            len(result.deleted_dirs),
            settings.gui_settings.output_history_retention_days,
        )
    return {
        "base_dir": str(result.base_dir),
        "deleted": len(result.deleted_dirs),
        "kept": len(result.kept_dirs),
        "skipped": len(result.skipped_non_session_entries),
        "errors": result.errors,
    }


async def _save_upload(upload: UploadFile, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    content = await upload.read()
    if not content:
        raise HTTPException(status_code=400, detail="Uploaded PDF is empty")
    destination.write_bytes(content)


def _build_job_settings(
    base_settings: SettingsModel,
    *,
    input_path: Path,
    output_dir: Path,
    lang_in: str | None,
    lang_out: str | None,
    pages: str | None,
    no_mono: bool,
    no_dual: bool,
    save_auto_extracted_glossary: bool,
) -> SettingsModel:
    job_settings = base_settings.clone()
    job_settings.basic.input_files = {str(input_path)}
    job_settings.basic.gui = False
    job_settings.translation.output = str(output_dir)
    job_settings.translation.lang_in = lang_in or job_settings.translation.lang_in
    job_settings.translation.lang_out = lang_out or job_settings.translation.lang_out
    _with_default_customer_glossary(job_settings)
    job_settings.translation.save_auto_extracted_glossary = (
        save_auto_extracted_glossary
    )
    job_settings.pdf.pages = pages or None
    job_settings.pdf.no_mono = no_mono
    job_settings.pdf.no_dual = no_dual
    return job_settings


async def _run_translation_job(app: FastAPI, job: TranslationJob) -> None:
    semaphore: asyncio.Semaphore = app.state.translation_semaphore

    async with semaphore:
        job.status = "running"
        job.updated_at = time.time()
        job.message = "Running"

        try:
            async for event in do_translate_async_stream(job.settings, job.input_path):
                event_type = event.get("type", "message")
                job.progress = _event_progress(event, job.progress)
                serialized_event = _serialize_event(event)
                job.events.append(serialized_event)
                job.updated_at = time.time()

                if event_type == "finish":
                    result = event["translate_result"]
                    job.files = _translation_result_files(result)
                    job.token_usage = _serialize_value(event.get("token_usage", {}))
                    job.status = "finished"
                    job.progress = 100.0
                    job.message = "Finished"
                    job.updated_at = time.time()
                    break

                if event_type == "error":
                    job.status = "error"
                    job.error = str(event.get("error") or "Translation failed")
                    job.message = job.error
                    job.updated_at = time.time()
                    break
        except TranslationError as exc:
            job.status = "error"
            job.error = str(exc)
            job.message = job.error
            job.events.append({"type": "error", "error": job.error})
            job.updated_at = time.time()
        except Exception as exc:
            logger.exception("FastAPI translation job failed")
            job.status = "error"
            job.error = str(exc)
            job.message = job.error
            job.events.append({"type": "error", "error": job.error})
            job.updated_at = time.time()


def _count_queued_jobs(jobs: dict[str, TranslationJob]) -> int:
    return sum(1 for job in jobs.values() if job.status == "queued")


def _annotation_includes(annotation: Any, target: type) -> bool:
    if annotation is target:
        return True
    return any(_annotation_includes(arg, target) for arg in get_args(annotation))


def _field_allows_none(annotation: Any) -> bool:
    if annotation is None or annotation is type(None):
        return True
    return any(_field_allows_none(arg) for arg in get_args(annotation))


def _engine_field_input_type(field_name: str, field: Any) -> str:
    if field_name in GUI_PASSWORD_FIELDS:
        return "password"
    annotation = field.annotation
    if _annotation_includes(annotation, bool):
        return "checkbox"
    if _annotation_includes(annotation, int) or _annotation_includes(annotation, float):
        return "number"
    return "text"


def _engine_field_choices(field: Any) -> list[dict[str, Any]] | None:
    gui_extra = (field.json_schema_extra or {}).get("gui", {})
    choices = gui_extra.get("choices")
    if not choices:
        return None

    normalized_choices = []
    for choice in choices:
        if isinstance(choice, (list, tuple)) and len(choice) == 2:
            label, value = choice
        else:
            label = value = choice
        normalized_choices.append({"label": str(label), "value": _serialize_value(value)})
    return normalized_choices


def _translation_engine_fields(settings: SettingsModel, engine_name: str) -> list[dict[str, Any]]:
    metadata = TRANSLATION_ENGINE_METADATA_MAP[engine_name]
    if _selected_engine_name(settings) == engine_name and settings.translate_engine_settings:
        detail_settings = settings.translate_engine_settings
    else:
        detail_settings = metadata.setting_model_type()

    fields = []
    for field_name, field in metadata.setting_model_type.model_fields.items():
        if field_name in {"translate_engine_type", "support_llm"}:
            continue
        value = getattr(detail_settings, field_name)
        is_password = field_name in GUI_PASSWORD_FIELDS
        fields.append(
            {
                "name": field_name,
                "label": field.description or field_name.replace("_", " "),
                "input_type": _engine_field_input_type(field_name, field),
                "value": "" if is_password else _serialize_value(value),
                "secret": is_password,
                "has_value": bool(value) if is_password else False,
                "choices": _engine_field_choices(field),
            }
        )
    return fields


def _translation_engine_options(settings: SettingsModel) -> list[dict[str, Any]]:
    return [
        {
            "name": metadata.translate_engine_type,
            "support_llm": metadata.support_llm,
            "fields": _translation_engine_fields(
                settings,
                metadata.translate_engine_type,
            ),
        }
        for metadata in TRANSLATION_ENGINE_METADATA
    ]


def _coerce_engine_value(field: Any, value: Any) -> Any:
    if value == "" and _field_allows_none(field.annotation):
        return None
    return value


def _apply_translation_engine_update(
    settings: SettingsModel,
    engine_name: str | None,
    engine_values: dict[str, Any],
) -> None:
    if engine_name is None and not engine_values:
        return

    selected_engine = engine_name or _selected_engine_name(settings)
    if not selected_engine or selected_engine not in TRANSLATION_ENGINE_METADATA_MAP:
        raise HTTPException(status_code=400, detail="Unsupported translation engine")

    metadata = TRANSLATION_ENGINE_METADATA_MAP[selected_engine]
    model_type = metadata.setting_model_type
    current_settings = (
        settings.translate_engine_settings
        if _selected_engine_name(settings) == selected_engine
        else None
    )
    merged_values = model_type().model_dump()
    if current_settings is not None:
        merged_values.update(current_settings.model_dump())

    for field_name, value in engine_values.items():
        if field_name not in model_type.model_fields:
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported translation engine field: {field_name}",
            )
        if field_name in {"translate_engine_type", "support_llm"}:
            continue
        if (
            field_name in GUI_PASSWORD_FIELDS
            and value in (None, "")
            and current_settings is not None
        ):
            continue
        merged_values[field_name] = _coerce_engine_value(
            model_type.model_fields[field_name],
            value,
        )

    merged_values["translate_engine_type"] = selected_engine
    settings.translate_engine_settings = model_type(**merged_values)


def _list_managed_users(auth_users: dict[str, tuple[str, str]]) -> list[dict[str, str]]:
    return [
        {"username": username, "role": role}
        for username, (_password, role) in sorted(auth_users.items())
    ]


def _require_valid_managed_user(update: ManagedUserUpdate) -> tuple[str, str]:
    username = _clean_auth_value(update.username)
    role = _clean_auth_value(update.role or "user")
    if not username:
        raise HTTPException(status_code=400, detail="Username is required")
    if role not in {"admin", "user"}:
        raise HTTPException(status_code=400, detail="Role must be admin or user")
    return username, role


def _ensure_another_admin(
    auth_users: dict[str, tuple[str, str]],
    username: str,
) -> None:
    for candidate_username, (_password, role) in auth_users.items():
        if candidate_username != username and role == "admin":
            return
    raise HTTPException(status_code=400, detail="At least one administrator is required")


def _sync_primary_gui_credentials(
    settings: SettingsModel,
    username: str,
    password: str | None,
    role: str,
) -> None:
    if password is None:
        return
    if role == "admin" and username == settings.gui_settings.admin_username:
        settings.gui_settings.admin_password = password
    if role == "user" and username == settings.gui_settings.user_username:
        settings.gui_settings.user_password = password


def _refresh_user_sessions(
    sessions: dict[str, ApiUser],
    username: str,
    role: str | None,
) -> None:
    for token, session_user in list(sessions.items()):
        if session_user.username != username:
            continue
        if role is None:
            sessions.pop(token, None)
        else:
            sessions[token] = ApiUser(
                username=username,
                role=role,
                authenticated=True,
            )


def _runtime_config_content(settings: SettingsModel) -> dict[str, Any]:
    content = settings.model_dump(
        mode="json",
        exclude={
            "config_file",
            "translate_engine_settings",
            "term_extraction_engine_settings",
        },
    )
    content["basic"]["input_files"] = []

    selected_engine = _selected_engine_name(settings)
    for metadata in TRANSLATION_ENGINE_METADATA:
        content[metadata.cli_flag_name] = metadata.translate_engine_type == selected_engine
        if (
            metadata.cli_detail_field_name
            and settings.translate_engine_settings
            and metadata.translate_engine_type == selected_engine
        ):
            content[metadata.cli_detail_field_name] = (
                settings.translate_engine_settings.model_dump(mode="json")
            )

    return content


def _runtime_config_file(settings: SettingsModel) -> Path:
    config_file = _clean_auth_value(settings.config_file)
    if config_file:
        return Path(config_file).expanduser()
    return DEFAULT_CONFIG_FILE


def _persist_runtime_config(settings: SettingsModel) -> None:
    config_file = _runtime_config_file(settings)
    config_file.parent.mkdir(parents=True, exist_ok=True)
    content = _runtime_config_content(settings)
    manager = ConfigManager()
    temp_config_file = config_file.with_name(f"{config_file.name}.temp")
    manager._write_toml_file(temp_config_file, content)
    temp_config_file.replace(config_file)


def _managed_users_file(settings: SettingsModel) -> Path:
    auth_file = _resolve_auth_file_path(
        settings.gui_settings.auth_file,
        config_file=settings.config_file,
    )
    if auth_file is not None:
        return auth_file
    return _runtime_config_file(settings).parent / GUI_USERS_FILENAME


def _persist_managed_users(
    settings: SettingsModel,
    auth_users: dict[str, tuple[str, str]],
) -> None:
    user_file = _managed_users_file(settings)
    user_file.parent.mkdir(parents=True, exist_ok=True)
    with user_file.open("w", encoding="utf-8", newline="") as file:
        file.write("# username,password,role\n")
        writer = csv.writer(file, lineterminator="\n")
        for username, (password, role) in sorted(auth_users.items()):
            writer.writerow([username, password, role])
    try:
        if user_file.resolve().parent == _runtime_config_file(settings).parent.resolve():
            settings.gui_settings.auth_file = user_file.name
        else:
            settings.gui_settings.auth_file = str(user_file)
    except OSError:
        settings.gui_settings.auth_file = str(user_file)
    _persist_runtime_config(settings)


def _settings_snapshot(settings: SettingsModel) -> dict[str, Any]:
    return {
        "gui_settings": {
            "brand_name": settings.gui_settings.brand_name,
            "brand_url": settings.gui_settings.brand_url,
            "require_gui_login": settings.gui_settings.require_gui_login,
            "user_username": settings.gui_settings.user_username,
            "admin_username": settings.gui_settings.admin_username,
            "max_concurrent_jobs": settings.gui_settings.max_concurrent_jobs,
            "max_queue_size": settings.gui_settings.max_queue_size,
            "auto_cleanup_output_history": settings.gui_settings.auto_cleanup_output_history,
            "output_history_retention_days": settings.gui_settings.output_history_retention_days,
        },
        "translation": {
            "lang_in": settings.translation.lang_in,
            "lang_out": settings.translation.lang_out,
            "qps": settings.translation.qps,
            "pool_max_workers": settings.translation.pool_max_workers,
            "term_qps": settings.translation.term_qps,
            "term_pool_max_workers": settings.translation.term_pool_max_workers,
            "ignore_cache": settings.translation.ignore_cache,
            "custom_system_prompt": settings.translation.custom_system_prompt,
            "glossaries": settings.translation.glossaries,
            "rpc_doclayout": settings.translation.rpc_doclayout,
            "disable_builtin_fashion_glossary": settings.translation.disable_builtin_fashion_glossary,
            "disable_builtin_fashion_prompt": settings.translation.disable_builtin_fashion_prompt,
            "save_auto_extracted_glossary": settings.translation.save_auto_extracted_glossary,
            "no_auto_extract_glossary": settings.translation.no_auto_extract_glossary,
            "min_text_length": settings.translation.min_text_length,
            "primary_font_family": settings.translation.primary_font_family,
        },
        "pdf": {
            "watermark_output_mode": settings.pdf.watermark_output_mode,
            "no_mono": settings.pdf.no_mono,
            "no_dual": settings.pdf.no_dual,
            "dual_translate_first": settings.pdf.dual_translate_first,
            "use_alternating_pages_dual": settings.pdf.use_alternating_pages_dual,
            "translate_table_text": settings.pdf.translate_table_text,
            "skip_scanned_detection": settings.pdf.skip_scanned_detection,
            "max_pages_per_part": settings.pdf.max_pages_per_part,
            "skip_clean": settings.pdf.skip_clean,
            "disable_rich_text_translate": settings.pdf.disable_rich_text_translate,
            "enhance_compatibility": settings.pdf.enhance_compatibility,
            "split_short_lines": settings.pdf.split_short_lines,
            "short_line_split_factor": settings.pdf.short_line_split_factor,
            "ocr_workaround": settings.pdf.ocr_workaround,
            "auto_enable_ocr_workaround": settings.pdf.auto_enable_ocr_workaround,
            "only_include_translated_page": settings.pdf.only_include_translated_page,
            "formular_font_pattern": settings.pdf.formular_font_pattern,
            "formular_char_pattern": settings.pdf.formular_char_pattern,
            "no_merge_alternating_line_numbers": settings.pdf.no_merge_alternating_line_numbers,
            "no_remove_non_formula_lines": settings.pdf.no_remove_non_formula_lines,
            "non_formula_line_iou_threshold": settings.pdf.non_formula_line_iou_threshold,
            "figure_table_protection_threshold": settings.pdf.figure_table_protection_threshold,
            "skip_formula_offset_calculation": settings.pdf.skip_formula_offset_calculation,
        },
        "translate_engine": (
            settings.translate_engine_settings.translate_engine_type
            if settings.translate_engine_settings
            else None
        ),
        "translation_engines": _translation_engine_options(settings),
    }


def _set_allowed_fields(target: Any, values: dict[str, Any], allowed: set[str]) -> None:
    for field_name, value in values.items():
        if field_name not in allowed:
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported settings field: {field_name}",
            )
        setattr(target, field_name, value)


def _apply_runtime_settings_update(
    settings: SettingsModel,
    update: RuntimeSettingsUpdate,
) -> None:
    _set_allowed_fields(
        settings.gui_settings,
        update.gui_settings,
        {
            "brand_name",
            "brand_url",
            "max_concurrent_jobs",
            "max_queue_size",
            "auto_cleanup_output_history",
            "output_history_retention_days",
        },
    )
    _set_allowed_fields(
        settings.translation,
        update.translation,
        {
            "lang_in",
            "lang_out",
            "qps",
            "pool_max_workers",
            "term_qps",
            "term_pool_max_workers",
            "ignore_cache",
            "custom_system_prompt",
            "glossaries",
            "rpc_doclayout",
            "disable_builtin_fashion_glossary",
            "disable_builtin_fashion_prompt",
            "save_auto_extracted_glossary",
            "no_auto_extract_glossary",
            "min_text_length",
            "primary_font_family",
        },
    )
    _set_allowed_fields(
        settings.pdf,
        update.pdf,
        {
            "watermark_output_mode",
            "no_mono",
            "no_dual",
            "dual_translate_first",
            "use_alternating_pages_dual",
            "translate_table_text",
            "skip_scanned_detection",
            "max_pages_per_part",
            "skip_clean",
            "disable_rich_text_translate",
            "enhance_compatibility",
            "split_short_lines",
            "short_line_split_factor",
            "ocr_workaround",
            "auto_enable_ocr_workaround",
            "only_include_translated_page",
            "formular_font_pattern",
            "formular_char_pattern",
            "no_merge_alternating_line_numbers",
            "no_remove_non_formula_lines",
            "non_formula_line_iou_threshold",
            "figure_table_protection_threshold",
            "skip_formula_offset_calculation",
        },
    )
    _apply_translation_engine_update(
        settings,
        update.translate_engine,
        update.translate_engine_settings,
    )

    settings.gui_settings.max_concurrent_jobs = max(
        1,
        int(settings.gui_settings.max_concurrent_jobs),
    )
    if settings.gui_settings.max_queue_size is not None:
        settings.gui_settings.max_queue_size = max(
            1,
            int(settings.gui_settings.max_queue_size),
        )
    settings.translation.qps = max(1, int(settings.translation.qps))
    if settings.translation.pool_max_workers is not None:
        settings.translation.pool_max_workers = max(
            0,
            int(settings.translation.pool_max_workers),
        )
    if settings.translation.term_qps is not None:
        settings.translation.term_qps = max(0, int(settings.translation.term_qps))
    if settings.translation.term_pool_max_workers is not None:
        settings.translation.term_pool_max_workers = max(
            0,
            int(settings.translation.term_pool_max_workers),
        )
    settings.translation.min_text_length = max(
        0,
        int(settings.translation.min_text_length),
    )
    if settings.pdf.max_pages_per_part is not None:
        settings.pdf.max_pages_per_part = max(1, int(settings.pdf.max_pages_per_part))
    settings.pdf.short_line_split_factor = float(settings.pdf.short_line_split_factor)
    settings.pdf.non_formula_line_iou_threshold = float(
        settings.pdf.non_formula_line_iou_threshold,
    )
    settings.pdf.figure_table_protection_threshold = float(
        settings.pdf.figure_table_protection_threshold,
    )


def _request_server_shutdown(app: FastAPI) -> None:
    server = getattr(app.state, "uvicorn_server", None)
    if server is None:
        app.state.shutdown_requested = True
        return
    server.should_exit = True


def create_app(
    settings: SettingsModel,
    *,
    run_startup_cleanup: bool = False,
) -> FastAPI:
    current_user = _make_current_user_dependency(settings)
    app = FastAPI(title="PDFTranslate API", version="1")
    app.add_middleware(
        CORSMiddleware,
        allow_origin_regex=(
            r"^(http://localhost:\d+|http://127\.0\.0\.1:\d+|"
            r"http://tauri\.localhost|https://tauri\.localhost|tauri://localhost)$"
        ),
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["Content-Disposition"],
    )
    app.state.settings = settings
    app.state.jobs = {}
    app.state.translation_semaphore = asyncio.Semaphore(
        max(1, int(settings.gui_settings.max_concurrent_jobs))
    )
    app.state.auth_required = _auth_required(settings)
    app.state.startup_cleanup = (
        _run_startup_output_history_cleanup(settings) if run_startup_cleanup else None
    )
    app.state.shutdown_token = os.environ.get(DESKTOP_SHUTDOWN_TOKEN_ENV)
    app.state.shutdown_requested = False
    app.state.uvicorn_server = None

    @app.get("/", response_class=HTMLResponse)
    async def index():
        return _frontend_index()

    @app.get("/assets/{asset_path:path}")
    async def frontend_asset(asset_path: str):
        return _frontend_file(Path("assets") / asset_path)

    @app.get("/favicon.svg")
    async def favicon():
        return _frontend_file("favicon.svg")

    @app.post("/api/login")
    async def login(login_request: LoginRequest):
        if not current_user.auth_required:
            user = ApiUser(username=None, role="admin", authenticated=False)
            return {"user": user.model_dump()}

        user = current_user.authenticate(
            login_request.username,
            login_request.password,
        )
        if user is None:
            raise _unauthorized()

        session_token = secrets.token_urlsafe(32)
        current_user.sessions[session_token] = user
        response = JSONResponse({"user": user.model_dump()})
        response.set_cookie(
            key=SESSION_COOKIE_NAME,
            value=session_token,
            httponly=True,
            samesite="lax",
            secure=False,
        )
        return response

    @app.post("/api/logout")
    async def logout(request: Request, response: Response):
        session_token = request.cookies.get(SESSION_COOKIE_NAME)
        if session_token:
            current_user.sessions.pop(session_token, None)
        response.delete_cookie(SESSION_COOKIE_NAME)
        return {"ok": True}

    @app.post("/api/desktop/shutdown")
    async def desktop_shutdown(request: Request):
        shutdown_token = getattr(app.state, "shutdown_token", None)
        if not shutdown_token:
            raise HTTPException(status_code=404, detail="Not found")

        provided_token = request.headers.get(DESKTOP_SHUTDOWN_TOKEN_HEADER, "")
        if not secrets.compare_digest(provided_token, shutdown_token):
            raise HTTPException(status_code=403, detail="Invalid shutdown token")

        _request_server_shutdown(app)
        return {"ok": True}

    @app.get("/api/session")
    async def session(user: ApiUser = Depends(current_user)):
        return {
            "user": user.model_dump(),
            "brand_name": settings.gui_settings.brand_name,
            "brand_url": settings.gui_settings.brand_url,
            "settings_visible": user.is_admin,
            "auth_required": app.state.auth_required,
            "startup_cleanup": app.state.startup_cleanup,
            "translate_engine": (
                settings.translate_engine_settings.translate_engine_type
                if settings.translate_engine_settings
                else None
            ),
        }

    @app.get("/api/glossaries/builtin")
    async def builtin_glossaries(_user: ApiUser = Depends(current_user)):
        packs = []
        total_rows = 0
        for glossary_path in get_builtin_fashion_glossary_paths():
            rows = load_glossary_rows(glossary_path)
            total_rows += len(rows)
            packs.append({"name": glossary_path.name, "rows": len(rows)})
        return {"total_rows": total_rows, "packs": packs}

    @app.get("/api/glossaries/customer-template")
    async def customer_glossary_template(user: ApiUser = Depends(current_user)):
        _require_admin(user)
        path = ensure_default_customer_glossary_template()
        return {"path": str(path), "rows": load_glossary_rows(path)}

    @app.put("/api/glossaries/customer-template")
    async def update_customer_glossary_template(
        update: CustomerGlossaryUpdate,
        user: ApiUser = Depends(current_user),
    ):
        _require_admin(user)
        path = save_customer_glossary_template_rows(update.rows)
        return {"path": str(path), "rows": load_glossary_rows(path)}

    @app.post("/api/glossaries/customer-template/reset")
    async def reset_customer_glossary_template(user: ApiUser = Depends(current_user)):
        _require_admin(user)
        path, rows = restore_customer_glossary_template_rows()
        return {"path": str(path), "rows": rows}

    @app.get("/api/settings")
    async def get_settings(user: ApiUser = Depends(current_user)):
        _require_admin(user)
        return _settings_snapshot(settings)

    @app.patch("/api/settings")
    async def update_settings(
        update: RuntimeSettingsUpdate,
        user: ApiUser = Depends(current_user),
    ):
        _require_admin(user)
        _apply_runtime_settings_update(settings, update)
        _persist_runtime_config(settings)
        app.state.translation_semaphore = asyncio.Semaphore(
            max(1, int(settings.gui_settings.max_concurrent_jobs))
        )
        return _settings_snapshot(settings)

    @app.get("/api/users")
    async def list_users(user: ApiUser = Depends(current_user)):
        _require_admin(user)
        return {
            "auth_required": app.state.auth_required,
            "users": _list_managed_users(current_user.auth_users),
        }

    @app.post("/api/users")
    async def save_user(
        update: ManagedUserUpdate,
        user: ApiUser = Depends(current_user),
    ):
        _require_admin(user)
        username, role = _require_valid_managed_user(update)
        existing = current_user.auth_users.get(username)
        if existing is None and not _clean_auth_value(update.password):
            raise HTTPException(
                status_code=400,
                detail="Password is required for a new user",
            )
        password = _clean_auth_value(update.password) or (
            existing[0] if existing else ""
        )
        if existing and existing[1] == "admin" and role != "admin":
            _ensure_another_admin(current_user.auth_users, username)

        current_user.auth_users[username] = (password, role)
        _sync_primary_gui_credentials(settings, username, password, role)
        _refresh_user_sessions(current_user.sessions, username, role)
        _persist_managed_users(settings, current_user.auth_users)
        return {
            "auth_required": app.state.auth_required,
            "users": _list_managed_users(current_user.auth_users),
        }

    @app.delete("/api/users/{username}")
    async def delete_user(username: str, user: ApiUser = Depends(current_user)):
        _require_admin(user)
        username = _clean_auth_value(username)
        existing = current_user.auth_users.get(username)
        if existing is None:
            raise HTTPException(status_code=404, detail="User not found")
        if existing[1] == "admin":
            _ensure_another_admin(current_user.auth_users, username)
        current_user.auth_users.pop(username, None)
        _refresh_user_sessions(current_user.sessions, username, None)
        _persist_managed_users(settings, current_user.auth_users)
        return {
            "auth_required": app.state.auth_required,
            "users": _list_managed_users(current_user.auth_users),
        }

    @app.post("/api/users/change-password")
    async def change_password(
        request: PasswordChangeRequest,
        user: ApiUser = Depends(current_user),
    ):
        if not user.username:
            raise HTTPException(
                status_code=400,
                detail="Password changes require a logged-in user",
            )
        existing = current_user.auth_users.get(user.username)
        if existing is None:
            raise HTTPException(status_code=404, detail="User not found")
        if not secrets.compare_digest(
            request.current_password or "",
            existing[0],
        ):
            raise HTTPException(status_code=400, detail="Current password is invalid")
        new_password = _clean_auth_value(request.new_password)
        if not new_password:
            raise HTTPException(status_code=400, detail="New password is required")

        current_user.auth_users[user.username] = (new_password, user.role)
        _sync_primary_gui_credentials(settings, user.username, new_password, user.role)
        _refresh_user_sessions(current_user.sessions, user.username, user.role)
        _persist_managed_users(settings, current_user.auth_users)
        return {"user": ApiUser(username=user.username, role=user.role, authenticated=True).model_dump()}

    @app.post("/api/output-history/cleanup")
    async def cleanup_output_history(
        cleanup_request: OutputCleanupRequest,
        user: ApiUser = Depends(current_user),
    ):
        _require_admin(user)
        result = cleanup_session_output_dirs(
            base_dir=get_gui_output_root_dir(),
            older_than_days=(
                None
                if cleanup_request.remove_all
                else settings.gui_settings.output_history_retention_days
            ),
            remove_all=cleanup_request.remove_all,
        )
        return {
            "base_dir": str(result.base_dir),
            "deleted": len(result.deleted_dirs),
            "kept": len(result.kept_dirs),
            "skipped": len(result.skipped_non_session_entries),
            "errors": result.errors,
        }

    @app.post("/api/translate")
    async def translate(
        request: Request,
        user: ApiUser = Depends(current_user),
        file: UploadFile = File(...),
        lang_in: str | None = Form(None),
        lang_out: str | None = Form(None),
        pages: str | None = Form(None),
        no_mono: bool = Form(False),
        no_dual: bool = Form(False),
        save_auto_extracted_glossary: bool = Form(False),
    ):
        max_queue_size = settings.gui_settings.max_queue_size
        if (
            max_queue_size is not None
            and _count_queued_jobs(app.state.jobs) >= max_queue_size
        ):
            raise HTTPException(status_code=429, detail="Translation queue is full")
        if no_mono and no_dual:
            raise HTTPException(
                status_code=400,
                detail="Mono and dual output cannot both be disabled",
            )

        session_id = str(uuid.uuid4())
        output_dir = get_gui_output_root_dir() / session_id
        upload_dir = output_dir / "uploads"
        filename = _safe_filename(file.filename)
        input_path = upload_dir / filename
        await _save_upload(file, input_path)

        job_settings = _build_job_settings(
            settings,
            input_path=input_path,
            output_dir=output_dir,
            lang_in=lang_in,
            lang_out=lang_out,
            pages=pages,
            no_mono=no_mono,
            no_dual=no_dual,
            save_auto_extracted_glossary=save_auto_extracted_glossary,
        )
        now = time.time()
        job = TranslationJob(
            id=session_id,
            filename=filename,
            input_path=input_path,
            output_dir=output_dir,
            settings=job_settings,
            created_at=now,
            updated_at=now,
        )
        app.state.jobs[job.id] = job
        asyncio.create_task(_run_translation_job(app, job))
        return job.snapshot() | {"events_url": str(request.url_for("job_events", job_id=job.id))}

    @app.get("/api/jobs")
    async def list_jobs(_user: ApiUser = Depends(current_user)):
        jobs: dict[str, TranslationJob] = app.state.jobs
        return {"jobs": [job.snapshot() for job in jobs.values()]}

    @app.get("/api/jobs/{job_id}")
    async def get_job(job_id: str, _user: ApiUser = Depends(current_user)):
        job = app.state.jobs.get(job_id)
        if not job:
            raise HTTPException(status_code=404, detail="Job not found")
        return job.snapshot()

    @app.get("/api/jobs/{job_id}/events", name="job_events")
    async def job_events(job_id: str, _user: ApiUser = Depends(current_user)):
        job = app.state.jobs.get(job_id)
        if not job:
            raise HTTPException(status_code=404, detail="Job not found")

        async def stream():
            event_index = 0
            while True:
                while job.events and event_index < len(job.events):
                    payload = json.dumps(
                        job.events[event_index],
                        ensure_ascii=False,
                    )
                    yield f"event: update\ndata: {payload}\n\n"
                    event_index += 1

                yield (
                    "event: status\n"
                    f"data: {json.dumps(job.snapshot(), ensure_ascii=False)}\n\n"
                )
                if job.status in {"finished", "error"}:
                    break
                await asyncio.sleep(0.5)

        return StreamingResponse(stream(), media_type="text/event-stream")

    @app.get("/api/jobs/{job_id}/files/{kind}")
    async def download_file(
        job_id: str,
        kind: str,
        _user: ApiUser = Depends(current_user),
    ):
        job = app.state.jobs.get(job_id)
        if not job:
            raise HTTPException(status_code=404, detail="Job not found")
        file_path = Path((job.files or {}).get(kind, ""))
        if not file_path.exists():
            raise HTTPException(status_code=404, detail="File not found")
        media_type = "application/pdf" if file_path.suffix.lower() == ".pdf" else None
        return FileResponse(
            file_path,
            media_type=media_type,
            filename=file_path.name,
            content_disposition_type="attachment",
        )

    @app.get("/{frontend_path:path}", response_class=HTMLResponse)
    async def frontend_fallback(
        frontend_path: str,
    ):
        if frontend_path.startswith("api/"):
            raise HTTPException(status_code=404, detail="API route not found")
        candidate = (WEB_FRONTEND_DIR / frontend_path).resolve()
        if (
            candidate.is_relative_to(WEB_FRONTEND_DIR.resolve())
            and candidate.is_file()
        ):
            return FileResponse(candidate)
        return _frontend_index()

    return app


def _can_bind_port(host: str, port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        try:
            sock.bind((host, port))
        except OSError:
            return False
    return True


def _resolve_launch_port(preferred_port: int, max_attempts: int = 20) -> int:
    for candidate_port in range(preferred_port, preferred_port + max_attempts):
        if _can_bind_port("127.0.0.1", candidate_port) and _can_bind_port(
            "0.0.0.0", candidate_port
        ):
            return candidate_port
    return preferred_port


async def setup_fastapi_gui(
    settings: SettingsModel,
    server_port: int = 7860,
) -> None:
    app = create_app(settings, run_startup_cleanup=True)
    resolved_port = _resolve_launch_port(server_port)
    if resolved_port != server_port:
        print(
            f"Port {server_port} is already in use. "
            f"Falling back to http://127.0.0.1:{resolved_port}/"
        )

    print(f"PDFTranslate WebUI: http://127.0.0.1:{resolved_port}/")
    config = uvicorn.Config(
        app=app,
        host="0.0.0.0",
        port=resolved_port,
        log_level="info",
    )
    server = uvicorn.Server(config)
    app.state.uvicorn_server = server
    await server.serve()
