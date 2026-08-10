#Requires -Version 7.4
<#
.SYNOPSIS
    Runs the robot positioning and OpenUSD viewer demo.
.DESCRIPTION
    Starts MinimalRobotServer, which composes OPC 40010 Robotics, OPC 10000-210 RSL,
    OPC 10000-211 GPOS, and OpenUSD bindings in one server, then opens the generic
    OpenUSD connector viewer against the live robot cell.
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
        -Title 'Robot with GPOS/RSL and USD' `
        -Shows 'Robotics, RSL frames, GPOS locations, and a live OpenUSD stage'

    $root = Resolve-StackRoot -StackRoot $StackRoot -RequiredPaths @(
        'samples\Robotics\MinimalRobotServer\MinimalRobotServer.csproj'
    )
    Assert-DotNetSdk
    Assert-StackBranch -StackRoot $root -Branch 'master' -RequiredPaths @(
        'src\Opc.Ua.Positioning\Opc.Ua.Positioning.csproj',
        'src\Opc.Ua.OpenUsd\Opc.Ua.OpenUsd.csproj',
        'tools\Opc.Ua.OpenUsd.Connector.Viewer\Opc.Ua.OpenUsd.Connector.Viewer.csproj'
    )

    $serverProject = Join-Path $root 'samples\Robotics\MinimalRobotServer\MinimalRobotServer.csproj'
    $connectorProject = Join-Path $root 'tools\Opc.Ua.OpenUsd.Connector\Opc.Ua.OpenUsd.Connector.csproj'
    $viewerProject = Join-Path $root 'tools\Opc.Ua.OpenUsd.Connector.Viewer\Opc.Ua.OpenUsd.Connector.Viewer.csproj'

    Write-DemoStep -Message 'Build the robot server and OpenUSD viewer' `
        -Detail 'Only the projects this walkthrough starts are built.'
    Invoke-DemoBuild -Projects @($serverProject, $connectorProject, $viewerProject) -NoBuild:$NoBuild
    Wait-DemoKeypress

    Write-DemoStep -Message 'Start the robot cell server' `
        -Detail 'The server publishes two mobile six-axis robots at opc.tcp://localhost:62830/MinimalRobotServer.'
    Start-DemoProcess -Name 'MinimalRobotServer' -Project $serverProject -Arguments @(
        '--host', 'localhost', '--port', '62830'
    ) | Out-Null
    Wait-DemoEndpoint -HostName 'localhost' -Port 62830
    Wait-DemoKeypress

    Write-DemoStep -Message 'Open the generic OpenUSD viewer' `
        -Detail 'The connector discovers Server/OpenUSD/Representations and fetches the served stage.'
    Start-DemoProcess -Name 'OpenUSD connector viewer' -Project $connectorProject -Arguments @(
        '--server', 'opc.tcp://localhost:62830/MinimalRobotServer',
        '--insecure', '--view'
    ) | Out-Null
    Write-DemoNote 'Look for two robots moving through the cell, with joints and platforms updating live.'
    Wait-DemoKeypress

    Write-DemoStep -Message 'Point out the positioning model in the live twin' `
        -Detail 'RSL drives relative frames; GPOS drives global longitude, latitude, and elevation attributes.'
    Write-DemoNote 'Say: one Robotics node manager composes Robotics, RSL, GPOS, and OpenUSD; the viewer has no robot-specific bridge.'
    Wait-DemoKeypress
}
finally {
    if (-not $KeepRunning) { Stop-DemoProcesses }
}
