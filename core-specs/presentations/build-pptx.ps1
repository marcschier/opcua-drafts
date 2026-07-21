#!/usr/bin/env pwsh
# Build OPC-UA-Encoding-and-Registry-Overview.pptx from the Marp deck.
#
# Marp does not render Mermaid diagrams when exporting to PPTX, so this script
# pre-renders each fenced ```mermaid block to a PNG (via the Mermaid CLI) and
# substitutes an image reference into a temporary build copy of the deck before
# running marp-cli. The committed Markdown deck is never modified.
#
# Requires Node.js on PATH (uses `npx` to fetch @mermaid-js/mermaid-cli and
# @marp-team/marp-cli on demand). Run from anywhere:
#   pwsh core-specs/presentations/build-pptx.ps1
param([string[]]$Sizes = @("w:660", "h:280", "h:290", "h:280"))
$ErrorActionPreference = "Stop"

$here = if ($PSScriptRoot) { $PSScriptRoot } else { Split-Path -Parent $MyInvocation.MyCommand.Path }
$repo = (Resolve-Path (Join-Path $here "..\..")).Path
$deck = Join-Path $here "OPC-UA-Encoding-and-Registry-Overview.md"
$pconf = Join-Path $repo ".github\puppeteer-config.json"
$work = Join-Path ([System.IO.Path]::GetTempPath()) "deckbuild"
if (Test-Path $work) { Remove-Item -Recurse -Force $work }
New-Item -ItemType Directory -Force -Path $work | Out-Null

$text = Get-Content -Raw $deck
$rx = [regex]'(?s)```mermaid\r?\n(.*?)\r?\n```'
$ms = $rx.Matches($text)
Write-Host "Rendering $($ms.Count) Mermaid diagram(s)..."
$new = $text
for ($i = 0; $i -lt $ms.Count; $i++) {
    $mmd = Join-Path $work "diagram$($i + 1).mmd"
    $png = Join-Path $work "diagram$($i + 1).png"
    Set-Content -Encoding utf8 $mmd $ms[$i].Groups[1].Value
    npx --yes @mermaid-js/mermaid-cli -i $mmd -o $png -b white -s 2 -p $pconf *> "$work\mmdc$($i + 1).log"
    if (-not (Test-Path $png)) { Get-Content "$work\mmdc$($i + 1).log" | Select-Object -Last 12; throw "Mermaid render failed for block $($i + 1)" }
    $new = $new.Replace($ms[$i].Value, "![$($Sizes[$i])]($(($png).Replace('\', '/')))")
}

# Build-only styling so the diagrams + text fit on the gaia slides. Injected into
# the temporary copy only; the committed deck is left untouched.
$style = "marp: true`nstyle: |`n  section { font-size: 26px; }`n  section h1 { font-size: 46px; }`n  img { display: block; margin: 0.25em auto; }"
$new = $new.Replace("marp: true", $style)

$build = Join-Path $work "build.md"
Set-Content -Encoding utf8 $build $new
$pptx = Join-Path $here "OPC-UA-Encoding-and-Registry-Overview.pptx"
npx --yes @marp-team/marp-cli $build --pptx --allow-local-files -o $pptx
if (-not (Test-Path $pptx)) { throw "marp PPTX export failed" }
Write-Host ("Wrote {0} ({1:n0} bytes)" -f $pptx, (Get-Item $pptx).Length)
