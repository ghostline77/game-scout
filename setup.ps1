param(
    [string]$GameRoot = $env:CYBERPUNK_GAME_ROOT,
    [string]$Python = 'python',
    [switch]$Development,
    [switch]$InstallMod,
    [switch]$RegisterCodex
)
$ErrorActionPreference = 'Stop'
if ($InstallMod -and -not $GameRoot) { throw 'Set -GameRoot or CYBERPUNK_GAME_ROOT to the game installation.' }
$environmentPath = Join-Path $PSScriptRoot '.venv'
$toolPython = Join-Path $environmentPath 'Scripts\python.exe'
if (-not (Test-Path -LiteralPath $toolPython)) {
    & $Python -m venv $environmentPath
    if ($LASTEXITCODE -ne 0) { throw 'Environment creation failed.' }
}
$packageSpec = $PSScriptRoot
if ($Development) { $packageSpec = "${PSScriptRoot}[test]" }
& $toolPython -m pip install -e $packageSpec
if ($LASTEXITCODE -ne 0) { throw 'Dependency installation failed.' }
$entry = Join-Path $PSScriptRoot 'game_scout_mcp.py'
$config = Join-Path $PSScriptRoot '.local\game-scout.json'
if ($InstallMod) {
    & $toolPython $entry --config $config install --game-root $GameRoot
    if ($LASTEXITCODE -ne 0) { throw 'CET mod installation failed.' }
}
if ($RegisterCodex) {
    if (-not (Test-Path -LiteralPath $config)) { throw 'Install the mod or supply local configuration before registration.' }
    & codex mcp add game_scout -- $toolPython $entry --config $config serve
    if ($LASTEXITCODE -ne 0) { throw 'Codex MCP registration failed.' }
}
Write-Host 'Environment ready. Use -InstallMod to update CET when idle and -RegisterCodex to switch the MCP entry.'
