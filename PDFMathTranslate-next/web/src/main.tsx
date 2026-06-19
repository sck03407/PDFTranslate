import React, { FormEvent, useCallback, useEffect, useMemo, useState } from "react";
import { createRoot } from "react-dom/client";
import {
  AlertCircle,
  Brush,
  Download,
  FileText,
  KeyRound,
  ListChecks,
  LogOut,
  Loader2,
  Play,
  Plus,
  RefreshCw,
  RotateCcw,
  Save,
  Settings,
  Shield,
  Trash2,
  Upload,
  User
} from "lucide-react";
import "./styles.css";

type ApiUser = {
  username: string | null;
  role: "admin" | "user";
  authenticated: boolean;
};

type SessionPayload = {
  user: ApiUser;
  brand_name: string;
  brand_url: string;
  settings_visible: boolean;
  auth_required: boolean;
  startup_cleanup: CleanupSummary | null;
  translate_engine: string | null;
};

type CleanupSummary = {
  base_dir: string;
  deleted: number;
  kept: number;
  skipped: number;
  errors: string[];
};

type JobSnapshot = {
  id: string;
  filename: string;
  status: "queued" | "running" | "finished" | "error";
  progress: number;
  message: string;
  files: Record<string, string>;
  token_usage: Record<string, unknown>;
  error: string | null;
};

type JobsResponse = {
  jobs: JobSnapshot[];
};

type BuiltinGlossaryResponse = {
  total_rows: number;
  packs: Array<{ name: string; rows: number }>;
};

type SettingsSnapshot = {
  gui_settings: {
    brand_name: string;
    brand_url: string;
    require_gui_login: boolean;
    user_username: string;
    admin_username: string;
    max_concurrent_jobs: number;
    max_queue_size: number | null;
    auto_cleanup_output_history: boolean;
    output_history_retention_days: number;
  };
  translation: {
    lang_in: string;
    lang_out: string;
    qps: number;
    pool_max_workers: number | null;
    term_qps: number | null;
    term_pool_max_workers: number | null;
    ignore_cache: boolean;
    custom_system_prompt: string | null;
    glossaries: string | null;
    rpc_doclayout: string | null;
    disable_builtin_fashion_glossary: boolean;
    disable_builtin_fashion_prompt: boolean;
    save_auto_extracted_glossary: boolean;
    no_auto_extract_glossary: boolean;
    min_text_length: number;
    primary_font_family: string | null;
  };
  pdf: {
    watermark_output_mode: string;
    no_mono: boolean;
    no_dual: boolean;
    dual_translate_first: boolean;
    use_alternating_pages_dual: boolean;
    translate_table_text: boolean;
    skip_scanned_detection: boolean;
    max_pages_per_part: number | null;
    skip_clean: boolean;
    disable_rich_text_translate: boolean;
    enhance_compatibility: boolean;
    split_short_lines: boolean;
    short_line_split_factor: number;
    ocr_workaround: boolean;
    auto_enable_ocr_workaround: boolean;
    only_include_translated_page: boolean;
    formular_font_pattern: string | null;
    formular_char_pattern: string | null;
    no_merge_alternating_line_numbers: boolean;
    no_remove_non_formula_lines: boolean;
    non_formula_line_iou_threshold: number;
    figure_table_protection_threshold: number;
    skip_formula_offset_calculation: boolean;
  };
  translate_engine: string | null;
  translation_engines: TranslationEngineOption[];
};

type CustomerGlossaryResponse = {
  path: string;
  rows: string[][];
};

type EngineChoice = {
  label: string;
  value: string | number | boolean | null;
};

type EngineField = {
  name: string;
  label: string;
  input_type: "text" | "password" | "checkbox" | "number";
  value: string | number | boolean | null;
  secret: boolean;
  has_value: boolean;
  choices: EngineChoice[] | null;
};

type TranslationEngineOption = {
  name: string;
  support_llm: boolean;
  fields: EngineField[];
};

type ManagedUser = {
  username: string;
  role: "admin" | "user";
};

type ManagedUsersResponse = {
  auth_required: boolean;
  users: ManagedUser[];
};

type ActiveTab = "translate" | "jobs" | "settings";

type ApiContext = {
  apiBase: string;
  authHeader: string | null;
};

const terminalJobStates = new Set(["finished", "error"]);

function isTauriRuntime() {
  return Boolean(
    (window as unknown as { __TAURI_INTERNALS__?: unknown }).__TAURI_INTERNALS__
  );
}

function defaultApiBase() {
  const envBase = import.meta.env.VITE_API_BASE_URL as string | undefined;
  if (envBase) {
    return envBase.replace(/\/$/, "");
  }
  const saved = window.localStorage.getItem("pdftranslate.apiBase");
  if (saved) {
    return saved.replace(/\/$/, "");
  }
  if (isTauriRuntime() || window.location.hostname === "tauri.localhost") {
    return "http://127.0.0.1:7860";
  }
  return "";
}

function joinApiPath(apiBase: string, path: string) {
  return `${apiBase}${path}`;
}

async function startDesktopBackend() {
  if (!isTauriRuntime()) {
    return null;
  }
  try {
    const { invoke } = await import("@tauri-apps/api/core");
    return await invoke<string>("start_backend");
  } catch (error) {
    console.warn("Unable to start bundled backend", error);
    return null;
  }
}

async function apiRequest<T>(
  context: ApiContext,
  path: string,
  init: RequestInit = {}
): Promise<T> {
  const headers = new Headers(init.headers);
  if (!(init.body instanceof FormData) && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }
  if (context.authHeader) {
    headers.set("Authorization", context.authHeader);
  }

  const response = await fetch(joinApiPath(context.apiBase, path), {
    ...init,
    headers,
    credentials: "include"
  });

  if (!response.ok) {
    let message = response.statusText || "Request failed";
    try {
      const payload = await response.json();
      message = payload.detail || message;
    } catch (_error) {
      const text = await response.text();
      if (text) {
        message = text;
      }
    }
    const error = new Error(message) as Error & { status?: number };
    error.status = response.status;
    throw error;
  }

  return (await response.json()) as T;
}

function makeBasicAuth(username: string, password: string) {
  return `Basic ${window.btoa(`${username}:${password}`)}`;
}

function glossaryRowsToText(rows: string[][]) {
  return rows.map((row) => row.join("\t")).join("\n");
}

function glossaryTextToRows(text: string) {
  return text
    .split(/\r?\n/)
    .map((line) => line.trim())
    .filter(Boolean)
    .map((line) => {
      const cells = line.includes("\t") ? line.split("\t") : line.split(",");
      return [
        (cells[0] || "").trim(),
        (cells[1] || "").trim(),
        (cells[2] || "zh").trim()
      ];
    });
}

