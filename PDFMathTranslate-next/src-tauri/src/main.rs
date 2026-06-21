#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

use std::fs;
use std::io::{Read, Write};
use std::net::{TcpListener, TcpStream};
use std::path::PathBuf;
use std::process::{Child, Command, Stdio};
use std::sync::Mutex;
use std::thread;
use std::time::{Duration, Instant, SystemTime, UNIX_EPOCH};
use tauri::{AppHandle, Manager, State};

#[cfg(windows)]
use std::os::windows::process::CommandExt;

#[cfg(windows)]
const CREATE_NO_WINDOW: u32 = 0x08000000;

const DEFAULT_BACKEND_PORT: u16 = 7860;

struct BackendState {
    child: Mutex<Option<Child>>,
    backend_url: Mutex<Option<String>>,
    shutdown_token: Mutex<Option<String>>,
}

impl Drop for BackendState {
    fn drop(&mut self) {
        stop_backend(self);
    }
}

fn exe_dir() -> Result<PathBuf, String> {
    let exe = std::env::current_exe()
        .map_err(|error| format!("Unable to resolve desktop executable path: {error}"))?;
    Ok(exe
        .parent()
        .map(PathBuf::from)
        .unwrap_or_else(|| PathBuf::from(".")))
}

fn desktop_runtime_dir(_app: &AppHandle) -> Result<PathBuf, String> {
    if let Ok(runtime_dir) = std::env::var("PDFTRANSLATE_RUNTIME_DIR") {
        return Ok(PathBuf::from(runtime_dir));
    }
    if let Ok(runtime_dir) = std::env::var("PDF2ZH_RUNTIME_DIR") {
        return Ok(PathBuf::from(runtime_dir));
    }
    exe_dir()
}

fn bundled_backend_dir(app: &AppHandle) -> Option<PathBuf> {
    let mut candidates = Vec::new();
    if let Ok(resource_dir) = app.path().resource_dir() {
        candidates.push(resource_dir.join("backend"));
        candidates.push(resource_dir.join("resources").join("backend"));
    }
    if let Ok(exe_dir) = exe_dir() {
        candidates.push(exe_dir.join("backend"));
        candidates.push(exe_dir.join("resources").join("backend"));
    }

    candidates.into_iter().find(|candidate| {
        candidate
            .join("runtime")
            .join(if cfg!(windows) {
                "python.exe"
            } else {
                "python"
            })
            .exists()
    })
}

fn copy_missing_tree(source: PathBuf, destination: PathBuf) -> Result<(), String> {
    if !source.exists() {
        return Ok(());
    }
    fs::create_dir_all(&destination).map_err(|error| {
        format!(
            "Unable to create bundled backend destination {:?}: {error}",
            destination
        )
    })?;

    for entry in fs::read_dir(&source)
        .map_err(|error| {
            format!(
                "Unable to read bundled backend dir {:?}: {error}",
                source
            )
        })?
    {
        let entry = entry.map_err(|error| format!("Unable to read backend entry: {error}"))?;
        let entry_type = entry
            .file_type()
            .map_err(|error| format!("Unable to inspect backend entry: {error}"))?;
        let target = destination.join(entry.file_name());
        if entry_type.is_dir() {
            copy_missing_tree(entry.path(), target)?;
        } else if entry_type.is_file() && !target.exists() {
            fs::copy(entry.path(), &target).map_err(|error| {
                format!("Unable to copy backend resource {:?}: {error}", target)
            })?;
        }
    }

    Ok(())
}

fn copy_missing_file(source: PathBuf, destination: PathBuf) -> Result<(), String> {
    if !source.exists() || destination.exists() {
        return Ok(());
    }
    if let Some(parent) = destination.parent() {
        fs::create_dir_all(parent).map_err(|error| {
            format!(
                "Unable to create bundled backend file destination {:?}: {error}",
                parent
            )
        })?;
    }
    fs::copy(&source, &destination)
        .map_err(|error| {
            format!(
                "Unable to copy bundled backend file {:?}: {error}",
                source
            )
        })?;
    Ok(())
}

fn bundled_glossary_dir(bundled_dir: &PathBuf) -> Option<PathBuf> {
    [
        bundled_dir.join("config").join("glossaries"),
        bundled_dir
            .join("runtime")
            .join("Lib")
            .join("site-packages")
            .join("pdf2zh_next")
            .join("assets")
            .join("glossaries"),
        bundled_dir
            .join("runtime")
            .join("lib")
            .join("site-packages")
            .join("pdf2zh_next")
            .join("assets")
            .join("glossaries"),
        bundled_dir
            .join("pdf2zh_next")
            .join("assets")
            .join("glossaries"),
    ]
    .into_iter()
    .find(|candidate| candidate.join("fashion-01-garment-parts.csv").exists())
}

