#Requires -Version 7.4
<#
.SYNOPSIS
    Runs the server redundancy demo.
.DESCRIPTION
    Starts a three-replica strong-consistency RedundantServer set and a RedundantClient, then stops the
    first replica mid-subscription so the presenter can watch transparent failover and data-loss logs.
.PARAMETER StackRoot
    Path to the UA-.NETStandard checkout. If omitted, the shared demo module locates it.
.PARAMETER NoBuild
    Skip building the referenced projects before running.
.PARAMETER KeepRunning
    Leave started processes running when the script exits.
.EXAMPLE
    .\run-demo.ps1
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

$environmentNames = @(
    'HA_NODE_ID',
    'HA_MODE',
    'REDUNDANCY_MODE',
    'HA_CONSISTENCY',
    'HA_RAFT_ID',
    'HA_RAFT_MEMBERS',
    'HA_RAFT_BIND',
    'HA_RAFT_PEERS',
    'HA_INSECURE',
    'HA_REDUNDANT_PEERS'
)
$savedEnvironment = @{}
foreach ($name in $environmentNames) {
    $savedEnvironment[$name] = [Environment]::GetEnvironmentVariable($name, 'Process')
}

try {
    Write-DemoBanner `
        -Title 'Demo 6 - server redundancy' `
        -Shows 'A client subscription surviving a server replica failure'

    $root = Resolve-StackRoot -StackRoot $StackRoot -RequiredPaths @('samples\RedundantServer\RedundantServer.csproj')
    Assert-DotNetSdk
    Assert-StackBranch -StackRoot $root -Branch 'master' `
        -RequiredPaths @('samples\RedundantServer\RedundantServer.csproj')

    $server = Join-Path $root 'samples\RedundantServer\RedundantServer.csproj'
    $client = Join-Path $root 'samples\RedundantClient\RedundantClient.csproj'

    Write-DemoStep -Message 'Build the redundant server and managed client' `
        -Detail 'The server publishes redundancy metadata; the client opts into WithServerRedundancy().'
    Invoke-DemoBuild -Projects @($server, $client) -NoBuild:$NoBuild
    Wait-DemoKeypress

    Write-DemoStep -Message 'Start three strong-consistency server replicas' `
        -Detail 'Raft backs the shared store; HA_INSECURE is set only for this isolated localhost demo.'
    $env:HA_MODE = 'ap'
    $env:REDUNDANCY_MODE = 'hot'
    $env:HA_CONSISTENCY = 'strong'
    $env:HA_RAFT_MEMBERS = '3'
    $env:HA_INSECURE = 'true'

    $env:HA_NODE_ID = 'replica-a'
    $env:HA_RAFT_ID = '1'
    $env:HA_RAFT_BIND = 'tcp://127.0.0.1:6560'
    $env:HA_RAFT_PEERS = 'tcp://127.0.0.1:6561,tcp://127.0.0.1:6562'
    $env:HA_REDUNDANT_PEERS = 'urn:localhost:OPCFoundation:RedundantServer:replica-b|RedundantServer replica-b|opc.tcp://localhost:62544/RedundantServer;urn:localhost:OPCFoundation:RedundantServer:replica-c|RedundantServer replica-c|opc.tcp://localhost:62545/RedundantServer'
    $serverA = Start-DemoProcess -Name 'RedundantServer replica-a' -Project $server -Arguments @('--port', '62543')

    $env:HA_NODE_ID = 'replica-b'
    $env:HA_RAFT_ID = '2'
    $env:HA_RAFT_BIND = 'tcp://127.0.0.1:6561'
    $env:HA_RAFT_PEERS = 'tcp://127.0.0.1:6560,tcp://127.0.0.1:6562'
    $env:HA_REDUNDANT_PEERS = 'urn:localhost:OPCFoundation:RedundantServer:replica-a|RedundantServer replica-a|opc.tcp://localhost:62543/RedundantServer;urn:localhost:OPCFoundation:RedundantServer:replica-c|RedundantServer replica-c|opc.tcp://localhost:62545/RedundantServer'
    $null = Start-DemoProcess -Name 'RedundantServer replica-b' -Project $server -Arguments @('--port', '62544')

    $env:HA_NODE_ID = 'replica-c'
    $env:HA_RAFT_ID = '3'
    $env:HA_RAFT_BIND = 'tcp://127.0.0.1:6562'
    $env:HA_RAFT_PEERS = 'tcp://127.0.0.1:6560,tcp://127.0.0.1:6561'
    $env:HA_REDUNDANT_PEERS = 'urn:localhost:OPCFoundation:RedundantServer:replica-a|RedundantServer replica-a|opc.tcp://localhost:62543/RedundantServer;urn:localhost:OPCFoundation:RedundantServer:replica-b|RedundantServer replica-b|opc.tcp://localhost:62544/RedundantServer'
    $null = Start-DemoProcess -Name 'RedundantServer replica-c' -Project $server -Arguments @('--port', '62545')

    Wait-DemoEndpoint -HostName 'localhost' -Port 62543
    Wait-DemoEndpoint -HostName 'localhost' -Port 62544
    Wait-DemoEndpoint -HostName 'localhost' -Port 62545
    Wait-DemoKeypress

    Write-DemoStep -Message 'Start the managed redundant client' `
        -Detail 'It subscribes to ServerStatus.CurrentTime and HighAvailability.Counter.'
    $null = Start-DemoProcess -Name 'RedundantClient' -Project $client `
        -Arguments @('--server', 'opc.tcp://localhost:62543/RedundantServer', '--autoaccept', '--nosecurity', '--duration', '00:00:00')
    Wait-DemoKeypress

    Write-DemoStep -Message 'Kill the active replica mid-subscription' `
        -Detail 'The client should log reconnect or failover and keep monitoring.'
    Write-DemoNote "Stopping replica-a by process id $($serverA.Id)."
    Stop-Process -Id $serverA.Id -ErrorAction SilentlyContinue
    Wait-DemoKeypress

    Write-DemoStep -Message 'Read the client log lines' `
        -Detail 'Look for FAILOVER, CONNECTED, DATA LOSS or HA OK lines.'
    Write-DemoNote 'This is the cost hidden behind drafts that assume a highly available Server.'
    Wait-DemoKeypress
}
finally {
    foreach ($name in $environmentNames) {
        [Environment]::SetEnvironmentVariable($name, $savedEnvironment[$name], 'Process')
    }
    if (-not $KeepRunning) {
        Stop-DemoProcesses
    }
}