function choiceInputValue(value: EngineChoice["value"]) {
  return value === null || value === undefined ? "" : String(value);
}

function EngineFieldControl({
  field,
  onChange
}: {
  field: EngineField;
  onChange: (value: EngineField["value"]) => void;
}) {
  if (field.input_type === "checkbox") {
    return (
      <label className="inline-check">
        <input
          type="checkbox"
          checked={Boolean(field.value)}
          onChange={(event) => onChange(event.target.checked)}
        />
        {field.label}
      </label>
    );
  }

  if (field.choices?.length) {
    return (
      <label>
        {field.label}
        <select
          value={choiceInputValue(field.value)}
          onChange={(event) => {
            const selected = field.choices?.find(
              (choice) => choiceInputValue(choice.value) === event.target.value
            );
            onChange(selected ? selected.value : event.target.value);
          }}
        >
          {field.choices.map((choice) => (
            <option key={`${field.name}-${choiceInputValue(choice.value)}`} value={choiceInputValue(choice.value)}>
              {choice.label}
            </option>
          ))}
        </select>
      </label>
    );
  }

  return (
    <label>
      {field.secret && field.has_value
        ? `${field.label}（已设置，留空不变）`
        : field.label}
      <input
        type={field.input_type === "password" ? "password" : field.input_type}
        value={field.value === null || field.value === undefined ? "" : String(field.value)}
        onChange={(event) => {
          if (field.input_type === "number") {
            onChange(event.target.value ? Number(event.target.value) : null);
            return;
          }
          onChange(event.target.value);
        }}
      />
    </label>
  );
}

