<#
.SYNOPSIS
    Finalise every converted specification with Microsoft Word.

.DESCRIPTION
    `build_docx.py` writes fields, not field results, so a freshly built document opens
    with an empty table of contents and blank cross-references. `build_all.py` rebuilds
    the whole batch, which means it un-finalises every document each time it runs — so
    "build, then finalise" is the normal order, not an exception.

    This script reads the converted list from `specs/batch.json` and runs
    `finalize_word.ps1` over each one, then re-validates with `--finalized` so a document
    that silently failed to finalise cannot be committed.

.EXAMPLE
    pwsh word-drafts/tools/finalize_all.ps1

.EXAMPLE
    pwsh word-drafts/tools/finalize_all.ps1 -VerifyOnly
#>
[CmdletBinding()]
param(
    # Check the committed documents without opening Word.
    [switch]$VerifyOnly
)

$ErrorActionPreference = 'Stop'

$tools = $PSScriptRoot
$repo = Split-Path -Parent (Split-Path -Parent $tools)
$batch = Get-Content (Join-Path $tools 'specs\batch.json') -Raw | ConvertFrom-Json

$env:PYTHONIOENCODING = 'utf-8'
$failed = @()

foreach ($entry in $batch.converted) {
    $config = Join-Path $tools "specs\$entry.json"
    $cfg = Get-Content $config -Raw | ConvertFrom-Json
    $docx = Join-Path $repo $cfg.output.docx

    if (-not $VerifyOnly) {
        & (Join-Path $tools 'finalize_word.ps1') -Path $docx
    }

    & python (Join-Path $tools 'validate_docx.py') $config --finalized | Out-Null
    if ($LASTEXITCODE -ne 0) {
        $failed += $entry
        Write-Host "FAIL  $entry" -ForegroundColor Red
    }
    else {
        Write-Host "ok    $entry" -ForegroundColor Green
    }
}

if ($failed.Count) {
    Write-Error "$($failed.Count) document(s) are not finalised: $($failed -join ', ')"
    exit 1
}

Write-Host "$($batch.converted.Count) document(s) finalised and validated"
