#!/usr/bin/env pwsh
# Build a PPTX from every Marp deck in this folder.
#
# A "Marp deck" is any *.md file whose YAML front matter contains `marp: true`.
# Marp does not render Mermaid diagrams when exporting to PPTX, so for each deck
# this script pre-renders every fenced ```mermaid block to a PNG (via the Mermaid
# CLI) and substitutes an image reference into a temporary build copy before
# running marp-cli. The committed Markdown decks are never modified.
#
# A small build-only stylesheet caps the diagram size and trims the font so the
# diagrams and text fit on a slide regardless of the deck's theme.
#
# Requires Node.js on PATH (uses `npx` to fetch @mermaid-js/mermaid-cli and
# @marp-team/marp-cli on demand). Run from anywhere:
#   pwsh core-specs/presentations/build-pptx.ps1
$ErrorActionPreference = "Stop"

$here = if ($PSScriptRoot) { $PSScriptRoot } else { Split-Path -Parent $MyInvocation.MyCommand.Path }
$repo = (Resolve-Path (Join-Path $here "..\..")).Path
$pconf = Join-Path $repo ".github\puppeteer-config.json"
$pconfArgs = if (Test-Path $pconf) { @("-p", $pconf) } else { @() }

# Build-only styling (injected into the temporary copy only): shrink the body
# font a touch and cap image size so a diagram plus its text fits on one slide.
$style = @"
<style>
section { font-size: 24px; }
img { display: block; margin: 0.3em auto; max-height: 290px; max-width: 900px; }
</style>
"@

$mermaidRx = [regex]'(?s)```mermaid\r?\n(.*?)\r?\n```'
$frontMatterRx = [regex]'(?s)^(---\r?\n.*?\r?\n---\r?\n)'

$decks = Get-ChildItem -Path $here -Filter *.md | Where-Object {
    (Get-Content -Raw $_.FullName) -match '(?m)^marp:\s*true\s*$'
} | Sort-Object Name
Write-Host "Found $($decks.Count) Marp deck(s) in $here"

foreach ($deck in $decks) {
    $stem = [System.IO.Path]::GetFileNameWithoutExtension($deck.Name)
    Write-Host "=== $($deck.Name) ==="
    $work = Join-Path ([System.IO.Path]::GetTempPath()) "deckbuild_$stem"
    if (Test-Path $work) { Remove-Item -Recurse -Force $work }
    New-Item -ItemType Directory -Force -Path $work | Out-Null

    $text = Get-Content -Raw $deck.FullName
    $ms = $mermaidRx.Matches($text)
    $new = $text
    for ($i = 0; $i -lt $ms.Count; $i++) {
        $mmd = Join-Path $work "diagram$($i + 1).mmd"
        $png = Join-Path $work "diagram$($i + 1).png"
        Set-Content -Encoding utf8 $mmd $ms[$i].Groups[1].Value
        npx --yes @mermaid-js/mermaid-cli -i $mmd -o $png -b white -s 2 @pconfArgs *> "$work\mmdc$($i + 1).log"
        if (-not (Test-Path $png)) { Get-Content "$work\mmdc$($i + 1).log" | Select-Object -Last 12; throw "Mermaid render failed in $($deck.Name) block $($i + 1)" }
        $new = $new.Replace($ms[$i].Value, "![]($(($png).Replace('\', '/')))")
    }

    # Inject the build-only stylesheet immediately after the front matter.
    $new = $frontMatterRx.Replace($new, [System.Text.RegularExpressions.MatchEvaluator] { param($m) $m.Groups[1].Value + "`n" + $style + "`n" }, 1)

    $build = Join-Path $work "build.md"
    Set-Content -Encoding utf8 $build $new
    $pptx = Join-Path $here "$stem.pptx"
    npx --yes @marp-team/marp-cli $build --pptx --allow-local-files -o $pptx *> "$work\marp.log"
    if (-not (Test-Path $pptx)) { Get-Content "$work\marp.log" | Select-Object -Last 12; throw "marp PPTX export failed for $($deck.Name)" }
    Write-Host ("  -> {0} ({1:n0} bytes, {2} diagram(s))" -f "$stem.pptx", (Get-Item $pptx).Length, $ms.Count)
}
Write-Host "Done."