function App() {
  const [apiBase, setApiBase] = useState(defaultApiBase);
  const [authHeader, setAuthHeader] = useState<string | null>(null);
  const [session, setSession] = useState<SessionPayload | null>(null);
  const [sessionError, setSessionError] = useState<string | null>(null);
  const [needsLogin, setNeedsLogin] = useState(false);
  const [activeTab, setActiveTab] = useState<ActiveTab>("translate");
  const [jobs, setJobs] = useState<JobSnapshot[]>([]);
  const [currentJob, setCurrentJob] = useState<JobSnapshot | null>(null);
  const [glossaryTotal, setGlossaryTotal] = useState<number | null>(null);
  const [submitStatus, setSubmitStatus] = useState("");
  const [settingsStatus, setSettingsStatus] = useState("");
  const [cleanupStatus, setCleanupStatus] = useState("");
  const [backendStatus, setBackendStatus] = useState(
    isTauriRuntime() ? "Starting local backend" : ""
  );
  const [settingsSnapshot, setSettingsSnapshot] = useState<SettingsSnapshot | null>(
    null
  );
  const [managedUsers, setManagedUsers] = useState<ManagedUser[]>([]);
  const [userStatus, setUserStatus] = useState("");
  const [customerGlossary, setCustomerGlossary] = useState("");
  const [customerGlossaryPath, setCustomerGlossaryPath] = useState("");
  const [passwordForm, setPasswordForm] = useState({
    currentPassword: "",
    newPassword: "",
    confirmPassword: ""
  });
  const [managedUserForm, setManagedUserForm] = useState({
    username: "",
    password: "",
    role: "user" as "admin" | "user"
  });
  const [loginForm, setLoginForm] = useState({
    apiBase: defaultApiBase() || "http://127.0.0.1:7860",
    username: "",
    password: ""
  });
  const [translateForm, setTranslateForm] = useState({
    langIn: "en",
    langOut: "zh",
    pages: "",
    monoOnly: false,
    dualOnly: false,
    saveGlossary: false
  });
  const [selectedFile, setSelectedFile] = useState<File | null>(null);

  const apiContext = useMemo<ApiContext>(
    () => ({ apiBase, authHeader }),
    [apiBase, authHeader]
  );

  const loadSession = useCallback(async () => {
    try {
      const payload = await apiRequest<SessionPayload>(apiContext, "/api/session");
      setSession(payload);
      setNeedsLogin(false);
      setSessionError(null);
      setTranslateForm((current) => ({
        ...current,
        langIn: current.langIn || "en",
        langOut: current.langOut || "zh"
      }));
      document.title = payload.brand_name || "PDFTranslate";
    } catch (error) {
      const status = (error as Error & { status?: number }).status;
      setSession(null);
      setNeedsLogin(status === 401);
      setSessionError((error as Error).message);
    }
  }, [apiContext]);

  const loadJobs = useCallback(async () => {
    if (!session) {
      return;
    }
    const payload = await apiRequest<JobsResponse>(apiContext, "/api/jobs");
    setJobs(payload.jobs);
  }, [apiContext, session]);

  const loadGlossaries = useCallback(async () => {
    if (!session) {
      return;
    }
    const payload = await apiRequest<BuiltinGlossaryResponse>(
      apiContext,
      "/api/glossaries/builtin"
    );
    setGlossaryTotal(payload.total_rows);
  }, [apiContext, session]);

  const loadSettings = useCallback(async () => {
    if (!session?.settings_visible) {
      return;
    }
    const [settingsPayload, glossaryPayload, usersPayload] = await Promise.all([
      apiRequest<SettingsSnapshot>(apiContext, "/api/settings"),
      apiRequest<CustomerGlossaryResponse>(
        apiContext,
        "/api/glossaries/customer-template"
      ),
      apiRequest<ManagedUsersResponse>(apiContext, "/api/users")
    ]);
    setSettingsSnapshot(settingsPayload);
    setCustomerGlossary(glossaryRowsToText(glossaryPayload.rows));
    setCustomerGlossaryPath(glossaryPayload.path);
    setManagedUsers(usersPayload.users);
    setSettingsStatus("");
    setUserStatus("");
  }, [apiContext, session]);

  useEffect(() => {
    let cancelled = false;
    async function bootDesktopBackend() {
      const backendUrl = await startDesktopBackend();
      if (cancelled) {
        return;
      }
      if (backendUrl) {
        const normalizedUrl = backendUrl.replace(/\/$/, "");
        window.localStorage.setItem("pdftranslate.apiBase", normalizedUrl);
        setApiBase(normalizedUrl);
        setLoginForm((current) => ({ ...current, apiBase: normalizedUrl }));
      }
      setBackendStatus("");
    }
    void bootDesktopBackend();
    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    void loadSession();
  }, [loadSession]);

  useEffect(() => {
    if (!session) {
      return;
    }
    void Promise.all([loadGlossaries(), loadJobs()]);
    if (session.settings_visible) {
      void loadSettings();
    }
  }, [loadGlossaries, loadJobs, loadSettings, session]);

  useEffect(() => {
    if (!currentJob || terminalJobStates.has(currentJob.status)) {
      return;
    }
    const timer = window.setInterval(async () => {
      try {
        const nextJob = await apiRequest<JobSnapshot>(
          apiContext,
          `/api/jobs/${currentJob.id}`
        );
        setCurrentJob(nextJob);
        setJobs((currentJobs) => {
          const exists = currentJobs.some((job) => job.id === nextJob.id);
          if (!exists) {
            return [nextJob, ...currentJobs];
          }
          return currentJobs.map((job) => (job.id === nextJob.id ? nextJob : job));
        });
      } catch (error) {
        setSubmitStatus((error as Error).message);
      }
    }, 1000);
    return () => window.clearInterval(timer);
  }, [apiContext, currentJob]);

  async function handleLogin(event: FormEvent) {
    event.preventDefault();
    const normalizedApiBase = loginForm.apiBase.replace(/\/$/, "");
    window.localStorage.setItem("pdftranslate.apiBase", normalizedApiBase);
    setApiBase(normalizedApiBase);
    const basicAuth = makeBasicAuth(loginForm.username, loginForm.password);
    try {
      await apiRequest<{ user: ApiUser }>(
        { apiBase: normalizedApiBase, authHeader: null },
        "/api/login",
        {
          method: "POST",
          body: JSON.stringify({
            username: loginForm.username,
            password: loginForm.password
          })
        }
      );
      const payload = await apiRequest<SessionPayload>(
        { apiBase: normalizedApiBase, authHeader: basicAuth },
        "/api/session"
      );
      setAuthHeader(basicAuth);
      setSession(payload);
      setLoginForm({ apiBase: normalizedApiBase, username: "", password: "" });
      setNeedsLogin(false);
      setSessionError(null);
    } catch (error) {
      setSessionError((error as Error).message);
    }
  }

  async function handleLogout() {
    try {
      await apiRequest<{ ok: boolean }>(apiContext, "/api/logout", {
        method: "POST",
        body: JSON.stringify({})
      });
    } catch (_error) {
      // Local state cleanup below is enough when the session is already gone.
    }
    setAuthHeader(null);
    setSession(null);
    setNeedsLogin(true);
    setActiveTab("translate");
    setJobs([]);
    setCurrentJob(null);
    setSettingsSnapshot(null);
  }

  async function submitTranslation(event: FormEvent) {
    event.preventDefault();
    if (!selectedFile) {
      setSubmitStatus("请选择 PDF 文件");
      return;
    }
    setSubmitStatus("提交中");
    const body = new FormData();
    body.append("file", selectedFile);
    body.append("lang_in", translateForm.langIn);
    body.append("lang_out", translateForm.langOut);
    body.append("pages", translateForm.pages);
    body.append("no_mono", String(translateForm.dualOnly));
    body.append("no_dual", String(translateForm.monoOnly));
    body.append(
      "save_auto_extracted_glossary",
      String(translateForm.saveGlossary)
    );

    try {
      const job = await apiRequest<JobSnapshot>(apiContext, "/api/translate", {
        method: "POST",
        body
      });
      setCurrentJob(job);
      setJobs((currentJobs) => [job, ...currentJobs]);
      setSubmitStatus("已进入队列");
      setActiveTab("translate");
    } catch (error) {
      setSubmitStatus((error as Error).message);
    }
  }

  function selectedEngine(snapshot: SettingsSnapshot) {
    return snapshot.translation_engines.find(
      (engine) => engine.name === snapshot.translate_engine
    );
  }

  function updateEngineField(engineName: string, fieldName: string, value: EngineField["value"]) {
    if (!settingsSnapshot) {
      return;
    }
    setSettingsSnapshot({
      ...settingsSnapshot,
      translation_engines: settingsSnapshot.translation_engines.map((engine) =>
        engine.name === engineName
          ? {
              ...engine,
              fields: engine.fields.map((field) =>
                field.name === fieldName ? { ...field, value } : field
              )
            }
          : engine
      )
    });
  }

  function selectedEngineSettings(snapshot: SettingsSnapshot) {
    const engine = selectedEngine(snapshot);
    if (!engine) {
      return {};
    }
    return Object.fromEntries(
      engine.fields.map((field) => [field.name, field.value])
    );
  }

  async function saveSettings(event: FormEvent) {
    event.preventDefault();
    if (!settingsSnapshot) {
      return;
    }
    setSettingsStatus("保存中");
    const payload = {
      gui_settings: {
        brand_name: settingsSnapshot.gui_settings.brand_name,
        brand_url: settingsSnapshot.gui_settings.brand_url,
        max_concurrent_jobs: settingsSnapshot.gui_settings.max_concurrent_jobs,
        max_queue_size: settingsSnapshot.gui_settings.max_queue_size,
        auto_cleanup_output_history:
          settingsSnapshot.gui_settings.auto_cleanup_output_history,
        output_history_retention_days:
          settingsSnapshot.gui_settings.output_history_retention_days
      },
      translation: {
        lang_in: settingsSnapshot.translation.lang_in,
        lang_out: settingsSnapshot.translation.lang_out,
        qps: settingsSnapshot.translation.qps,
        pool_max_workers: settingsSnapshot.translation.pool_max_workers,
        term_qps: settingsSnapshot.translation.term_qps,
        term_pool_max_workers:
          settingsSnapshot.translation.term_pool_max_workers,
        ignore_cache: settingsSnapshot.translation.ignore_cache,
        custom_system_prompt: settingsSnapshot.translation.custom_system_prompt,
        glossaries: settingsSnapshot.translation.glossaries,
        rpc_doclayout: settingsSnapshot.translation.rpc_doclayout,
        disable_builtin_fashion_glossary:
          settingsSnapshot.translation.disable_builtin_fashion_glossary,
        disable_builtin_fashion_prompt:
          settingsSnapshot.translation.disable_builtin_fashion_prompt,
        save_auto_extracted_glossary:
          settingsSnapshot.translation.save_auto_extracted_glossary,
        no_auto_extract_glossary:
          settingsSnapshot.translation.no_auto_extract_glossary,
        min_text_length: settingsSnapshot.translation.min_text_length,
        primary_font_family: settingsSnapshot.translation.primary_font_family
      },
      pdf: {
        watermark_output_mode: settingsSnapshot.pdf.watermark_output_mode,
        no_mono: settingsSnapshot.pdf.no_mono,
        no_dual: settingsSnapshot.pdf.no_dual,
        dual_translate_first: settingsSnapshot.pdf.dual_translate_first,
        use_alternating_pages_dual:
          settingsSnapshot.pdf.use_alternating_pages_dual,
        translate_table_text: settingsSnapshot.pdf.translate_table_text,
        skip_scanned_detection: settingsSnapshot.pdf.skip_scanned_detection,
        max_pages_per_part: settingsSnapshot.pdf.max_pages_per_part,
        skip_clean: settingsSnapshot.pdf.skip_clean,
        disable_rich_text_translate:
          settingsSnapshot.pdf.disable_rich_text_translate,
        enhance_compatibility: settingsSnapshot.pdf.enhance_compatibility,
        split_short_lines: settingsSnapshot.pdf.split_short_lines,
        short_line_split_factor: settingsSnapshot.pdf.short_line_split_factor,
        ocr_workaround: settingsSnapshot.pdf.ocr_workaround,
        auto_enable_ocr_workaround: settingsSnapshot.pdf.auto_enable_ocr_workaround,
        only_include_translated_page:
          settingsSnapshot.pdf.only_include_translated_page,
        formular_font_pattern: settingsSnapshot.pdf.formular_font_pattern,
        formular_char_pattern: settingsSnapshot.pdf.formular_char_pattern,
        no_merge_alternating_line_numbers:
          settingsSnapshot.pdf.no_merge_alternating_line_numbers,
        no_remove_non_formula_lines:
          settingsSnapshot.pdf.no_remove_non_formula_lines,
        non_formula_line_iou_threshold:
          settingsSnapshot.pdf.non_formula_line_iou_threshold,
        figure_table_protection_threshold:
          settingsSnapshot.pdf.figure_table_protection_threshold,
        skip_formula_offset_calculation:
          settingsSnapshot.pdf.skip_formula_offset_calculation
      },
      translate_engine: settingsSnapshot.translate_engine,
      translate_engine_settings: selectedEngineSettings(settingsSnapshot)
    };

    try {
      const updated = await apiRequest<SettingsSnapshot>(
        apiContext,
        "/api/settings",
        {
          method: "PATCH",
          body: JSON.stringify(payload)
        }
      );
      setSettingsSnapshot(updated);
      if (session) {
        setSession({
          ...session,
          brand_name: updated.gui_settings.brand_name,
          translate_engine: updated.translate_engine
        });
      }
      setSettingsStatus("已保存运行设置");
    } catch (error) {
      setSettingsStatus((error as Error).message);
    }
  }

  async function saveCustomerGlossary() {
    setSettingsStatus("保存术语模板中");
    try {
      const payload = await apiRequest<CustomerGlossaryResponse>(
        apiContext,
        "/api/glossaries/customer-template",
        {
          method: "PUT",
          body: JSON.stringify({ rows: glossaryTextToRows(customerGlossary) })
        }
      );
      setCustomerGlossary(glossaryRowsToText(payload.rows));
      setCustomerGlossaryPath(payload.path);
      setSettingsStatus("客户术语模板已保存");
    } catch (error) {
      setSettingsStatus((error as Error).message);
    }
  }

  async function resetCustomerGlossary() {
    setSettingsStatus("重置术语模板中");
    try {
      const payload = await apiRequest<CustomerGlossaryResponse>(
        apiContext,
        "/api/glossaries/customer-template/reset",
        { method: "POST", body: JSON.stringify({}) }
      );
      setCustomerGlossary(glossaryRowsToText(payload.rows));
      setCustomerGlossaryPath(payload.path);
      setSettingsStatus("客户术语模板已恢复默认");
    } catch (error) {
      setSettingsStatus((error as Error).message);
    }
  }

  async function cleanupOutputHistory(removeAll: boolean) {
    setCleanupStatus("清理中");
    try {
      const result = await apiRequest<CleanupSummary>(
        apiContext,
        "/api/output-history/cleanup",
        {
          method: "POST",
          body: JSON.stringify({ remove_all: removeAll })
        }
      );
      setCleanupStatus(`已删除 ${result.deleted} 个历史目录`);
    } catch (error) {
      setCleanupStatus((error as Error).message);
    }
  }

  async function changePassword(event: FormEvent) {
    event.preventDefault();
    if (!passwordForm.newPassword) {
      setUserStatus("请输入新密码");
      return;
    }
    if (passwordForm.newPassword !== passwordForm.confirmPassword) {
      setUserStatus("两次输入的新密码不一致");
      return;
    }
    try {
      await apiRequest<{ user: ApiUser }>(apiContext, "/api/users/change-password", {
        method: "POST",
        body: JSON.stringify({
          current_password: passwordForm.currentPassword,
          new_password: passwordForm.newPassword
        })
      });
      if (session?.user.username) {
        setAuthHeader(makeBasicAuth(session.user.username, passwordForm.newPassword));
      }
      setPasswordForm({
        currentPassword: "",
        newPassword: "",
        confirmPassword: ""
      });
      setUserStatus("管理员密码已修改");
    } catch (error) {
      setUserStatus((error as Error).message);
    }
  }

  async function saveManagedUser(event: FormEvent) {
    event.preventDefault();
    try {
      const payload = await apiRequest<ManagedUsersResponse>(apiContext, "/api/users", {
        method: "POST",
        body: JSON.stringify(managedUserForm)
      });
      setManagedUsers(payload.users);
      setManagedUserForm({ username: "", password: "", role: "user" });
      setUserStatus("用户已保存");
    } catch (error) {
      setUserStatus((error as Error).message);
    }
  }

  async function deleteManagedUser(username: string) {
    if (!window.confirm(`删除用户 ${username}？`)) {
      return;
    }
    try {
      const payload = await apiRequest<ManagedUsersResponse>(
        apiContext,
        `/api/users/${encodeURIComponent(username)}`,
        { method: "DELETE" }
      );
      setManagedUsers(payload.users);
      setUserStatus("用户已删除");
    } catch (error) {
      setUserStatus((error as Error).message);
    }
  }

  if (needsLogin || (!session && sessionError)) {
    return (
      <main className="login-screen">
        <form className="login-panel" onSubmit={handleLogin}>
          <div className="login-title">
            <Shield size={24} />
            <div>
              <h1>PDFTranslate</h1>
              <p>{backendStatus || sessionError || "需要登录"}</p>
            </div>
          </div>
          <label>
            API 地址
            <input
              value={loginForm.apiBase}
              onChange={(event) =>
                setLoginForm({ ...loginForm, apiBase: event.target.value })
              }
            />
          </label>
          <label>
            用户名
            <input
              autoComplete="username"
              value={loginForm.username}
              onChange={(event) =>
                setLoginForm({ ...loginForm, username: event.target.value })
              }
            />
          </label>
          <label>
            密码
            <input
              type="password"
              autoComplete="current-password"
              value={loginForm.password}
              onChange={(event) =>
                setLoginForm({ ...loginForm, password: event.target.value })
              }
            />
          </label>
          <button className="primary-btn" type="submit">
            <Shield size={16} />
            登录
          </button>
        </form>
      </main>
    );
  }

  if (!session) {
    return (
      <main className="loading-screen">
        <Loader2 className="spin" size={24} />
        <span>{backendStatus || "正在连接 PDFTranslate"}</span>
      </main>
    );
  }

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="brand">
          <div className="brand-mark">PT</div>
          <div>
            <h1>{session.brand_name || "PDFTranslate"}</h1>
            <p>{session.translate_engine || "Configured engine"}</p>
          </div>
        </div>
        <nav className="nav">
          <button
            className={activeTab === "translate" ? "active" : ""}
            onClick={() => setActiveTab("translate")}
            type="button"
          >
            <FileText size={16} />
            翻译
          </button>
          <button
            className={activeTab === "jobs" ? "active" : ""}
            onClick={() => {
              setActiveTab("jobs");
              void loadJobs();
            }}
            type="button"
          >
            <ListChecks size={16} />
            任务
          </button>
          {session.settings_visible ? (
            <button
              className={activeTab === "settings" ? "active" : ""}
              onClick={() => {
                setActiveTab("settings");
                void loadSettings();
              }}
              type="button"
            >
              <Settings size={16} />
              设置
            </button>
          ) : null}
        </nav>
        <div className="session-box">
          <span className="role-badge">
            <User size={14} />
            {session.user.role}
          </span>
          <span>{session.user.username || "local admin"}</span>
          <button className="session-action" onClick={() => void handleLogout()} type="button">
            <LogOut size={15} />
            退出登录
          </button>
        </div>
      </aside>

      <main className="workspace">
        {activeTab === "translate" ? (
          <section className="view-stack">
            <header className="toolbar">
              <div>
                <h2>PDF 翻译工作台</h2>
                <p>
                  {glossaryTotal === null
                    ? "正在读取内置服装术语库"
                    : `已加载 ${glossaryTotal} 条内置服装术语`}
                </p>
              </div>
              <button className="secondary-btn" onClick={() => void loadJobs()} type="button">
                <RefreshCw size={16} />
                刷新
              </button>
            </header>

            <form className="panel upload-panel" onSubmit={submitTranslation}>
              <label className="file-drop">
                <input
                  type="file"
                  accept="application/pdf,.pdf"
                  onChange={(event) =>
                    setSelectedFile(event.target.files?.[0] || null)
                  }
                />
                <Upload size={22} />
                <span>{selectedFile ? selectedFile.name : "选择 PDF 文件"}</span>
              </label>

              <div className="form-grid">
                <label>
                  源语言
                  <input
                    value={translateForm.langIn}
                    onChange={(event) =>
                      setTranslateForm({ ...translateForm, langIn: event.target.value })
                    }
                  />
                </label>
                <label>
                  目标语言
                  <input
                    value={translateForm.langOut}
                    onChange={(event) =>
                      setTranslateForm({ ...translateForm, langOut: event.target.value })
                    }
                  />
                </label>
                <label>
                  页码
                  <input
                    placeholder="1,3-5"
                    value={translateForm.pages}
                    onChange={(event) =>
                      setTranslateForm({ ...translateForm, pages: event.target.value })
                    }
                  />
                </label>
              </div>

              <div className="check-row">
                <label>
                  <input
                    type="checkbox"
                    checked={translateForm.monoOnly}
                    onChange={(event) =>
                      setTranslateForm({
                        ...translateForm,
                        monoOnly: event.target.checked,
                        dualOnly: event.target.checked ? false : translateForm.dualOnly
                      })
                    }
                  />
                  仅单语 PDF
                </label>
                <label>
                  <input
                    type="checkbox"
                    checked={translateForm.dualOnly}
                    onChange={(event) =>
                      setTranslateForm({
                        ...translateForm,
                        dualOnly: event.target.checked,
                        monoOnly: event.target.checked ? false : translateForm.monoOnly
                      })
                    }
                  />
                  仅双语 PDF
                </label>
                <label>
                  <input
                    type="checkbox"
                    checked={translateForm.saveGlossary}
                    onChange={(event) =>
                      setTranslateForm({
                        ...translateForm,
                        saveGlossary: event.target.checked
                      })
                    }
                  />
                  保存自动术语
                </label>
              </div>

              <div className="actions">
                <button className="primary-btn" type="submit">
                  <Play size={16} />
                  开始翻译
                </button>
                <span className="status-text">{submitStatus}</span>
              </div>
            </form>

            <JobPanel apiContext={apiContext} job={currentJob} />
          </section>
        ) : null}

        {activeTab === "jobs" ? (
          <section className="view-stack">
            <header className="toolbar">
              <h2>任务</h2>
              <button className="secondary-btn" onClick={() => void loadJobs()} type="button">
                <RefreshCw size={16} />
                刷新
              </button>
            </header>
            <div className="jobs-list">
              {jobs.length ? (
                jobs
                  .slice()
                  .reverse()
                  .map((job) => (
                    <button
                      className="job-row"
                      key={job.id}
                      onClick={() => {
                        setCurrentJob(job);
                        setActiveTab("translate");
                      }}
                      type="button"
                    >
                      <span>
                        <strong>{job.filename}</strong>
                        <small>{job.message || job.status}</small>
                      </span>
                      <span>{Math.round(job.progress || 0)}%</span>
                    </button>
                  ))
              ) : (
                <div className="empty-state">暂无任务</div>
              )}
            </div>
          </section>
        ) : null}

        {activeTab === "settings" && session.settings_visible ? (
          <section className="view-stack">
            <header className="toolbar">
              <div>
                <h2>管理员设置</h2>
                <p>当前账号可调整运行参数、客户术语模板和输出历史</p>
              </div>
              <button className="secondary-btn" onClick={() => void loadSettings()} type="button">
                <RefreshCw size={16} />
                重新读取
              </button>
            </header>
            {settingsSnapshot ? (
              <>
                <form className="panel settings-panel" onSubmit={saveSettings}>
                  <header className="sub-toolbar">
                    <h3>运行与翻译</h3>
                    <span className="status-text">{settingsStatus}</span>
                  </header>
                  <div className="form-grid settings-grid">
                    <label>
                      品牌名称
                      <input
                        value={settingsSnapshot.gui_settings.brand_name}
                        onChange={(event) =>
                          setSettingsSnapshot({
                            ...settingsSnapshot,
                            gui_settings: {
                              ...settingsSnapshot.gui_settings,
                              brand_name: event.target.value
                            }
                          })
                        }
                      />
                    </label>
                    <label>
                      源语言
                      <input
                        value={settingsSnapshot.translation.lang_in}
                        onChange={(event) =>
                          setSettingsSnapshot({
                            ...settingsSnapshot,
                            translation: {
                              ...settingsSnapshot.translation,
                              lang_in: event.target.value
                            }
                          })
                        }
                      />
                    </label>
                    <label>
                      目标语言
                      <input
                        value={settingsSnapshot.translation.lang_out}
                        onChange={(event) =>
                          setSettingsSnapshot({
                            ...settingsSnapshot,
                            translation: {
                              ...settingsSnapshot.translation,
                              lang_out: event.target.value
                            }
                          })
                        }
                      />
                    </label>
                    <label>
                      QPS
                      <input
                        min={1}
                        type="number"
                        value={settingsSnapshot.translation.qps}
                        onChange={(event) =>
                          setSettingsSnapshot({
                            ...settingsSnapshot,
                            translation: {
                              ...settingsSnapshot.translation,
                              qps: Number(event.target.value || 1)
                            }
                          })
                        }
                      />
                    </label>
                    <label>
                      Worker
                      <input
                        min={0}
                        type="number"
                        value={settingsSnapshot.translation.pool_max_workers ?? ""}
                        onChange={(event) =>
                          setSettingsSnapshot({
                            ...settingsSnapshot,
                            translation: {
                              ...settingsSnapshot.translation,
                              pool_max_workers: event.target.value
                                ? Number(event.target.value)
                                : null
                            }
                          })
                        }
                      />
                    </label>
                    <label>
                      术语 QPS
                      <input
                        min={0}
                        type="number"
                        value={settingsSnapshot.translation.term_qps ?? ""}
                        onChange={(event) =>
                          setSettingsSnapshot({
                            ...settingsSnapshot,
                            translation: {
                              ...settingsSnapshot.translation,
                              term_qps: event.target.value
                                ? Number(event.target.value)
                                : null
                            }
                          })
                        }
                      />
                    </label>
                    <label>
                      术语 Worker
                      <input
                        min={0}
                        type="number"
                        value={
                          settingsSnapshot.translation.term_pool_max_workers ?? ""
                        }
                        onChange={(event) =>
                          setSettingsSnapshot({
                            ...settingsSnapshot,
                            translation: {
                              ...settingsSnapshot.translation,
                              term_pool_max_workers: event.target.value
                                ? Number(event.target.value)
                                : null
                            }
                          })
                        }
                      />
                    </label>
                    <label>
                      并发任务
                      <input
                        min={1}
                        type="number"
                        value={settingsSnapshot.gui_settings.max_concurrent_jobs}
                        onChange={(event) =>
                          setSettingsSnapshot({
                            ...settingsSnapshot,
                            gui_settings: {
                              ...settingsSnapshot.gui_settings,
                              max_concurrent_jobs: Number(event.target.value || 1)
                            }
                          })
                        }
                      />
                    </label>
                    <label>
                      队列上限
                      <input
                        min={1}
                        type="number"
                        value={settingsSnapshot.gui_settings.max_queue_size ?? ""}
                        onChange={(event) =>
                          setSettingsSnapshot({
                            ...settingsSnapshot,
                            gui_settings: {
                              ...settingsSnapshot.gui_settings,
                              max_queue_size: event.target.value
                                ? Number(event.target.value)
                                : null
                            }
                          })
                        }
                      />
                    </label>
                    <label>
                      历史保留天数
                      <input
                        min={1}
                        type="number"
                        value={
                          settingsSnapshot.gui_settings.output_history_retention_days
                        }
                        onChange={(event) =>
                          setSettingsSnapshot({
                            ...settingsSnapshot,
                            gui_settings: {
                              ...settingsSnapshot.gui_settings,
                              output_history_retention_days: Number(
                                event.target.value || 1
                              )
                            }
                          })
                        }
                      />
                    </label>
                    <label>
                      最小文本长度
                      <input
                        min={0}
                        type="number"
                        value={settingsSnapshot.translation.min_text_length}
                        onChange={(event) =>
                          setSettingsSnapshot({
                            ...settingsSnapshot,
                            translation: {
                              ...settingsSnapshot.translation,
                              min_text_length: Number(event.target.value || 0)
                            }
                          })
                        }
                      />
                    </label>
                    <label>
                      分段页数
                      <input
                        min={1}
                        type="number"
                        value={settingsSnapshot.pdf.max_pages_per_part ?? ""}
                        onChange={(event) =>
                          setSettingsSnapshot({
                            ...settingsSnapshot,
                            pdf: {
                              ...settingsSnapshot.pdf,
                              max_pages_per_part: event.target.value
                                ? Number(event.target.value)
                                : null
                            }
                          })
                        }
                      />
                    </label>
                    <label className="wide-field">
                      额外术语表
                      <input
                        value={settingsSnapshot.translation.glossaries ?? ""}
                        onChange={(event) =>
                          setSettingsSnapshot({
                            ...settingsSnapshot,
                            translation: {
                              ...settingsSnapshot.translation,
                              glossaries: event.target.value || null
                            }
                          })
                        }
                      />
                    </label>
                    <label className="wide-field">
                      文档布局 RPC
                      <input
                        value={settingsSnapshot.translation.rpc_doclayout ?? ""}
                        onChange={(event) =>
                          setSettingsSnapshot({
                            ...settingsSnapshot,
                            translation: {
                              ...settingsSnapshot.translation,
                              rpc_doclayout: event.target.value || null
                            }
                          })
                        }
                      />
                    </label>
                    <label className="wide-field">
                      自定义系统提示词
                      <textarea
                        className="compact-textarea"
                        value={settingsSnapshot.translation.custom_system_prompt ?? ""}
                        onChange={(event) =>
                          setSettingsSnapshot({
                            ...settingsSnapshot,
                            translation: {
                              ...settingsSnapshot.translation,
                              custom_system_prompt: event.target.value || null
                            }
                          })
                        }
                      />
                    </label>
                  </div>

                  <div className="check-row">
                    <label>
                      <input
                        type="checkbox"
                        checked={
                          !settingsSnapshot.translation.disable_builtin_fashion_glossary
                        }
                        onChange={(event) =>
                          setSettingsSnapshot({
                            ...settingsSnapshot,
                            translation: {
                              ...settingsSnapshot.translation,
                              disable_builtin_fashion_glossary:
                                !event.target.checked
                            }
                          })
                        }
                      />
                      启用内置服装术语库
                    </label>
                    <label>
                      <input
                        type="checkbox"
                        checked={
                          !settingsSnapshot.translation.disable_builtin_fashion_prompt
                        }
                        onChange={(event) =>
                          setSettingsSnapshot({
                            ...settingsSnapshot,
                            translation: {
                              ...settingsSnapshot.translation,
                              disable_builtin_fashion_prompt: !event.target.checked
                            }
                          })
                        }
                      />
                      启用服装翻译提示词
                    </label>
                    <label>
                      <input
                        type="checkbox"
                        checked={!settingsSnapshot.translation.no_auto_extract_glossary}
                        onChange={(event) =>
                          setSettingsSnapshot({
                            ...settingsSnapshot,
                            translation: {
                              ...settingsSnapshot.translation,
                              no_auto_extract_glossary: !event.target.checked
                            }
                          })
                        }
                      />
                      自动抽取术语
                    </label>
                    <label>
                      <input
                        type="checkbox"
                        checked={settingsSnapshot.translation.ignore_cache}
                        onChange={(event) =>
                          setSettingsSnapshot({
                            ...settingsSnapshot,
                            translation: {
                              ...settingsSnapshot.translation,
                              ignore_cache: event.target.checked
                            }
                          })
                        }
                      />
                      忽略翻译缓存
                    </label>
                  </div>

                  <section className="settings-section">
                    <header className="sub-toolbar">
                      <h3>AI 模型服务商</h3>
                      <span className="status-text">
                        {selectedEngine(settingsSnapshot)?.support_llm
                          ? "LLM"
                          : "翻译接口"}
                      </span>
                    </header>
                    <div className="form-grid engine-grid">
                      <label>
                        服务商
                        <select
                          value={settingsSnapshot.translate_engine ?? ""}
                          onChange={(event) =>
                            setSettingsSnapshot({
                              ...settingsSnapshot,
                              translate_engine: event.target.value
                            })
                          }
                        >
                          {settingsSnapshot.translation_engines.map((engine) => (
                            <option key={engine.name} value={engine.name}>
                              {engine.name}
                            </option>
                          ))}
                        </select>
                      </label>
                      {selectedEngine(settingsSnapshot)?.fields.map((field) => (
                        <EngineFieldControl
                          field={field}
                          key={`${settingsSnapshot.translate_engine}-${field.name}`}
                          onChange={(value) =>
                            updateEngineField(
                              settingsSnapshot.translate_engine || "",
                              field.name,
                              value
                            )
                          }
                        />
                      ))}
                    </div>
                  </section>

                  <section className="settings-section">
                    <header className="sub-toolbar">
                      <h3>PDF 输出</h3>
                    </header>
                    <div className="form-grid settings-grid">
                      <label>
                        水印模式
                        <select
                          value={settingsSnapshot.pdf.watermark_output_mode}
                          onChange={(event) =>
                            setSettingsSnapshot({
                              ...settingsSnapshot,
                              pdf: {
                                ...settingsSnapshot.pdf,
                                watermark_output_mode: event.target.value
                              }
                            })
                          }
                        >
                          <option value="no_watermark">no_watermark</option>
                          <option value="watermarked">watermarked</option>
                          <option value="both">both</option>
                        </select>
                      </label>
                      <label>
                        短行拆分系数
                        <input
                          step="0.1"
                          type="number"
                          value={settingsSnapshot.pdf.short_line_split_factor}
                          onChange={(event) =>
                            setSettingsSnapshot({
                              ...settingsSnapshot,
                              pdf: {
                                ...settingsSnapshot.pdf,
                                short_line_split_factor: Number(
                                  event.target.value || 0
                                )
                              }
                            })
                          }
                        />
                      </label>
                      <label>
                        非公式线阈值
                        <input
                          step="0.01"
                          type="number"
                          value={settingsSnapshot.pdf.non_formula_line_iou_threshold}
                          onChange={(event) =>
                            setSettingsSnapshot({
                              ...settingsSnapshot,
                              pdf: {
                                ...settingsSnapshot.pdf,
                                non_formula_line_iou_threshold: Number(
                                  event.target.value || 0
                                )
                              }
                            })
                          }
                        />
                      </label>
                      <label>
                        图表保护阈值
                        <input
                          step="0.01"
                          type="number"
                          value={
                            settingsSnapshot.pdf.figure_table_protection_threshold
                          }
                          onChange={(event) =>
                            setSettingsSnapshot({
                              ...settingsSnapshot,
                              pdf: {
                                ...settingsSnapshot.pdf,
                                figure_table_protection_threshold: Number(
                                  event.target.value || 0
                                )
                              }
                            })
                          }
                        />
                      </label>
                      <label className="wide-field">
                        公式字体模式
                        <input
                          value={settingsSnapshot.pdf.formular_font_pattern ?? ""}
                          onChange={(event) =>
                            setSettingsSnapshot({
                              ...settingsSnapshot,
                              pdf: {
                                ...settingsSnapshot.pdf,
                                formular_font_pattern: event.target.value || null
                              }
                            })
                          }
                        />
                      </label>
                      <label className="wide-field">
                        公式字符模式
                        <input
                          value={settingsSnapshot.pdf.formular_char_pattern ?? ""}
                          onChange={(event) =>
                            setSettingsSnapshot({
                              ...settingsSnapshot,
                              pdf: {
                                ...settingsSnapshot.pdf,
                                formular_char_pattern: event.target.value || null
                              }
                            })
                          }
                        />
                      </label>
                    </div>
                    <div className="check-row">
                      {[
                        ["no_mono", "不输出单语 PDF"],
                        ["no_dual", "不输出双语 PDF"],
                        ["dual_translate_first", "双语译文在前"],
                        ["use_alternating_pages_dual", "交替页双语"],
                        ["translate_table_text", "翻译表格文本"],
                        ["skip_scanned_detection", "跳过扫描检测"],
                        ["skip_clean", "跳过 PDF 清理"],
                        ["disable_rich_text_translate", "禁用富文本翻译"],
                        ["enhance_compatibility", "增强兼容性"],
                        ["split_short_lines", "拆分短行"],
                        ["ocr_workaround", "OCR 黑字白底"],
                        ["auto_enable_ocr_workaround", "自动 OCR 处理"],
                        ["only_include_translated_page", "仅输出翻译页"],
                        ["no_merge_alternating_line_numbers", "保留交替行号"],
                        ["no_remove_non_formula_lines", "保留非公式线"],
                        ["skip_formula_offset_calculation", "跳过公式偏移"]
                      ].map(([fieldName, label]) => (
                        <label key={fieldName}>
                          <input
                            type="checkbox"
                            checked={Boolean(
                              settingsSnapshot.pdf[
                                fieldName as keyof SettingsSnapshot["pdf"]
                              ]
                            )}
                            onChange={(event) =>
                              setSettingsSnapshot({
                                ...settingsSnapshot,
                                pdf: {
                                  ...settingsSnapshot.pdf,
                                  [fieldName]: event.target.checked
                                }
                              })
                            }
                          />
                          {label}
                        </label>
                      ))}
                    </div>
                  </section>

                  <div className="actions">
                    <button className="primary-btn" type="submit">
                      <Save size={16} />
                      保存设置
                    </button>
                  </div>
                </form>

                <section className="panel settings-panel">
                  <header className="sub-toolbar">
                    <h3>账号与用户</h3>
                    <span className="status-text">{userStatus}</span>
                  </header>
                  <form className="form-grid account-grid" onSubmit={changePassword}>
                    <label>
                      当前密码
                      <input
                        type="password"
                        value={passwordForm.currentPassword}
                        onChange={(event) =>
                          setPasswordForm({
                            ...passwordForm,
                            currentPassword: event.target.value
                          })
                        }
                      />
                    </label>
                    <label>
                      新密码
                      <input
                        type="password"
                        value={passwordForm.newPassword}
                        onChange={(event) =>
                          setPasswordForm({
                            ...passwordForm,
                            newPassword: event.target.value
                          })
                        }
                      />
                    </label>
                    <label>
                      确认新密码
                      <input
                        type="password"
                        value={passwordForm.confirmPassword}
                        onChange={(event) =>
                          setPasswordForm({
                            ...passwordForm,
                            confirmPassword: event.target.value
                          })
                        }
                      />
                    </label>
                    <button className="secondary-btn" type="submit">
                      <KeyRound size={16} />
                      修改密码
                    </button>
                  </form>

                  <form className="form-grid account-grid" onSubmit={saveManagedUser}>
                    <label>
                      用户名
                      <input
                        value={managedUserForm.username}
                        onChange={(event) =>
                          setManagedUserForm({
                            ...managedUserForm,
                            username: event.target.value
                          })
                        }
                      />
                    </label>
                    <label>
                      密码
                      <input
                        type="password"
                        value={managedUserForm.password}
                        onChange={(event) =>
                          setManagedUserForm({
                            ...managedUserForm,
                            password: event.target.value
                          })
                        }
                      />
                    </label>
                    <label>
                      角色
                      <select
                        value={managedUserForm.role}
                        onChange={(event) =>
                          setManagedUserForm({
                            ...managedUserForm,
                            role: event.target.value as "admin" | "user"
                          })
                        }
                      >
                        <option value="user">user</option>
                        <option value="admin">admin</option>
                      </select>
                    </label>
                    <button className="primary-btn" type="submit">
                      <Plus size={16} />
                      保存用户
                    </button>
                  </form>

                  <div className="users-list">
                    {managedUsers.map((managedUser) => (
                      <div className="user-row" key={managedUser.username}>
                        <span>
                          <strong>{managedUser.username}</strong>
                          <small>{managedUser.role}</small>
                        </span>
                        <div className="button-row">
                          <button
                            className="secondary-btn"
                            onClick={() =>
                              setManagedUserForm({
                                username: managedUser.username,
                                password: "",
                                role: managedUser.role
                              })
                            }
                            type="button"
                          >
                            <User size={16} />
                            编辑
                          </button>
                          <button
                            className="danger-btn"
                            onClick={() => void deleteManagedUser(managedUser.username)}
                            type="button"
                          >
                            <Trash2 size={16} />
                            删除
                          </button>
                        </div>
                      </div>
                    ))}
                  </div>
                </section>
              </>
            ) : (
              <div className="empty-state">正在读取设置</div>
            )}

            <section className="panel glossary-panel">
              <header className="sub-toolbar">
                <div>
                  <h3>客户术语模板</h3>
                  <p>{customerGlossaryPath || "fashion-customer-glossary-template.csv"}</p>
                </div>
                <div className="button-row">
                  <button className="secondary-btn" onClick={resetCustomerGlossary} type="button">
                    <RotateCcw size={16} />
                    恢复默认
                  </button>
                  <button className="primary-btn" onClick={saveCustomerGlossary} type="button">
                    <Save size={16} />
                    保存术语
                  </button>
                </div>
              </header>
              <textarea
                value={customerGlossary}
                onChange={(event) => setCustomerGlossary(event.target.value)}
                spellCheck={false}
              />
            </section>

            <section className="panel cleanup-panel">
              <header className="sub-toolbar">
                <div>
                  <h3>输出历史</h3>
                  <p>{cleanupStatus || "按保留天数清理历史任务目录"}</p>
                </div>
                <div className="button-row">
                  <button
                    className="secondary-btn"
                    onClick={() => void cleanupOutputHistory(false)}
                    type="button"
                  >
                    <Brush size={16} />
                    清理过期
                  </button>
                  <button
                    className="danger-btn"
                    onClick={() => void cleanupOutputHistory(true)}
                    type="button"
                  >
                    <AlertCircle size={16} />
                    清空历史
                  </button>
                </div>
              </header>
            </section>
          </section>
        ) : null}
      </main>
    </div>
  );
}

