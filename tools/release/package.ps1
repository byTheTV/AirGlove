[CmdletBinding()]
param(
    [string] $NsisCompiler,
    [switch] $PortableOnly
)

$ErrorActionPreference = 'Stop'
$root = (Resolve-Path (Join-Path $PSScriptRoot '../..')).Path
$target = 'x86_64-pc-windows-msvc'
$cargo = (Get-Command cargo.exe -ErrorAction SilentlyContinue).Source
if (-not $cargo) { $cargo = Join-Path $env:USERPROFILE '.cargo/bin/cargo.exe' }
if (-not (Test-Path -LiteralPath $cargo)) { throw 'Install Rust for Windows (MSVC) before packaging AirGlove.' }
if (-not $PortableOnly -and -not $NsisCompiler) {
    $NsisCompiler = (Get-Command makensis.exe -ErrorAction SilentlyContinue).Source
    if (-not $NsisCompiler) {
        $NsisCompiler = Join-Path ${env:ProgramFiles(x86)} 'NSIS/makensis.exe'
    }
}
if (-not $PortableOnly -and -not (Test-Path -LiteralPath $NsisCompiler)) {
    throw 'Install NSIS 3, pass -NsisCompiler, or use -PortableOnly.'
}

Push-Location $root
try {
    & $cargo build --release --locked --target $target
    if ($LASTEXITCODE -ne 0) { throw 'Failed to build AirGlove.' }
    $metadata = & $cargo metadata --locked --format-version 1 --filter-platform $target | ConvertFrom-Json
    if ($LASTEXITCODE -ne 0) { throw 'Failed to read the dependency graph.' }
    $application = $metadata.packages | Where-Object { $_.id -eq $metadata.resolve.root }
    $version = $application.version
    if ($version -notmatch '^\d+\.\d+\.\d+$') { throw 'Packaging requires a three-part Cargo version.' }

    $output = Join-Path $root 'dist'
    New-Item -ItemType Directory -Force -Path $output | Out-Null
    $stage = Join-Path ([IO.Path]::GetTempPath()) "airglove-package-$([Guid]::NewGuid().ToString('N'))"
    New-Item -ItemType Directory -Path $stage | Out-Null
    try {
        $program = Join-Path $stage 'AirGlove.exe'
        Copy-Item -LiteralPath "target/$target/release/airglove.exe" -Destination $program
        Copy-Item -LiteralPath 'tools/release/AirGlove.ico' -Destination $stage
        $help = [IO.File]::ReadAllText((Join-Path $PSScriptRoot 'Readme.txt'))
        $bom = [Text.UTF8Encoding]::new($true)
        [IO.File]::WriteAllText((Join-Path $stage 'Readme.txt'), $help.Replace('{version}', $version), $bom)

        $notices = [Text.StringBuilder]::new()
        [void] $notices.AppendLine('AirGlove — third-party notices for the Windows x64 build.')
        $runtimeDependencies = & $cargo tree --locked --target $target --edges normal --prefix none --format '{p}'
        if ($LASTEXITCODE -ne 0) { throw 'Failed to list runtime dependencies.' }
        $used = @{}
        foreach ($row in $runtimeDependencies) {
            if ($row -match '^(\S+) v(\S+)') { $used["$($Matches[1])@$($Matches[2])"] = $true }
        }
        foreach ($package in ($metadata.packages | Sort-Object name, version)) {
            if ($package.id -eq $application.id -or -not $used.ContainsKey("$($package.name)@$($package.version)")) { continue }
            $crate = Split-Path -Parent $package.manifest_path
            [void] $notices.AppendLine().AppendLine(('=' * 72))
            [void] $notices.AppendLine("$($package.name) $($package.version) — $($package.license)")
            if ($package.repository) { [void] $notices.AppendLine($package.repository) }
            $files = @(Get-ChildItem -LiteralPath $crate -File -Recurse | Where-Object {
                $_.Name -match '^(LICENSE|LICENCE|COPYING|COPYRIGHT|NOTICE|OFL|UFL|SIL-OFL)([._-]|$)|[-_.](license|licence|notice)([._-]|$)|^Hack-Regular\.txt$'
            })
            if ($package.license_file) {
                $files += Get-Item -LiteralPath (Join-Path $crate $package.license_file)
            }
            foreach ($file in ($files | Sort-Object FullName -Unique)) {
                $relative = $file.FullName.Substring($crate.Length + 1)
                [void] $notices.AppendLine().AppendLine($relative)
                [void] $notices.AppendLine([IO.File]::ReadAllText($file.FullName))
            }
        }
        [IO.File]::WriteAllText((Join-Path $stage 'THIRD-PARTY-NOTICES.txt'), $notices.ToString(), $bom)

        $portable = Join-Path $output "AirGlove-$version-windows-x64.zip"
        Compress-Archive -LiteralPath $program,(Join-Path $stage 'Readme.txt'),(Join-Path $stage 'THIRD-PARTY-NOTICES.txt') -DestinationPath $portable -Force
        $artifacts = @($portable)
        if (-not $PortableOnly) {
            $installer = Join-Path $output "AirGlove-$version-windows-x64-setup.exe"
            & $NsisCompiler '/V3' "/DStageDir=$stage" "/DOutputFile=$installer" "/DAppVersion=$version" (Join-Path $PSScriptRoot 'AirGlove.nsi')
            if ($LASTEXITCODE -ne 0) { throw 'NSIS failed to build the installer.' }
            $artifacts += $installer
        }
        $checksums = foreach ($artifact in $artifacts) {
            $hash = (Get-FileHash -Algorithm SHA256 -LiteralPath $artifact).Hash.ToLowerInvariant()
            "$hash  $([IO.Path]::GetFileName($artifact))"
        }
        $checksums | Set-Content -LiteralPath (Join-Path $output "AirGlove-$version-SHA256.txt") -Encoding ascii
        Get-Item -LiteralPath $artifacts
    } finally {
        $temporaryRoot = [IO.Path]::GetFullPath([IO.Path]::GetTempPath()).TrimEnd('\') + '\'
        $absoluteStage = (Resolve-Path -LiteralPath $stage).Path
        if (-not $absoluteStage.StartsWith($temporaryRoot, [StringComparison]::OrdinalIgnoreCase) -or
            -not ([IO.Path]::GetFileName($absoluteStage) -match '^airglove-package-[0-9a-f]{32}$')) {
            throw 'Unexpected staging path.'
        }
        Remove-Item -LiteralPath $absoluteStage -Recurse -Force
    }
} finally {
    Pop-Location
}
