#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

use std::process::{Child, Command, Stdio};
use std::sync::Mutex;
use tauri::State;

struct BackendState {
    child: Mutex<Option<Child>>,
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
    let child = Command::new(backend_bin)
        .args(["--gui", "--server-port", "7860"])
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