async function downloadJobFile(
  apiContext: ApiContext,
  job: JobSnapshot,
  kind: string
) {
  const headers = new Headers();
  if (apiContext.authHeader) {
    headers.set("Authorization", apiContext.authHeader);
  }
  const response = await fetch(
    joinApiPath(apiContext.apiBase, `/api/jobs/${job.id}/files/${kind}`),
    {
      credentials: "include",
      headers
    }
  );
  if (!response.ok) {
    throw new Error(response.statusText || "Download failed");
  }

  const blob = await response.blob();
  const url = window.URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = `${kind}-${job.filename}`;
  document.body.appendChild(link);
  link.click();
  link.remove();
  window.URL.revokeObjectURL(url);
}

function JobPanel({
  apiContext,
  job
}: {
  apiContext: ApiContext;
  job: JobSnapshot | null;
}) {
  const [downloadError, setDownloadError] = useState("");

  if (!job) {
    return (
      <section className="panel job-panel">
        <header className="job-header">
          <h3>当前任务</h3>
          <span>Idle</span>
        </header>
        <div className="empty-state">等待提交 PDF</div>
      </section>
    );
  }

  return (
    <section className="panel job-panel">
      <header className="job-header">
        <div>
          <h3>{job.filename}</h3>
          <p>{job.message || job.status}</p>
        </div>
        <span>{job.status}</span>
      </header>
      <div className="progress-track">
        <div
          className="progress-bar"
          style={{ width: `${Math.max(0, Math.min(job.progress || 0, 100))}%` }}
        />
      </div>
      <div className="download-row">
        {Object.keys(job.files || {}).length ? (
          Object.keys(job.files).map((kind) => (
            <button
              className="download-btn"
              key={kind}
              onClick={async () => {
                try {
                  setDownloadError("");
                  await downloadJobFile(apiContext, job, kind);
                } catch (error) {
                  setDownloadError((error as Error).message);
                }
              }}
              type="button"
            >
              <Download size={16} />
              下载 {kind}
            </button>
          ))
        ) : (
          <span>结果生成后会显示下载入口</span>
        )}
      </div>
      {downloadError ? <div className="error-line">{downloadError}</div> : null}
      {job.error ? <div className="error-line">{job.error}</div> : null}
    </section>
  );
}

createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
);
