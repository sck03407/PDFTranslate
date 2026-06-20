param(
    [string]$OutputDir = (Join-Path (Resolve-Path (Join-Path $PSScriptRoot "..")) "dist\pdftranslate-portable"),
    [string]$PythonVersion = "3.13.3",
    [ValidateSet("local-stable", "github-latest", "github-ref")]
    [string]$BabelDOCSource = "local-stable",
    [string]$BabelDOCGitRef = "",
    [string]$LocalBabelDOCPath = (Join-Path (Resolve-Path (Join-Path $PSScriptRoot "..")) "..\BabelDOC"),
    [string]$StableBabelDOCRef = "v0.6.3"
)

$ErrorActionPreference = "Stop"

$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$OutputDir = [System.IO.Path]::GetFullPath($OutputDir)
$RuntimeDir = Join-Path $OutputDir "runtime"
$ConfigDir = Join-Path $OutputDir "config"
$DataDir = Join-Path $OutputDir "data"
$OutputFilesDir = Join-Path $OutputDir "pdf2zh_files"
$AssetsDir = Join-Path $OutputDir "assets"
$BuildEnv = Join-Path $RepoRoot ".build_fashion_env"
$EmbedZip = Join-Path $RepoRoot ".build_fashion_python.zip"
$PortableZip = "$OutputDir.zip"

function Assert-SafeDirectory {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Path
    )

    $resolved = [System.IO.Path]::GetFullPath($Path)
    $root = [System.IO.Path]::GetPathRoot($resolved)
    if ([string]::IsNullOrWhiteSpace($resolved) -or $resolved -eq $root) {
        throw "Refusing to operate on unsafe directory path: $resolved"
    }
}

function Remove-DirectoryIfExists {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Path
    )

    Assert-SafeDirectory -Path $Path
    if (Test-Path -LiteralPath $Path) {
        Remove-Item -LiteralPath $Path -Recurse -Force
    }
}

function Write-Utf8NoBomFile {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Path,
        [Parameter(Mandatory = $true)]
        [string]$Content
    )

    $utf8NoBom = New-Object System.Text.UTF8Encoding($false)
    [System.IO.File]::WriteAllText($Path, $Content, $utf8NoBom)
}

function Resolve-BuildPythonInterpreter {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Version
    )

    function Get-PythonVersionFamily {
        param(
            [Parameter(Mandatory = $true)]
            [string]$RawVersion
        )

        $parts = $RawVersion -split '\.'
        if ($parts.Length -lt 2) {
            return $RawVersion
        }
        return ($parts[0..1] -join '.')
    }

    function Test-PythonVersionMatch {
        param(
            [Parameter(Mandatory = $true)]
            [string]$ExecutablePath,
            [Parameter(Mandatory = $true)]
            [string]$ExpectedVersion,
            [switch]$AllowPatchMismatch
        )

        $resolvedVersion = (& $ExecutablePath -c "import platform; print(platform.python_version())" 2>$null)
        if ($LASTEXITCODE -ne 0 -or [string]::IsNullOrWhiteSpace($resolvedVersion)) {
            return $false
        }

        $resolvedVersion = $resolvedVersion.Trim()
        if ($resolvedVersion -eq $ExpectedVersion) {
            return $true
        }

        if ($AllowPatchMismatch) {
            return (Get-PythonVersionFamily -RawVersion $resolvedVersion) -eq (Get-PythonVersionFamily -RawVersion $ExpectedVersion)
        }

        return $false
    }

    $majorMinor = Get-PythonVersionFamily -RawVersion $Version

    $setupPythonDirs = @(
        $env:pythonLocation,
        $env:Python_ROOT_DIR,
        $env:Python3_ROOT_DIR,
        $env:Python2_ROOT_DIR
    ) | Where-Object { -not [string]::IsNullOrWhiteSpace($_) } | Select-Object -Unique

    foreach ($candidateDir in $setupPythonDirs) {
        $candidateExe = Join-Path $candidateDir "python.exe"
        if (Test-Path -LiteralPath $candidateExe) {
            if (Test-PythonVersionMatch -ExecutablePath $candidateExe -ExpectedVersion $Version -AllowPatchMismatch) {
                return $candidateExe
            }
        }
    }

    $pythonCmd = Get-Command python -ErrorAction SilentlyContinue
    if ($null -ne $pythonCmd) {
        $resolvedExe = (& $pythonCmd.Source -c "import sys; print(sys.executable)" 2>$null)
        if ($LASTEXITCODE -eq 0 -and -not [string]::IsNullOrWhiteSpace($resolvedExe) -and (Test-PythonVersionMatch -ExecutablePath $resolvedExe.Trim() -ExpectedVersion $Version -AllowPatchMismatch)) {
            return $resolvedExe.Trim()
        }
    }

    $launcher = Get-Command py -ErrorAction SilentlyContinue
    if ($null -ne $launcher) {
        try {
            $candidate = (& $launcher.Source "-$majorMinor" -c "import sys; print(sys.executable)" 2>$null)
        }
        catch {
            $candidate = $null
        }

        if ($LASTEXITCODE -eq 0 -and -not [string]::IsNullOrWhiteSpace($candidate) -and (Test-PythonVersionMatch -ExecutablePath $candidate.Trim() -ExpectedVersion $Version -AllowPatchMismatch)) {
            return $candidate.Trim()
        }
    }

    throw "Python $Version was not found. Install Python $majorMinor (preferred exact version $Version) or expose it through setup-python / PATH before building the portable package."
}