fn seed_writable_runtime(bundled_dir: &PathBuf, runtime_dir: &PathBuf) -> Result<(), String> {
    copy_missing_tree(bundled_dir.join("config"), runtime_dir.join("config"))?;
    copy_missing_tree(bundled_dir.join("data"), runtime_dir.join("data"))?;
    if let Some(glossary_dir) = bundled_glossary_dir(bundled_dir) {
        copy_missing_tree(glossary_dir, runtime_dir.join("config").join("glossaries"))?;
    }
    copy_missing_file(
        bundled_dir.join("BABELDOC-BUILD-INFO.txt"),
        runtime_dir.join("BABELDOC-BUILD-INFO.txt"),
    )?;
    copy_missing_file(
        bundled_dir.join("README-Fashion-Portable.txt"),
        runtime_dir.join("README-Fashion-Portable.txt"),
    )?;
    Ok(())
}

fn parse_backend_port(backend_url: &str) -> Option<u16> {
    backend_url
        .trim_end_matches('/')
        .rsplit(':')
        .next()
        .and_then(|port| port.parse::<u16>().ok())
}

fn generate_shutdown_token() -> String {
    format!(
        "{}-{}",
        std::process::id(),
        SystemTime::now()
            .duration_since(UNIX_EPOCH)
            .map(|duration| duration.as_nanos())
            .unwrap_or_default()
    )
}

fn send_backend_shutdown_request(backend_url: &str, shutdown_token: &str) -> Result<(), String> {
    let port = parse_backend_port(backend_url)
        .ok_or_else(|| format!("Unable to parse backend shutdown port from {backend_url}"))?;
    let mut stream = TcpStream::connect(("127.0.0.1", port))
        .map_err(|error| format!("Unable to connect to backend shutdown endpoint: {error}"))?;
    stream
        .set_read_timeout(Some(Duration::from_secs(2)))
        .map_err(|error| format!("Unable to set backend shutdown read timeout: {error}"))?;
    stream
        .set_write_timeout(Some(Duration::from_secs(2)))
        .map_err(|error| format!("Unable to set backend shutdown write timeout: {error}"))?;

    let request = format!(
        "POST /api/desktop/shutdown HTTP/1.1\r\n\
         Host: 127.0.0.1:{port}\r\n\
         Connection: close\r\n\
         Content-Length: 0\r\n\
         X-PDFTranslate-Shutdown-Token: {shutdown_token}\r\n\
         \r\n"
    );
    stream
        .write_all(request.as_bytes())
        .map_err(|error| format!("Unable to write backend shutdown request: {error}"))?;

    let mut response = String::new();
    stream
        .read_to_string(&mut response)
        .map_err(|error| format!("Unable to read backend shutdown response: {error}"))?;
    if response.starts_with("HTTP/1.1 200") || response.starts_with("HTTP/1.0 200") {
        Ok(())
    } else {
        Err(format!("Backend shutdown endpoint returned: {response}"))
    }
}

fn terminate_backend_process_tree(child: &mut Child) {
    #[cfg(windows)]
    {
        let pid = child.id().to_string();
        let mut command = Command::new("taskkill");
        configure_hidden_process(&mut command);
        let _ = command
            .args(["/PID", &pid, "/T", "/F"])
            .stdin(Stdio::null())
            .stdout(Stdio::null())
            .stderr(Stdio::null())
            .status();
    }

    let _ = child.kill();
}

fn stop_backend(state: &BackendState) {
    let backend_url = state
        .backend_url
        .lock()
        .ok()
        .and_then(|guard| guard.clone());
    let shutdown_token = state
        .shutdown_token
        .lock()
        .ok()
        .and_then(|guard| guard.clone());

    let Ok(mut child_guard) = state.child.lock() else {
        return;
    };
    let Some(child) = child_guard.as_mut() else {
        return;
    };

    if child.try_wait().ok().flatten().is_none() {
        if let (Some(url), Some(token)) = (&backend_url, &shutdown_token) {
            let _ = send_backend_shutdown_request(url, token);
            let deadline = Instant::now() + Duration::from_secs(6);
            while Instant::now() < deadline {
                if child.try_wait().ok().flatten().is_some() {
                    break;
                }
                thread::sleep(Duration::from_millis(200));
            }
        }
    }

    if child.try_wait().ok().flatten().is_none() {
        terminate_backend_process_tree(child);
        let _ = child.wait();
    }

    *child_guard = None;
    if let Ok(mut url_guard) = state.backend_url.lock() {
        *url_guard = None;
    }
    if let Ok(mut token_guard) = state.shutdown_token.lock() {
        *token_guard = None;
    }
}

