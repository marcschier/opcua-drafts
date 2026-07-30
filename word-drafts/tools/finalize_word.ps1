<#
.SYNOPSIS
    Finalise a generated companion-specification document with Microsoft Word.

.DESCRIPTION
    The pure-Python build cannot paginate, so the table of contents, the table of
    figures, the table of tables and every PAGEREF have no correct cached value. This
    script drives Word to recalculate them, so the committed .docx opens fully
    paginated and needs no manual step.

    It also acts as the strongest available structural check: Word refuses to open a
    malformed package, and any unresolved cross-reference shows up as
    "Error! Reference source not found", which this script fails on.

    Requires Microsoft Word, so it is a local-only gate — like the repository's
    determinism check. The build itself stays pure Python and cross-platform.

    Every build un-finalises the document it writes, and `build_all.py` does it to the
    whole set, so this is not an optional polish step: run `finalize_all.ps1` after any
    build that will be committed.

.EXAMPLE
    pwsh word-drafts/tools/finalize_word.ps1 -Path word-drafts/OPC-UA-OpenUSD-Binding-Part1.docx
#>
[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [string]$Path,

    [switch]$Pdf,

    [switch]$KeepOpen
)

$ErrorActionPreference = 'Stop'

$full = (Resolve-Path -LiteralPath $Path).Path
Write-Host "Finalising $full"

$word = $null
$doc = $null
try {
    $word = New-Object -ComObject Word.Application
    $word.Visible = $false
    $word.DisplayAlerts = 0

    $doc = $word.Documents.Open($full, [ref]$false, [ref]$false)

    # This pass deliberately does not touch $doc.TrackRevisions. The build arms change
    # tracking by writing w:trackChanges into word/settings.xml, and Word preserves that
    # element across a save; but assigning the COM property *removes* it and assigning it
    # back does not restore it, so the document would ship with tracking silently off.
    # Word opens with tracking inactive, so the field updates below are never recorded —
    # which is what the revision count at the end verifies.

    # Fields first, then each table of contents twice: the first pass inserts the
    # entries, the second settles the page numbers once pagination has shifted.
    $doc.Fields.Update() | Out-Null
    foreach ($story in $doc.StoryRanges) {
        $story.Fields.Update() | Out-Null
    }
    for ($pass = 1; $pass -le 2; $pass++) {
        foreach ($toc in $doc.TablesOfContents) { $toc.Update() }
        foreach ($tof in $doc.TablesOfFigures) { $tof.Update() }
        $doc.Repaginate()
    }

    $text = $doc.Content.Text
    $broken = @()
    if ($text -match 'Error! Reference source not found') {
        $broken += 'unresolved cross-reference (REF field)'
    }
    if ($text -match 'Error! Bookmark not defined') {
        $broken += 'unresolved bookmark (PAGEREF field)'
    }
    if ($text -match 'Right-click and choose Update Field') {
        $broken += 'a table of contents did not update'
    }
    if ($doc.Revisions.Count -gt 0) {
        $broken += ("this pass recorded {0} tracked revision(s) of its own" -f $doc.Revisions.Count)
    }

    Write-Host ("pages: {0}, words: {1}, tables: {2}, fields: {3}" -f `
        $doc.ComputeStatistics(2), $doc.ComputeStatistics(0), $doc.Tables.Count, $doc.Fields.Count)

    $doc.Save()

    if ($Pdf) {
        $pdfPath = [System.IO.Path]::ChangeExtension($full, '.pdf')
        $doc.ExportAsFixedFormat($pdfPath, 17)
        Write-Host "exported $pdfPath"
    }

    if ($broken.Count -gt 0) {
        throw ("Document has unresolved references: {0}" -f ($broken -join '; '))
    }
    Write-Host 'OK - all fields resolved'
}
finally {
    if ($null -ne $doc -and -not $KeepOpen) { $doc.Close([ref]$true) | Out-Null }
    if ($null -ne $word -and -not $KeepOpen) { $word.Quit() | Out-Null }
    if ($null -ne $doc) { [void][Runtime.InteropServices.Marshal]::ReleaseComObject($doc) }
    if ($null -ne $word) { [void][Runtime.InteropServices.Marshal]::ReleaseComObject($word) }
    [GC]::Collect()
    [GC]::WaitForPendingFinalizers()
}

# Word rewrites word/settings.xml from its own state and drops the change-tracking element
# the build wrote, so tracking is re-armed here, after Word has closed the file. Doing it
# through the COM property does not work: setting it False removes the element and setting
# it back True does not restore it.
if (-not $KeepOpen) {
    $tools = Split-Path -Parent $PSCommandPath
    python (Join-Path $tools 'arm_track_changes.py') $full
    if ($LASTEXITCODE -ne 0) { throw 'could not re-arm change tracking' }
}