function Get-BabelDOCInstallTarget {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Source,
        [Parameter(Mandatory = $true)]
        [string]$StableRef,
        [string]$GitRef,
        [string]$LocalPath
    )

    switch ($Source) {
        "local-stable" {
            if (Test-Path -LiteralPath $LocalPath) {
                return (Resolve-Path -LiteralPath $LocalPath).Path
            }
            Write-Warning "Local BabelDOC path not found: $LocalPath. Falling back to source ref $StableRef."
            return "git+https://github.com/funstory-ai/BabelDOC.git@$StableRef"
        }
        "github-latest" {
            return "git+https://github.com/funstory-ai/BabelDOC.git"
        }
        "github-ref" {
            if ([string]::IsNullOrWhiteSpace($GitRef)) {
                throw "BabelDOCGitRef must be provided when BabelDOCSource is github-ref."
            }
            return "git+https://github.com/funstory-ai/BabelDOC.git@$GitRef"
        }
        default {
            throw "Unsupported BabelDOCSource: $Source"
        }
    }
}

$BabelDOCInstallTarget = Get-BabelDOCInstallTarget `
    -Source $BabelDOCSource `
    -StableRef $StableBabelDOCRef `
    -GitRef $BabelDOCGitRef `
    -LocalPath $LocalBabelDOCPath
$BuildPythonInterpreter = Resolve-BuildPythonInterpreter -Version $PythonVersion

Write-Host "==> Repo root: $RepoRoot"
Write-Host "==> BabelDOC source mode: $BabelDOCSource"
Write-Host "==> BabelDOC install target: $BabelDOCInstallTarget"
Write-Host "==> Build Python interpreter: $BuildPythonInterpreter"
Write-Host "==> Output dir: $OutputDir"

Remove-DirectoryIfExists -Path $OutputDir
Remove-DirectoryIfExists -Path $BuildEnv
if (Test-Path -LiteralPath $EmbedZip) {
    Remove-Item -LiteralPath $EmbedZip -Force
}
if (Test-Path -LiteralPath $PortableZip) {
    Remove-Item -LiteralPath $PortableZip -Force
}

New-Item -ItemType Directory -Path $RuntimeDir, $ConfigDir, $DataDir, $OutputFilesDir, $AssetsDir | Out-Null

Write-Host "==> Creating build venv"
& $BuildPythonInterpreter -m venv $BuildEnv
$BuildPython = Join-Path $BuildEnv "Scripts\python.exe"

& $BuildPython -m pip install --upgrade pip setuptools wheel
& $BuildPython -m pip install $BabelDOCInstallTarget
& $BuildPython -m pip install $RepoRoot

