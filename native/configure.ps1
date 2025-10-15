param(
    [string]$QtRoot = "C:\\Qt",
    [string]$BuildDir = "build-qt-mingw",
    [string]$Generator = "Ninja",
    [string]$BuildType = "Release",
    [switch]$EnableWhisper,
    [switch]$UseLocalDeps = $true,
    [switch]$ConfigureOnly,
    [string]$WindeployQt = ""
)

# ASCII-only comments to avoid encoding issues
$ScriptRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjectRoot = Split-Path -Parent $ScriptRoot
$ThirdPartyRoot = Join-Path $ScriptRoot "third_party"

Write-Host "[configure] ScriptRoot = $ScriptRoot"
Write-Host "[configure] ProjectRoot = $ProjectRoot"
Write-Host "[configure] ThirdPartyRoot = $ThirdPartyRoot"

# ---- Helper: Copy FFmpeg runtime DLLs to target dir ----
function Copy-FFmpegRuntime {
    param(
        [string]$TargetDir
    )
    try {
        $ffmpegRoot = Join-Path $ThirdPartyRoot "ffmpeg"
        if (-not (Test-Path $ffmpegRoot)) { return }
        $dlls = @()
        $binDir = Join-Path $ffmpegRoot "bin"
        $libDir = Join-Path $ffmpegRoot "lib"
        if (Test-Path $binDir) { $dlls += Get-ChildItem -Path $binDir -Filter "*.dll" -ErrorAction SilentlyContinue }
        if (Test-Path $libDir) { $dlls += Get-ChildItem -Path $libDir -Filter "*.dll" -ErrorAction SilentlyContinue }
        if ($dlls.Count -gt 0) {
            Write-Host "[deploy] Copy FFmpeg DLLs to $TargetDir"
            foreach ($d in $dlls) {
                Copy-Item $d.FullName -Destination $TargetDir -Force -ErrorAction SilentlyContinue
            }
        }
    } catch {
        Write-Warning "[deploy] FFmpeg runtime copy failed: $($_.Exception.Message)"
    }
}

# ---- Helper: Copy MinGW runtime DLLs (compiler runtime + gomp) ----
function Copy-MinGwRuntime {
    param(
        [string]$ToolchainBin,
        [string]$TargetDir
    )
    try {
        if (-not (Test-Path $ToolchainBin)) { return }
        $runtimeDlls = @(
            "libstdc++-6.dll",
            "libgcc_s_seh-1.dll",
            "libwinpthread-1.dll",
            "libgomp-1.dll"
        )
        foreach ($name in $runtimeDlls) {
            $src = Join-Path $ToolchainBin $name
            if (Test-Path $src) {
                Write-Host "[deploy] Copy $name to $TargetDir"
                Copy-Item $src -Destination $TargetDir -Force -ErrorAction SilentlyContinue
            }
        }
    } catch {
        Write-Warning "[deploy] MinGW runtime copy failed: $($_.Exception.Message)"
    }
}

# ---- Helper: Run windeployqt for GUI exe ----
function Deploy-QtGui {
    param(
        [string]$QtPrefix,
        [string]$GuiExe,
        [string]$BuildType,
        [string]$WindeployPath
    )
    try {
        $windeploy = $null
        if ($WindeployPath -and (Test-Path $WindeployPath)) {
            $windeploy = $WindeployPath
        } else {
            $windeploy = Join-Path (Join-Path $QtPrefix "bin") "windeployqt.exe"
        }
        if (-not (Test-Path $windeploy)) { Write-Warning "[deploy] windeployqt.exe not found at $windeploy"; return }
        $mode = if ($BuildType -match "(?i)debug") { "--debug" } else { "--release" }
        Write-Host "[deploy] $windeploy --compiler-runtime $mode $GuiExe"
        & $windeploy --compiler-runtime $mode $GuiExe | Write-Output
    } catch {
        Write-Warning "[deploy] windeployqt failed: $($_.Exception.Message)"
    }
}

function Find-QtPrefixMingw {
    param([string]$Root)
    if (-not (Test-Path $Root)) { return $null }
    # Find Qt version directory that contains mingw_64 (Qt libraries/cmake live here)
    $candidates = Get-ChildItem -Path $Root -Recurse -Directory -ErrorAction SilentlyContinue | Where-Object { $_.Name -eq 'mingw_64' }
    foreach ($dir in $candidates) {
        $qtCmakeDir = Join-Path $dir.FullName "lib\cmake\Qt6"
        if (Test-Path $qtCmakeDir) { return $dir.FullName }
    }
    return $null
}

function Find-MingwToolchain {
    param([string]$Root)
    if (-not (Test-Path $Root)) { return $null }
    # Typical Qt installs keep MinGW toolchain under Tools/mingw*/bin
    $candidates = Get-ChildItem -Path (Join-Path $Root "Tools") -Directory -ErrorAction SilentlyContinue | Where-Object { $_.Name -match '^mingw\d+_64$' }
    foreach ($dir in $candidates) {
        $gpp = Join-Path $dir.FullName "bin\g++.exe"
        $gcc = Join-Path $dir.FullName "bin\gcc.exe"
        if ((Test-Path $gpp) -and (Test-Path $gcc)) { return $dir.FullName }
    }
    # Fallback: search recursively for a mingw toolchain dir that has g++/gcc
    $allDirs = Get-ChildItem -Path $Root -Recurse -Directory -ErrorAction SilentlyContinue | Where-Object { $_.Name -match '^mingw\d+_64$' -or $_.Name -eq 'mingw_64' }
    foreach ($dir in $allDirs) {
        $gpp = Join-Path $dir.FullName "bin\g++.exe"
        $gcc = Join-Path $dir.FullName "bin\gcc.exe"
        if ((Test-Path $gpp) -and (Test-Path $gcc)) { return $dir.FullName }
    }
    return $null
}

