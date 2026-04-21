$ErrorActionPreference = "Stop"

$codeRoot = Split-Path -Parent $PSScriptRoot
$toolsRoot = Join-Path $codeRoot "tools\piper"
$voicesRoot = Join-Path $codeRoot "data\voices\piper"

New-Item -ItemType Directory -Force -Path $toolsRoot | Out-Null
New-Item -ItemType Directory -Force -Path $voicesRoot | Out-Null

$zipPath = Join-Path $toolsRoot "piper_windows_amd64.zip"
$releaseUrl = "https://github.com/rhasspy/piper/releases/download/2023.11.14-2/piper_windows_amd64.zip"

Write-Host "Downloading Piper runtime..."
Invoke-WebRequest -Uri $releaseUrl -OutFile $zipPath
Expand-Archive -LiteralPath $zipPath -DestinationPath $toolsRoot -Force
Remove-Item -LiteralPath $zipPath -Force

$voiceBases = @{
    "de_DE-thorsten-high" = "https://huggingface.co/rhasspy/piper-voices/resolve/main/de/de_DE/thorsten/high/"
    "en_GB-alan-medium" = "https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_GB/alan/medium/"
    "pl_PL-darkman-medium" = "https://huggingface.co/rhasspy/piper-voices/resolve/main/pl/pl_PL/darkman/medium/"
    "ro_RO-mihai-medium" = "https://huggingface.co/rhasspy/piper-voices/resolve/main/ro/ro_RO/mihai/medium/"
    "ru_RU-ruslan-medium" = "https://huggingface.co/rhasspy/piper-voices/resolve/main/ru/ru_RU/ruslan/medium/"
}

foreach ($voice in $voiceBases.GetEnumerator()) {
    $name = $voice.Key
    $base = $voice.Value
    Write-Host "Downloading voice $name..."
    Invoke-WebRequest -Uri ($base + $name + ".onnx?download=true") -OutFile (Join-Path $voicesRoot ($name + ".onnx"))
    Invoke-WebRequest -Uri ($base + $name + ".onnx.json?download=true") -OutFile (Join-Path $voicesRoot ($name + ".onnx.json"))
}

Write-Host ""
Write-Host "Installed Piper to:" (Join-Path $toolsRoot "piper\piper.exe")
Write-Host "Installed voices to:" $voicesRoot
