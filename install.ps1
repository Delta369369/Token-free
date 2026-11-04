<#
.SYNOPSIS
  Opt-in local installer for ADON Context Efficiency skill. No remote calls, no hooks or agent configs modified.
.EXAMPLE
  .\install.ps1 -Claude
.EXAMPLE
  .\install.ps1 -Codex
.EXAMPLE
  .\install.ps1 -Claude -Codex
#>
[CmdletBinding()]
param([switch]$Claude, [switch]$Codex, [switch]$Force)
$ErrorActionPreference = 'Stop'
if (-not $Claude -and -not $Codex) {
  throw 'Specify -Claude and/or -Codex. This installer will not modify anything without an explicit target.'
}
$origin = (Resolve-Path $PSScriptRoot).Path
$targets = @()
if ($Claude) { $targets += (Join-Path $HOME '.claude\skills\adon-context-efficiency') }
if ($Codex)  { $targets += (Join-Path $HOME '.agents\skills\adon-context-efficiency') }
foreach ($target in $targets) {
  if (Test-Path $target) {
    if (-not $Force) { throw "Destination exists: $target. Stop or pass -Force after backing up existing content." }
    # Keep backups outside the agent's skills scan root; otherwise backup SKILL.md
    # files may be loaded as duplicate or invalid skills by Claude Code or Codex.
    $agentHome = Split-Path -Parent (Split-Path -Parent $target)
    $backupRoot = Join-Path $agentHome 'skill-backups\adon-context-efficiency'
    New-Item -ItemType Directory -Path $backupRoot -Force | Out-Null
    $backup = Join-Path $backupRoot "adon-context-efficiency.backup.$(Get-Date -Format yyyyMMddHHmmss)"
    Copy-Item -LiteralPath $target -Destination $backup -Recurse -Force
    Remove-Item -LiteralPath $target -Recurse -Force
    Write-Host "Existing skill backed up: $backup"
  }
  New-Item -ItemType Directory -Path $target -Force | Out-Null
  Copy-Item -LiteralPath (Join-Path $origin 'SKILL.md') -Destination $target
  Copy-Item -LiteralPath (Join-Path $origin 'README.md') -Destination $target
  Copy-Item -LiteralPath (Join-Path $origin 'adon_context') -Destination $target -Recurse
  Copy-Item -LiteralPath (Join-Path $origin 'references') -Destination $target -Recurse
  Copy-Item -LiteralPath (Join-Path $origin 'examples') -Destination $target -Recurse
  Write-Host "Installed local skill: $target"
}
Write-Host 'No account sign-in, external traffic, hooks, config changes or SQLite imports were performed.'
Write-Host 'Open the installed skill folder and run: py -3 -m adon_context --help'
