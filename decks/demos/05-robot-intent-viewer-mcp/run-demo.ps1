#Requires -Version 7.4
<#
.SYNOPSIS
    Runs the Robot Intent viewer plus MCP demo.
.DESCRIPTION
    Starts the Robot Intent server, the viewer client, and the OPC UA MCP server so the presenter can
    show the same controller observed in a live viewer and driven from MCP tools.
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

try {
    Write-DemoBanner `
        -Title 'Demo 5 - robot intent viewer plus MCP' `
        -Shows 'A task-level Robot Intent controller observed live and driven through MCP'

    $root = Resolve-StackRoot -StackRoot $StackRoot `
        -RequiredPaths @('samples\Robotics\IntentEnabledRobot\IntentEnabledRobot.csproj')
    Assert-DotNetSdk
    Assert-StackBranch -StackRoot $root -Branch 'master' `
        -RequiredPaths @('samples\Robotics\IntentEnabledRobot\IntentEnabledRobot.csproj')

    $server = Join-Path $root 'samples\Robotics\IntentEnabledRobot\IntentEnabledRobot.csproj'
    $viewer = Join-Path $root 'samples\Robotics\IntentViewerClient\IntentViewerClient.csproj'
    $mcpServer = Join-Path $root 'tools\Opc.Ua.Mcp\Opc.Ua.Mcp.csproj'

    Write-DemoStep -Message 'Build the robot server, viewer client and MCP server' `
        -Detail 'The server publishes Robot Intent and OpenUSD; the client watches and commands it.'
    Invoke-DemoBuild -Projects @($server, $viewer, $mcpServer) -NoBuild:$NoBuild
    Wait-DemoKeypress

    Write-DemoStep -Message 'Start the IntentEnabledRobot server' `
        -Detail 'The endpoint is opc.tcp://localhost:62840/IntentEnabledRobot.'
    $null = Start-DemoProcess -Name 'IntentEnabledRobot' -Project $server -Arguments @('--host', 'localhost', '--port', '62840')
    Wait-DemoEndpoint -HostName 'localhost' -Port 62840
    Wait-DemoKeypress

    Write-DemoStep -Message 'Start the viewer client in headless mode' `
        -Detail 'It discovers the controller, prints facets, takes authority and offers target pucks.'
    $null = Start-DemoProcess -Name 'Intent Viewer Client' -Project $viewer `
        -Arguments @('--server', 'opc.tcp://localhost:62840/IntentEnabledRobot', '--insecure', '--seconds', '600')
    Wait-DemoKeypress

    Write-DemoStep -Message 'Start the MCP server for the same endpoint' `
        -Detail 'Use the services profile at http://localhost:5100/mcp.'
    $null = Start-DemoProcess -Name 'OPC UA MCP Server' -Project $mcpServer `
        -Arguments @('--transport', 'http', '--port', '5100', '--profile', 'services')
    Wait-DemoEndpoint -HostName 'localhost' -Port 5100
    Wait-DemoKeypress

    Write-DemoStep -Message 'Drive a task intent from MCP' `
        -Detail 'Connect, browse Server/RobotIntent/Controllers, request control and call SubmitIntent.'
    Write-DemoNote 'Endpoint: opc.tcp://localhost:62840/IntentEnabledRobot; use autoAcceptCerts=true.'
    Write-DemoNote 'The same Part 10 operation the viewer tracks is created by the MCP Call tool.'
    Wait-DemoKeypress

    Write-DemoStep -Message 'Watch the lifecycle and talk through refusal rules' `
        -Detail 'The viewer reports Accepted, Queued or Executing, then Succeeded, Failed or Cancelled.'
    Write-DemoNote 'Use the server console commands stop, limit 0.05 and reset to show safety refusals.'
    Wait-DemoKeypress
}
finally {
    if (-not $KeepRunning) {
        Stop-DemoProcesses
    }
}
