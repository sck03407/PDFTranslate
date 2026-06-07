param(
    [string]$Tag = "pdfmathtranslate-fashion:local",
    [ValidateSet("local-stable", "github-latest", "github-ref")]
    [string]$BabelDOCSource = "local-stable",
    [string]$BabelDOCGitRef = "",
    [string]$StableBabelDOCRef = "v0.6.3"
)

$ErrorActionPreference = "Stop"
$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path

switch ($BabelDOCSource) {
    "local-stable" {
        $DockerBabelDOCSource = "stable"
    }
    "github-latest" {
        $DockerBabelDOCSource = "latest"
    }
    "github-ref" {
        if ([string]::IsNullOrWhiteSpace($BabelDOCGitRef)) {
            throw "BabelDOCGitRef must be provided when BabelDOCSource is github-ref."
        }
        $DockerBabelDOCSource = "ref"
    }
    default {
        throw "Unsupported BabelDOCSource: $BabelDOCSource"
    }
}

Write-Host "==> Docker tag: $Tag"
Write-Host "==> BabelDOC source mode: $BabelDOCSource"

$BuildArgs = @(
    "build",
    "-f",
    "Dockerfile",
    "--build-arg",
    "BABELDOC_SOURCE=$DockerBabelDOCSource",
    "--build-arg",
    "BABELDOC_STABLE_REF=$StableBabelDOCRef",
    "-t",
    $Tag,
    "."
)

if (-not [string]::IsNullOrWhiteSpace($BabelDOCGitRef)) {
    $BuildArgs += @("--build-arg", "BABELDOC_GIT_REF=$BabelDOCGitRef")
}

Write-Host "==> Running docker build in $RepoRoot"
& docker @BuildArgs