$InstalledBabelDOCVersion = (& $BuildPython -c "from importlib.metadata import version; print(version('BabelDOC'))").Trim()
Write-Host "==> Installed BabelDOC version: $InstalledBabelDOCVersion"

Write-Host "==> Downloading embedded Python $PythonVersion"
$PythonUrl = "https://www.python.org/ftp/python/$PythonVersion/python-$PythonVersion-embed-amd64.zip"
Invoke-WebRequest -Uri $PythonUrl -OutFile $EmbedZip
Expand-Archive -Path $EmbedZip -DestinationPath $RuntimeDir -Force

$PthFile = Get-ChildItem -Path $RuntimeDir -Filter "python*._pth" | Select-Object -First 1 -ExpandProperty FullName
$PthContent = @()
foreach ($Line in Get-Content -Path $PthFile) {
    if ($Line -eq "#import site") {
        $PthContent += "site-packages"
        $PthContent += "import site"
    }
    else {
        $PthContent += $Line
    }
}
Set-Content -Path $PthFile -Value $PthContent -Encoding Ascii

Write-Host "==> Copying site-packages"
Copy-Item -Path (Join-Path $BuildEnv "Lib\site-packages") -Destination (Join-Path $RuntimeDir "site-packages") -Recurse -Force

$SklearnLibDir = Join-Path $RuntimeDir "site-packages\sklearn\.libs"
foreach ($RequiredDll in @("vcomp140.dll", "msvcp140.dll")) {
    $RequiredDllPath = Join-Path $SklearnLibDir $RequiredDll
    if (-not (Test-Path -LiteralPath $RequiredDllPath)) {
        throw "Portable runtime is missing sklearn\.libs\$RequiredDll. The Windows package would fail before the WebUI starts."
    }
}

Write-Host "==> Generating BabelDOC offline assets"
& $BuildPython -m babeldoc.main --generate-offline-assets $AssetsDir

$OfflineAssetZip = Get-ChildItem -Path $AssetsDir -Filter "offline_assets_*.zip" | Select-Object -First 1
if ($null -eq $OfflineAssetZip) {
    throw "Offline assets zip was not generated."
}

Write-Host "==> Restoring offline assets into portable data directory"
$PreviousPortableEnv = @{
    PDF2ZH_RUNTIME_DIR = $env:PDF2ZH_RUNTIME_DIR
    PDF2ZH_DATA_DIR = $env:PDF2ZH_DATA_DIR
    PDF2ZH_CONFIG_DIR = $env:PDF2ZH_CONFIG_DIR
    PDF2ZH_OUTPUT_DIR = $env:PDF2ZH_OUTPUT_DIR
    PDF2ZH_CUSTOMER_GLOSSARY_DIR = $env:PDF2ZH_CUSTOMER_GLOSSARY_DIR
    BABELDOC_CACHE_DIR = $env:BABELDOC_CACHE_DIR
    HOME = $env:HOME
    USERPROFILE = $env:USERPROFILE
    XDG_CACHE_HOME = $env:XDG_CACHE_HOME
    XDG_DATA_HOME = $env:XDG_DATA_HOME
    XDG_CONFIG_HOME = $env:XDG_CONFIG_HOME
}
$env:PDF2ZH_RUNTIME_DIR = $OutputDir
$env:PDF2ZH_DATA_DIR = $DataDir
$env:PDF2ZH_CONFIG_DIR = $ConfigDir
$env:PDF2ZH_OUTPUT_DIR = Join-Path $OutputDir "pdf2zh_files"
$env:PDF2ZH_CUSTOMER_GLOSSARY_DIR = $ConfigDir
$env:BABELDOC_CACHE_DIR = Join-Path $DataDir "babeldoc-cache"
$env:HOME = Join-Path $DataDir "home"
$env:USERPROFILE = Join-Path $DataDir "home"
$env:XDG_CACHE_HOME = Join-Path $DataDir "xdg-cache"
$env:XDG_DATA_HOME = Join-Path $DataDir "xdg-data"
$env:XDG_CONFIG_HOME = Join-Path $DataDir "xdg-config"
try {
    & $BuildPython -m babeldoc.main --restore-offline-assets $OfflineAssetZip.FullName
    Remove-Item -Force $OfflineAssetZip.FullName
}
finally {
    foreach ($Name in $PreviousPortableEnv.Keys) {
        if ($null -eq $PreviousPortableEnv[$Name]) {
            Remove-Item -Path "Env:$Name" -ErrorAction SilentlyContinue
        }
        else {
            Set-Item -Path "Env:$Name" -Value $PreviousPortableEnv[$Name]
        }
    }
}

