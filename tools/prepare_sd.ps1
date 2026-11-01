# 准备 TF 卡（FAT32）：复制模型镜像与 tokenizer
# 用法：powershell -ExecutionPolicy Bypass -File tools\prepare_sd.ps1 -Drive E:
param([Parameter(Mandatory=$true)][string]$Drive)

$ErrorActionPreference = "Stop"
$root = $Drive.TrimEnd('\') + '\'
if (-not (Test-Path $root)) { throw "drive not found: $root" }

$files = @(
    @{ src = "C:\p4test\artifacts\minimind-3-q3e4.kmcu"; dst = "model.kmcu" },
    @{ src = "C:\p4test\artifacts\tokenizer.bin";         dst = "tokenizer.bin" }
)
foreach ($f in $files) {
    if (-not (Test-Path $f.src)) { throw "missing $($f.src)" }
    Copy-Item $f.src (Join-Path $root $f.dst) -Force
    $len = (Get-Item (Join-Path $root $f.dst)).Length
    Write-Host ("copied {0} -> {1} ({2:N0} bytes)" -f $f.src, $f.dst, $len)
}
Write-Host "SD card ready at $root"
