<#
.SYNOPSIS
    Export slides from the generated deck to PNG using PowerPoint.

.DESCRIPTION
    check_layout.py verifies deck geometry from the OOXML, which cannot show how
    PowerPoint actually routes an elbow connector. This exports real renderings so
    a diagram can be looked at.

.PARAMETER Deck
    The .pptx to export. Defaults to the generated overview deck.

.PARAMETER Slides
    Slide numbers to export. Defaults to every slide.

.PARAMETER OutputDirectory
    Where the PNG files are written.

.EXAMPLE
    .\export_slides.ps1 -Slides 4,31,39
#>
[CmdletBinding()]
param(
    [string] $Deck = (Join-Path $PSScriptRoot 'OPC-UA-Drafts-Overview.pptx'),
    [int[]] $Slides,
    [string] $OutputDirectory = (Join-Path $env:TEMP 'deck-render')
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$deckPath = (Resolve-Path $Deck).Path
New-Item -ItemType Directory -Path $OutputDirectory -Force | Out-Null

$powerpoint = New-Object -ComObject PowerPoint.Application
try {
    $presentation = $powerpoint.Presentations.Open($deckPath, $true, $false, $false)
    try {
        $targets = if ($Slides) { $Slides } else { 1..$presentation.Slides.Count }
        foreach ($number in $targets) {
            $slide = $presentation.Slides.Item($number)
            $file = Join-Path $OutputDirectory ("slide{0:D3}.png" -f $number)
            $slide.Export($file, 'PNG', 1600, 900)
            Write-Output $file
        }
    }
    finally {
        $presentation.Close()
    }
}
finally {
    $powerpoint.Quit()
    [void][Runtime.InteropServices.Marshal]::ReleaseComObject($powerpoint)
}
