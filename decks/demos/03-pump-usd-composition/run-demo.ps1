#Requires -Version 7.4
<#
.SYNOPSIS
    Runs the pump OpenUSD composition demo.
.DESCRIPTION
    Starts a PumpDeviceIntegrationServer with several simulated pumps, starts the
    SiteCompositionServer that declares the pump server as a cross-server component,
    and opens the generic OpenUSD connector viewer with federation enabled.
.PARAMETER StackRoot
    Path to the UA-.NETStandard checkout. When omitted, the shared demo module
    searches OPCUA_STACK_ROOT and sibling checkouts.
.PARAMETER NoBuild
    Skip building the projects before running them.
.PARAMETER KeepRunning
    Leave started demo processes running when the script exits.
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

try {
    Write-DemoBanner `
        -Title 'Pump USD and composition' `
        -Shows 'DI pumps, OpenUSD bindings, and cross-server USD composition'

    $root = Resolve-StackRoot -StackRoot $StackRoot -RequiredPaths @(
        'samples\SiteCompositionServer\SiteCompositionServer.csproj'
    )
    Assert-DotNetSdk
    Assert-StackBranch -StackRoot $root -Branch 'master' -RequiredPaths @(
        'samples\PumpDeviceIntegrationServer\PumpDeviceIntegrationServer.csproj',
        'tools\Opc.Ua.OpenUsd.Connector\Opc.Ua.OpenUsd.Connector.csproj'
    )

    $pumpProject = Join-Path $root 'samples\PumpDeviceIntegrationServer\PumpDeviceIntegrationServer.csproj'
    $siteProject = Join-Path $root 'samples\SiteCompositionServer\SiteCompositionServer.csproj'
    $connectorProject = Join-Path $root 'tools\Opc.Ua.OpenUsd.Connector\Opc.Ua.OpenUsd.Connector.csproj'
    $viewerProject = Join-Path $root 'tools\Opc.Ua.OpenUsd.Connector.Viewer\Opc.Ua.OpenUsd.Connector.Viewer.csproj'

    Write-DemoStep -Message 'Build the pump, site, and OpenUSD projects' `
        -Detail 'The site server owns the stage shell; the pump server owns the machines.'
    Invoke-DemoBuild -Projects @($pumpProject, $siteProject, $connectorProject, $viewerProject) -NoBuild:$NoBuild
    Wait-DemoKeypress

    Write-DemoStep -Message 'Start the DI pump server' `
        -Detail 'Three PumpType instances publish their own OpenUSD representations.'
    Start-DemoProcess -Name 'PumpDeviceIntegrationServer' -Project $pumpProject -Arguments @(
        '--host', 'localhost', '--port', '62542', '--pumps', '3'
    ) | Out-Null
    Wait-DemoEndpoint -HostName 'localhost' -Port 62542
    Wait-DemoKeypress

    Write-DemoStep -Message 'Start the site composition server' `
        -Detail 'It owns no pumps; it names the pump server as the owner of the Pump Hall component.'
    Start-DemoProcess -Name 'SiteCompositionServer' -Project $siteProject -Arguments @(
        '--host', 'localhost', '--port', '62544',
        '--pump-server', 'opc.tcp://localhost:62542/PumpDeviceIntegrationServer',
        '--generator-server', ''
    ) | Out-Null
    Wait-DemoEndpoint -HostName 'localhost' -Port 62544
    Wait-DemoKeypress

    Write-DemoStep -Message 'Render the federated site stage' `
        -Detail 'The connector opens the site, follows the component endpoint, and composes the pumps.'
    Start-DemoProcess -Name 'OpenUSD federated viewer' -Project $connectorProject -Arguments @(
        '--server', 'opc.tcp://localhost:62544/SiteCompositionServer',
        '--insecure', '--federate', '--view'
    ) | Out-Null
    Write-DemoNote 'Look for a site shell with several live pump machines, assembled through USD composition.'
    Wait-DemoKeypress
}
finally {
    if (-not $KeepRunning) { Stop-DemoProcesses }
}
