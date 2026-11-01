# Build the USB-Host protocol bridge test firmware (firmware_pethost).
param([switch]$Clean)

$ErrorActionPreference = "Stop"

$IDF_PATH   = "C:\espidf\esp-idf"
$IDF_PY     = "C:\p4test\vendor\idf_py\python.exe"
$IDF_PY_DIR = "C:\p4test\vendor\idf_py"
$TOOLS_PATH = "C:\et"
$APP_DIR    = "C:\p4test\firmware_pethost"

$env:IDF_PATH = $IDF_PATH
$env:IDF_TOOLS_PATH = $TOOLS_PATH
$env:IDF_SKIP_CHECK_SUBMODULES = "1"
$env:IDF_PYTHON_CHECK_CONSTRAINTS = "0"
$env:PATH = "$IDF_PY_DIR;$env:PATH"

& "$IDF_PATH\export.ps1"

Push-Location $APP_DIR
try {
    if ($Clean) { & idf.py fullclean }
    & idf.py set-target esp32p4
    if ($LASTEXITCODE -ne 0) { throw "set-target failed" }
    & idf.py build
    if ($LASTEXITCODE -ne 0) { throw "build failed" }
    Write-Host "BUILD OK: $APP_DIR\build\pethost.bin"
} finally {
    Pop-Location
}