$QtPrefix = Find-QtPrefixMingw -Root $QtRoot
if ($null -eq $QtPrefix) {
    Write-Warning "Qt libraries prefix (mingw_64) not found under $QtRoot"
} else {
    Write-Host "[configure] Qt prefix = $QtPrefix"
    $QtBin = Join-Path $QtPrefix "bin"
    $env:PATH = "$QtBin;" + $env:PATH
}

$ToolchainDir = Find-MingwToolchain -Root $QtRoot
if ($null -eq $ToolchainDir) {
    Write-Warning "MinGW toolchain not found under $QtRoot/Tools; will rely on system PATH"
}
else {
    Write-Host "[configure] MinGW toolchain = $ToolchainDir"
    $ToolchainBin = Join-Path $ToolchainDir "bin"
    $env:PATH = "$ToolchainBin;" + $env:PATH
}

$CCompiler = if ($ToolchainDir) { Join-Path $ToolchainDir "bin\gcc.exe" } else { "gcc" }
$CxxCompiler = if ($ToolchainDir) { Join-Path $ToolchainDir "bin\g++.exe" } else { "g++" }

$cmakeArgs = @(
    "-S", $ScriptRoot,
    "-B", (Join-Path $ScriptRoot $BuildDir),
    "-G", $Generator,
    "-DCMAKE_BUILD_TYPE=$BuildType",
    "-DCMAKE_C_COMPILER=$CCompiler",
    "-DCMAKE_CXX_COMPILER=$CxxCompiler",
    "-DCMAKE_PREFIX_PATH=$QtPrefix"
)

if ($UseLocalDeps) {
    $cmakeArgs += @("-DV2S_USE_LOCAL_DEPS=ON", "-DV2S_THIRD_PARTY_DIR=$ThirdPartyRoot")
    $jsonInc = Join-Path $ThirdPartyRoot "nlohmann_json\include\nlohmann\json.hpp"
    if (Test-Path $jsonInc) {
        $jsonRoot = Join-Path $ThirdPartyRoot "nlohmann_json"
        $cmakeArgs += @("-DNLOHMANN_JSON_ROOT=$jsonRoot")
        Write-Host "[configure] Found local nlohmann_json at $jsonRoot"
    } else {
        Write-Warning "Local nlohmann_json not found under third_party; will use package manager if available"
    }
}

if ($EnableWhisper.IsPresent) {
    $cmakeArgs += @("-DV2S_ENABLE_WHISPER=ON")
} else {
    $cmakeArgs += @("-DV2S_ENABLE_WHISPER=OFF")
}

Write-Host "[configure] cmake " ($cmakeArgs -join ' ')
cmake @cmakeArgs
if ($LASTEXITCODE -ne 0) {
    Write-Error "CMake configure failed"
    exit 1
}

if (-not $ConfigureOnly) {
    $procs = (Get-CimInstance Win32_ComputerSystem).NumberOfLogicalProcessors
    if (-not $procs) { $procs = 4 }
    Write-Host "[build] cmake --build $BuildDir -j $procs"
    cmake --build (Join-Path $ScriptRoot $BuildDir) -j $procs
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

    # Post-build deploy: copy third-party runtime dependencies to program directories
    $GuiExe = Join-Path (Join-Path $ScriptRoot $BuildDir) "apps\qtgui\v2s_qt.exe"
    $CliExe = Join-Path (Join-Path $ScriptRoot $BuildDir) "apps\cli\v2s_cli.exe"
    $GuiDir = Split-Path -Parent $GuiExe
    $CliDir = Split-Path -Parent $CliExe

    # Deploy Qt runtime to GUI
    if (Test-Path $GuiExe -PathType Leaf -ErrorAction SilentlyContinue) {
        if ($WindeployQt -and (Test-Path $WindeployQt)) {
            Deploy-QtGui -QtPrefix $QtPrefix -GuiExe $GuiExe -BuildType $BuildType -WindeployPath $WindeployQt
        } elseif ($QtPrefix) {
            Deploy-QtGui -QtPrefix $QtPrefix -GuiExe $GuiExe -BuildType $BuildType -WindeployPath ""
        } else {
            Write-Warning "[deploy] QtPrefix or WindeployQt not provided; skip windeployqt"
        }
    }

    # Copy FFmpeg DLLs to both GUI and CLI
    if (Test-Path $GuiDir) { Copy-FFmpegRuntime -TargetDir $GuiDir }
    if (Test-Path $CliDir) { Copy-FFmpegRuntime -TargetDir $CliDir }

    # Copy MinGW runtime DLLs to CLI (windeployqt handles GUI compiler runtime, but ensure both)
    if ($ToolchainBin) {
        if (Test-Path $GuiDir) { Copy-MinGwRuntime -ToolchainBin $ToolchainBin -TargetDir $GuiDir }
        if (Test-Path $CliDir) { Copy-MinGwRuntime -ToolchainBin $ToolchainBin -TargetDir $CliDir }
    }

    Write-Host "[deploy] Third-party runtime dependencies copied to $GuiDir and $CliDir"
    exit 0
}

exit 0