fn can_bind(host: &str, port: u16) -> bool {
    TcpListener::bind((host, port)).is_ok()
}

fn resolve_backend_port() -> u16 {
    if let Ok(port) = std::env::var("PDFTRANSLATE_BACKEND_PORT") {
        if let Ok(parsed_port) = port.parse::<u16>() {
            return parsed_port;
        }
    }
    if let Ok(backend_url) = std::env::var("PDFTRANSLATE_BACKEND_URL") {
        if let Some(parsed_port) = parse_backend_port(&backend_url) {
            return parsed_port;
        }
    }

    for port in DEFAULT_BACKEND_PORT..DEFAULT_BACKEND_PORT + 20 {
        if can_bind("127.0.0.1", port) && can_bind("0.0.0.0", port) {
            return port;
        }
    }

    DEFAULT_BACKEND_PORT
}

fn wait_for_backend(child: &mut Child, port: u16) -> Result<(), String> {
    let deadline = Instant::now() + Duration::from_secs(120);
    loop {
        if TcpStream::connect(("127.0.0.1", port)).is_ok() {
            return Ok(());
        }
        if let Some(status) = child
            .try_wait()
            .map_err(|error| format!("Unable to inspect backend process: {error}"))?
        {
            return Err(format!(
                "PDFTranslate backend exited before startup: {status}"
            ));
        }
        if Instant::now() >= deadline {
            return Err("Timed out waiting for PDFTranslate backend to start".to_string());
        }
        thread::sleep(Duration::from_millis(250));
    }
}

fn configure_hidden_process(command: &mut Command) {
    #[cfg(windows)]
    {
        command.creation_flags(CREATE_NO_WINDOW);
    }
}

