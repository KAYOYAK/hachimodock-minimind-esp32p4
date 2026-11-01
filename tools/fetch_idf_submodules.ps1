# Fetch the ESP-IDF submodules needed for a WiFi/BT-off ESP32-P4 build.
# GitHub is not reachable directly here; archives go through gh-proxy.com.
$ErrorActionPreference = "Stop"
$zipDir = "C:\p4test\work\idf_submodules"
New-Item -ItemType Directory -Force -Path $zipDir | Out-Null

$items = @(
    @{ name = "micro-ecc";  repo = "kmackay/micro-ecc";          sha = "24c60e243580c7868f4334a1ba3123481fe1aa48"; dst = "C:\espidf\esp-idf\components\bootloader\subproject\components\micro-ecc\micro-ecc" },
    @{ name = "mbedtls";    repo = "espressif/mbedtls";          sha = "a2b32072ea898afc1ed5b6caf6931e36028c91d6"; dst = "C:\espidf\esp-idf\components\mbedtls\mbedtls" },
    @{ name = "lwip";       repo = "espressif/esp-lwip";         sha = "c6f2f878e7b0f86033214b85547d579be43351e3"; dst = "C:\espidf\esp-idf\components\lwip\lwip" },
    @{ name = "protobuf-c"; repo = "protobuf-c/protobuf-c";      sha = "abc67a11c6db271bedbb9f58be85d6f4e2ea8389"; dst = "C:\espidf\esp-idf\components\protobuf-c\protobuf-c" },
    @{ name = "tlsf";       repo = "espressif/tlsf";             sha = "2867f6883a12920b1969ff9624c0ab0e4185c2ce"; dst = "C:\espidf\esp-idf\components\heap\tlsf" }
)

foreach ($it in $items) {
    $zip = Join-Path $zipDir ($it.name + ".zip")
    if (-not (Test-Path $zip) -or (Get-Item $zip).Length -lt 1000) {
        $url = "https://gh-proxy.com/https://github.com/" + $it.repo + "/archive/" + $it.sha + ".zip"
        Write-Host "downloading $($it.name) ..."
        & curl.exe -s -L --max-time 900 --retry 3 -o $zip $url
        if ($LASTEXITCODE -ne 0) { throw "download failed: $($it.name)" }
    }
    Write-Host "  $($it.name) zip = $((Get-Item $zip).Length) bytes"
    $tmp = Join-Path $zipDir ($it.name + "_x")
    if (Test-Path $tmp) { Remove-Item -Recurse -Force $tmp }
    Expand-Archive -Path $zip -DestinationPath $tmp -Force
    $inner = Get-ChildItem $tmp -Directory | Select-Object -First 1
    if (-not $inner) { throw "no top dir in $($it.name) zip" }
    if (Test-Path $it.dst) { Remove-Item -Recurse -Force $it.dst }
    New-Item -ItemType Directory -Force -Path (Split-Path $it.dst) | Out-Null
    Move-Item $inner.FullName $it.dst
    Remove-Item -Recurse -Force $tmp
    Write-Host "  installed -> $($it.dst)"
}
Write-Host "all needed submodules installed"
