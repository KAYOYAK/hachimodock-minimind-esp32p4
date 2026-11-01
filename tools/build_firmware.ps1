# 一键构建 ESP32-P4 固件（使用本机已安装的 ESP-IDF 6.x + 隔离 Python 环境）
# 用法：powershell -ExecutionPolicy Bypass -File tools\build_firmware.ps1 [-Clean]
param([switch]$Clean)

$ErrorActionPreference = "Stop"

$IDF_PATH   = "C:\espidf\esp-idf"
$IDF_PY     = "C:\p4test\vendor\idf_py\python.exe"
$IDF_PY_DIR = "C:\p4test\vendor\idf_py"
$TOOLS_PATH = "C:\et"
$APP_DIR    = "C:\p4test\firmware_app"

if (-not (Test-Path $IDF_PATH)) { throw "ESP-IDF not found at $IDF_PATH" }
if (-not (Test-Path $IDF_PY))   { throw "isolated Python not found at $IDF_PY" }

$env:IDF_PATH = $IDF_PATH
$env:IDF_TOOLS_PATH = $TOOLS_PATH
$env:IDF_SKIP_CHECK_SUBMODULES = "1"
$env:IDF_PYTHON_CHECK_CONSTRAINTS = "0"
$env:PATH = "$IDF_PY_DIR;$env:PATH"

# activate ESP-IDF environment (sets toolchain paths in this process)
& "$IDF_PATH\export.ps1"

Push-Location $APP_DIR
try {
    if ($Clean) { & idf.py fullclean }
    & idf.py set-target esp32p4
    if ($LASTEXITCODE -ne 0) { throw "set-target failed" }
    & idf.py build
    if ($LASTEXITCODE -ne 0) { throw "build failed" }
    Write-Host "BUILD OK: $APP_DIR\build\minimind_p4.bin"
} finally {
    Pop-Location
}
