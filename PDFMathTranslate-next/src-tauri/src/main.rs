#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

use std::fs;
use std::path::PathBuf;
use std::process::{Child, Command, Stdio};
use std::sync::Mutex;
use tauri::State;

struct BackendState {
    child: Mutex<Option<Child>>,
}

fn desktop_runtime_dir() -> Result<PathBuf, String> {
    if let Ok(runtime_dir) = std::env::var("PDFTRANSLATE_RUNTIME_DIR") {
        return Ok(PathBuf::from(runtime_dir));
    }
    if let Ok(runtime_dir) = std::env::var("PDF2ZH_RUNTIME_DIR") {
        return Ok(PathBuf::from(runtime_dir));
    }
    let exe = std::env::current_exe()
        .map_err(|error| format!("Unable to resolve desktop executable path: {error}"))?;
    Ok(exe
        .parent()
        .map(PathBuf::from)
        .unwrap_or_else(|| PathBuf::from(".")))
}

#[tauri::command]
fn start_backend(state: State<'_, BackendState>) -> Result<String, String> {
    let backend_url = std::env::var("PDFTRANSLATE_BACKEND_URL")
        .unwrap_or_else(|_| "http://127.0.0.1:7860".to_string());

    let mut guard = state
        .child
        .lock()
        .map_err(|_| "Backend process lock failed".to_string())?;
    if guard.is_some() {
        return Ok(backend_url);
    }

    let backend_bin =
        std::env::var("PDFTRANSLATE_BACKEND_BIN").unwrap_or_else(|_| "pdf2zh".to_string());
    let runtime_dir = desktop_runtime_dir()?;
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
            .map_err(|error| format!("Unable to create backend data dir {:?}: {error}", dir))?;
    }

    let child = Command::new(backend_bin)
        .args(["--gui", "--server-port", "7860"])
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
        .stdin(Stdio::null())
        .stdout(Stdio::null())
        .stderr(Stdio::null())
        .spawn()
        .map_err(|error| format!("Unable to start PDFTranslate backend: {error}"))?;
    *guard = Some(child);
    Ok(backend_url)
}

fn main() {
    tauri::Builder::default()
        .manage(BackendState {
            child: Mutex::new(None),
        })
        .invoke_handler(tauri::generate_handler![start_backend])
        .run(tauri::generate_context!())
        .expect("error while running PDFTranslate desktop app");
}
