#Requires -Version 7.4
<#
.SYNOPSIS
    Runs the media-over-data-channels demo.
.DESCRIPTION
    Builds and runs the experimental ConsoleDataChannelStreaming sample from the
    data-channels-quic-experimental branch. It exercises a real Session and
    OpenDataChannel over inline TCP framing, then repeats the same application
    stream over the opc.quic binding when QUIC is available.
.PARAMETER StackRoot
    Path to a UA-.NETStandard checkout on data-channels-quic-experimental. If omitted, the shared
    demo module locates a checkout that contains the required marker paths.
.PARAMETER NoBuild
    Skip building the referenced project before running.
.PARAMETER KeepRunning
    Leave started processes running when the script exits.
.EXAMPLE
    .\run-demo.ps1 -StackRoot C:\src\ua-datachannels
#>
[CmdletBinding()]
param(
    [string] $StackRoot,
    [switch] $NoBuild,
    [switch] $KeepRunning
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

Import-Module (Join-Path $PSScriptRoot '..\_shared\Demo.psm1') -Force

try {
    Write-DemoBanner `
        -Title 'Demo 8 — Media over Data Channels' `
        -Shows 'Media-like bytes on the OPC UA SecureChannel that is already open'

    $requiredPaths = @(
        'samples\ConsoleDataChannelStreaming\ConsoleDataChannelStreaming.csproj',
        'src\Opc.Ua.Core\Stack\DataChannels\DataChannel.cs',
        'src\Opc.Ua.Bindings.Quic\Opc.Ua.Bindings.Quic.csproj',
        'docs\DataChannels.md'
    )
    $root = Resolve-StackRoot -StackRoot $StackRoot -RequiredPaths @($requiredPaths[0])
    Assert-StackBranch -StackRoot $root -Branch 'data-channels-quic-experimental' -RequiredPaths $requiredPaths
    Assert-DotNetSdk

    $sample = Join-Path $root 'samples\ConsoleDataChannelStreaming\ConsoleDataChannelStreaming.csproj'

    Write-DemoStep -Message 'Build the streaming sample' `
        -Detail 'The worked sample opens a real Session and calls OpenDataChannel.'
    Invoke-DemoBuild -Projects @($sample) -NoBuild:$NoBuild
    Wait-DemoKeypress

    Write-DemoStep -Message 'Run the server-mode TCP stream' `
        -Detail 'Inline STR chunks share the same SecureChannel as ordinary Service traffic.'
    & dotnet run --project $sample -c Release -f net10.0 --no-build --nologo -- `
        --transport tcp --mode server --frames 600 --size 1200
    if ($LASTEXITCODE -ne 0) {
        throw "TCP data channel run failed with exit code $LASTEXITCODE."
    }
    Wait-DemoKeypress

    Write-DemoStep -Message 'Run the server-mode QUIC stream' `
        -Detail 'The same application stream uses the experimental opc.quic binding when available.'
    & dotnet run --project $sample -c Release -f net10.0 --no-build --nologo -- `
        --transport quic --mode server --frames 600 --size 1200
    if ($LASTEXITCODE -eq 2) {
        Write-DemoNote 'QUIC is unavailable on this machine; present the TCP leg and docs\DataChannels.md.'
    }
    elseif ($LASTEXITCODE -ne 0) {
        throw "QUIC data channel run failed with exit code $LASTEXITCODE."
    }
    Wait-DemoKeypress

    Write-DemoStep -Message 'Run the benchmark with competing Publish load' `
        -Detail 'A short TCP matrix shows whether streaming starves ordinary Subscription traffic.'
    & dotnet run --project $sample -c Release -f net10.0 --no-build --nologo -- `
        --transport tcp --mode benchmark --frames 12000 --size 1200 --monitored-items 50 --repeat 2
    if ($LASTEXITCODE -ne 0) {
        throw "Benchmark run failed with exit code $LASTEXITCODE."
    }
    Wait-DemoKeypress

    Write-DemoStep -Message 'Read the result counters' `
        -Detail 'Use channel id, revised credit, discarded frames and credit stalls as the proof points.'
    Write-DemoNote 'Credit stalls are not a failure; they are the mechanism that protects Service traffic.'
    Write-DemoNote 'Over opc.quic, the transport channel id identifies the QUIC stream used for the data channel.'
    Wait-DemoKeypress
}
finally {
    if (-not $KeepRunning) {
        Stop-DemoProcesses
    }
}

