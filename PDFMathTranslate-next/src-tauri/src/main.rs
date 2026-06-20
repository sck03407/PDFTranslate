#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

use std::fs;
use std::net::{TcpListener, TcpStream};
use std::path::PathBuf;
use std::process::{Child, Command, Stdio};
use std::sync::Mutex;
use std::thread;
use std::time::{Duration, Instant};
use tauri::{AppHandle, Manager, State};

#[cfg(windows)]
use std::os::windows::process::CommandExt;

#[cfg(windows)]
const CREATE_NO_WINDOW: u32 = 0x08000000;

const DEFAULT_BACKEND_PORT: u16 = 7860;

struct BackendState {
    child: Mutex<Option<Child>>,
    backend_url: Mutex<Option<String>>,
}

impl Drop for BackendState {
    fn drop(&mut self) {
        if let Ok(mut child_guard) = self.child.lock() {
            if let Some(child) = child_guard.as_mut() {
                let _ = child.kill();
            }
        }
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

fn desktop_runtime_dir(app: &AppHandle) -> Result<PathBuf, String> {
    if let Ok(runtime_dir) = std::env::var("PDFTRANSLATE_RUNTIME_DIR") {
        return Ok(PathBuf::from(runtime_dir));
    }
    if let Ok(runtime_dir) = std::env::var("PDF2ZH_RUNTIME_DIR") {
        return Ok(PathBuf::from(runtime_dir));
    }
    app.path()
        .app_data_dir()
        .map_err(|error| format!("Unable to resolve app data directory: {error}"))
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

fn seed_writable_runtime(bundled_dir: &PathBuf, runtime_dir: &PathBuf) -> Result<(), String> {
    copy_missing_tree(bundled_dir.join("config"), runtime_dir.join("config"))?;
    copy_missing_tree(bundled_dir.join("data"), runtime_dir.join("data"))?;
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
        let pythonw = runtime_bin_dir.join("pythonw.exe");
        let python = runtime_bin_dir.join(if cfg!(windows) {
            "python.exe"
        } else {
            "python"
        });
        let python_bin = if pythonw.exists() { pythonw } else { python };
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

    configure_hidden_process(&mut command);
    let mut child = command
        .current_dir(&runtime_dir)
        .env("PDF2ZH_RUNTIME_DIR", &runtime_dir)
        .env("PDF2ZH_DATA_DIR", &data_dir)
        .env("PDF2ZH_CONFIG_DIR", &config_dir)
        .env("PDF2ZH_OUTPUT_DIR", &output_dir)
        .env("PDF2ZH_CUSTOMER_GLOSSARY_DIR", &config_dir)
        .env("BABELDOC_CACHE_DIR", &babeldoc_cache_dir)
        .env("HOME", &home_dir)
        .env("USERPROFILE", &home_dir)
        .env("XDG_CACHE_HOME", &xdg_cache_dir)
        .env("XDG_DATA_HOME", &xdg_data_dir)
        .env("XDG_CONFIG_HOME", &xdg_config_dir)
        .env("PYTHONDONTWRITEBYTECODE", "1")
        .env("PYTHONUTF8", "1")
        .stdin(Stdio::null())
        .stdout(Stdio::null())
        .stderr(Stdio::null())
        .spawn()
        .map_err(|error| format!("Unable to start PDFTranslate backend: {error}"))?;

    wait_for_backend(&mut child, backend_port)?;
    *state
        .backend_url
        .lock()
        .map_err(|_| "Backend URL lock failed".to_string())? = Some(backend_url.clone());
    *guard = Some(child);
    Ok(backend_url)
}

fn main() {
    tauri::Builder::default()
        .manage(BackendState {
            child: Mutex::new(None),
            backend_url: Mutex::new(None),
        })
        .invoke_handler(tauri::generate_handler![start_backend])
        .run(tauri::generate_context!())
        .expect("error while running PDFTranslate desktop app");
}
