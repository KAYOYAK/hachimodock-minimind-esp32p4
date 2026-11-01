# 烧写 ESP32-P4 固件（需已构建：tools\build_firmware.ps1）
# 用法：powershell -ExecutionPolicy Bypass -File tools\flash_firmware.ps1 -Port COM5 [-Baud 921600]
param(
    [Parameter(Mandatory=$true)][string]$Port,
    [int]$Baud = 921600
)

$ErrorActionPreference = "Stop"
$build = "C:\p4test\firmware_app\build"
$py = "C:\et\python_env\idf6.1_py3.12_env\Scripts\python.exe"

if (-not (Test-Path "$build\minimind_p4.bin")) { throw "firmware not built: run tools\build_firmware.ps1 first" }
if (-not (Test-Path $py)) { throw "ESP-IDF python not found: $py" }

Push-Location $build
try {
    & $py -m esptool --chip esp32p4 -p $Port -b $Baud --before default-reset --after hard-reset write_flash "@flash_args"
    if ($LASTEXITCODE -ne 0) { throw "flash failed" }
    Write-Host "FLASH OK on $Port"
    Write-Host "打开串口监视： $py -m esp_idf_monitor --port $Port"
} finally {
    Pop-Location
}