#[tauri::command]
fn start_backend(app: AppHandle, state: State<'_, BackendState>) -> Result<String, String> {
    let mut guard = state
        .child
        .lock()
        .map_err(|_| "Backend process lock failed".to_string())?;
    if let Some(child) = guard.as_mut() {
        if child
            .try_wait()
            .map_err(|error| format!("Unable to inspect backend process: {error}"))?
            .is_none()
        {
            let saved_url = state
                .backend_url
                .lock()
                .map_err(|_| "Backend URL lock failed".to_string())?
                .clone()
                .unwrap_or_else(|| format!("http://127.0.0.1:{DEFAULT_BACKEND_PORT}"));
            return Ok(saved_url);
        }
        *guard = None;
    }

    let backend_port = resolve_backend_port();
    let backend_url = std::env::var("PDFTRANSLATE_BACKEND_URL")
        .unwrap_or_else(|_| format!("http://127.0.0.1:{backend_port}"));
    let shutdown_token = generate_shutdown_token();

    let bundled_backend = bundled_backend_dir(&app);
    let runtime_dir = desktop_runtime_dir(&app)?;
    let backend_port_arg = backend_port.to_string();
    let data_dir = runtime_dir.join("data");
    let config_dir = runtime_dir.join("config");
    let output_dir = runtime_dir.join("pdf2zh_files");
    let babeldoc_cache_dir = data_dir.join("babeldoc-cache");
    let home_dir = data_dir.join("home");
    let xdg_cache_dir = data_dir.join("xdg-cache");
    let xdg_data_dir = data_dir.join("xdg-data");
    let xdg_config_dir = data_dir.join("xdg-config");

    for dir in [
        &data_dir,
        &config_dir,
        &output_dir,
        &babeldoc_cache_dir,
        &home_dir,
        &xdg_cache_dir,
        &xdg_data_dir,
        &xdg_config_dir,
    ] {
        fs::create_dir_all(dir)
            .map_err(|error| {
                format!("Unable to create backend data dir {:?}: {error}", dir)
            })?;
    }

    let mut command = if let Ok(backend_bin) = std::env::var("PDFTRANSLATE_BACKEND_BIN") {
        let mut command = Command::new(backend_bin);
        command
            .arg("--gui")
            .arg("--server-port")
            .arg(&backend_port_arg);
        command
    } else if let Some(bundled_dir) = bundled_backend {
        seed_writable_runtime(&bundled_dir, &runtime_dir)?;
        let runtime_bin_dir = bundled_dir.join("runtime");
        let python = runtime_bin_dir.join(if cfg!(windows) {
            "python.exe"
        } else {
            "python"
        });
        let pythonw = runtime_bin_dir.join("pythonw.exe");
        let python_bin = if python.exists() { python } else { pythonw };
        let mut command = Command::new(python_bin);
        command
            .arg("-m")
            .arg("pdf2zh_next.main")
            .arg("--gui")
            .arg("--server-port")
            .arg(&backend_port_arg);
        command.env("PDFTRANSLATE_BACKEND_RESOURCE_DIR", bundled_dir);
        command
    } else {
        let mut command = Command::new("pdf2zh");
        command
            .arg("--gui")
            .arg("--server-port")
            .arg(&backend_port_arg);
        command
    };

    let log_dir = runtime_dir.join("logs");
    fs::create_dir_all(&log_dir)
        .map_err(|error| format!("Unable to create backend log dir {:?}: {error}", log_dir))?;
    let stdout_log = log_dir.join("backend.stdout.log");
    let stderr_log = log_dir.join("backend.stderr.log");
    let stdout_file = fs::File::create(&stdout_log)
        .map_err(|error| format!("Unable to create backend stdout log {:?}: {error}", stdout_log))?;
    let stderr_file = fs::File::create(&stderr_log)
        .map_err(|error| format!("Unable to create backend stderr log {:?}: {error}", stderr_log))?;

    configure_hidden_process(&mut command);
    let mut child = command
        .current_dir(&runtime_dir)
        .env("PDF2ZH_RUNTIME_DIR", &runtime_dir)
        .env("PDF2ZH_DATA_DIR", &data_dir)
        .env("PDF2ZH_CONFIG_DIR", &config_dir)
        .env("PDF2ZH_OUTPUT_DIR", &output_dir)
        .env("PDF2ZH_CUSTOMER_GLOSSARY_DIR", &config_dir)
        .env("PDF2ZH_BUILTIN_FASHION_GLOSSARY_DIR", config_dir.join("glossaries"))
        .env("BABELDOC_CACHE_DIR", &babeldoc_cache_dir)
        .env("HOME", &home_dir)
        .env("USERPROFILE", &home_dir)
        .env("XDG_CACHE_HOME", &xdg_cache_dir)
        .env("XDG_DATA_HOME", &xdg_data_dir)
        .env("XDG_CONFIG_HOME", &xdg_config_dir)
        .env("PYTHONDONTWRITEBYTECODE", "1")
        .env("PYTHONUTF8", "1")
        .env("PDFTRANSLATE_SHUTDOWN_TOKEN", &shutdown_token)
        .stdin(Stdio::null())
        .stdout(Stdio::from(stdout_file))
        .stderr(Stdio::from(stderr_file))
        .spawn()
        .map_err(|error| format!("Unable to start PDFTranslate backend: {error}"))?;

    if let Err(error) = wait_for_backend(&mut child, backend_port) {
        let _ = child.kill();
        return Err(format!(
            "{error}. Backend logs: {:?}, {:?}",
            stdout_log, stderr_log
        ));
    }
    *state
        .backend_url
        .lock()
        .map_err(|_| "Backend URL lock failed".to_string())? = Some(backend_url.clone());
    *state
        .shutdown_token
        .lock()
        .map_err(|_| "Backend shutdown token lock failed".to_string())? = Some(shutdown_token);
    *guard = Some(child);
    Ok(backend_url)
}

#[tauri::command]
fn save_download_file(
    url: String,
    auth_header: Option<String>,
    suggested_name: String,
) -> Result<bool, String> {
    let Some(destination) = rfd::FileDialog::new()
        .set_file_name(suggested_name)
        .save_file()
    else {
        return Ok(false);
    };

    let mut request = ureq::get(&url);
    if let Some(auth_header) = auth_header.as_deref() {
        if !auth_header.trim().is_empty() {
            request = request.set("Authorization", auth_header);
        }
    }

    let response = request.call().map_err(|error| match error {
        ureq::Error::Status(code, response) => {
            format!("Download failed with HTTP {code}: {}", response.status_text())
        }
        other => format!("Download failed: {other}"),
    })?;

    let mut reader = response.into_reader();
    let mut output = fs::File::create(&destination)
        .map_err(|error| format!("Unable to create {:?}: {error}", destination))?;
    std::io::copy(&mut reader, &mut output)
        .map_err(|error| format!("Unable to save {:?}: {error}", destination))?;
    Ok(true)
}

fn main() {
    let app = tauri::Builder::default()
        .manage(BackendState {
            child: Mutex::new(None),
            backend_url: Mutex::new(None),
            shutdown_token: Mutex::new(None),
        })
        .invoke_handler(tauri::generate_handler![start_backend, save_download_file])
        .build(tauri::generate_context!())
        .expect("error while running PDFTranslate desktop app");

    app.run(|app_handle, event| {
        if let tauri::RunEvent::ExitRequested { .. } = event {
            let state = app_handle.state::<BackendState>();
            stop_backend(state.inner());
        }
    });
}