Write-Host "==> Copying profile configs"
Copy-Item -Path (Join-Path $RepoRoot "examples\fashion-online-high-quality.toml") -Destination (Join-Path $ConfigDir "fashion-online-high-quality.toml") -Force
Copy-Item -Path (Join-Path $RepoRoot "examples\fashion-customer-glossary-template.csv") -Destination (Join-Path $ConfigDir "fashion-customer-glossary-template.csv") -Force
Copy-Item -Path (Join-Path $RepoRoot "config\distribution.toml") -Destination (Join-Path $ConfigDir "distribution.toml") -Force
Copy-Item -Path (Join-Path $RepoRoot "script\fashion_portable_quickstart.txt") -Destination (Join-Path $OutputDir "README-Fashion-Portable.txt") -Force

$BuildInfo = @"
PDFTranslate Portable Build Info
===========================================

BabelDOC source mode: $BabelDOCSource
BabelDOC install target: $BabelDOCInstallTarget
BabelDOC version: $InstalledBabelDOCVersion
Python embed version: $PythonVersion
"@
Set-Content -Path (Join-Path $OutputDir "BABELDOC-BUILD-INFO.txt") -Value $BuildInfo -Encoding Ascii

$DefaultConfig = @'
siliconflowfree = true

[basic]
gui = false

[translation]
lang_in = "en"
lang_out = "zh"
glossaries = "./fashion-customer-glossary-template.csv"
disable_builtin_fashion_glossary = false
disable_builtin_fashion_prompt = false
no_auto_extract_glossary = false
save_auto_extracted_glossary = false
qps = 4

[pdf]
watermark_output_mode = "no_watermark"
translate_table_text = true

[gui_settings]
brand_name = "PDFTranslate"
brand_url = ""
ui_lang = "zh"
require_gui_login = false
user_username = "user"
user_password = ""
admin_username = "admin"
admin_password = ""
'@
Write-Utf8NoBomFile -Path (Join-Path $ConfigDir "config.v3.toml") -Content $DefaultConfig

$Launcher = @'
@echo off
setlocal
cd /d "%~dp0"
set "PDF2ZH_RUNTIME_DIR=%~dp0"
set "PDF2ZH_DATA_DIR=%~dp0data"
set "PDF2ZH_CONFIG_DIR=%~dp0config"
set "PDF2ZH_OUTPUT_DIR=%~dp0pdf2zh_files"
set "PDF2ZH_CUSTOMER_GLOSSARY_DIR=%~dp0config"
set "BABELDOC_CACHE_DIR=%~dp0data\babeldoc-cache"
set "HOME=%~dp0data\home"
set "USERPROFILE=%~dp0data\home"
set "XDG_CACHE_HOME=%~dp0data\xdg-cache"
set "XDG_DATA_HOME=%~dp0data\xdg-data"
set "XDG_CONFIG_HOME=%~dp0data\xdg-config"
echo.
echo PDFTranslate Portable
echo.
echo Default startup shows the simple PDF translation page.
echo Administrators can edit config\distribution.toml to unlock settings or tune LAN concurrency.
echo.
"%~dp0runtime\python.exe" -m pdf2zh_next.main --gui
'@
Set-Content -Path (Join-Path $OutputDir "Start-Fashion.bat") -Value $Launcher -Encoding Ascii

Write-Host "==> Creating zip archive"
Compress-Archive -Path (Join-Path $OutputDir "*") -DestinationPath $PortableZip -Force

Write-Host "==> Cleaning build venv"
Remove-DirectoryIfExists -Path $BuildEnv
Remove-Item -LiteralPath $EmbedZip -Force

Write-Host "Portable package ready:"
Write-Host "  Folder: $OutputDir"
Write-Host "  Zip:    $PortableZip"
