#Requires -Version 7.4
<#
.SYNOPSIS
    Runs the OPC UA MCP server demo.
.DESCRIPTION
    Starts the reference OPC UA Server and the OPC UA MCP server over Streamable HTTP, then walks
    through the MCP tool calls that let a model browse, read, write, subscribe and call methods.
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
        -Title 'Demo 1 - OPC UA MCP server' `
        -Shows 'An OPC UA address space driven through Model Context Protocol tools'

    $root = Resolve-StackRoot -StackRoot $StackRoot -RequiredPaths @('tools\Opc.Ua.Mcp\Opc.Ua.Mcp.csproj')
    Assert-DotNetSdk
    Assert-StackBranch -StackRoot $root -Branch 'master' -RequiredPaths @('tools\Opc.Ua.Mcp\Opc.Ua.Mcp.csproj')

    $referenceServer = Join-Path $root 'samples\ConsoleReferenceServer\ConsoleReferenceServer.csproj'
    $mcpServer = Join-Path $root 'tools\Opc.Ua.Mcp\Opc.Ua.Mcp.csproj'

    Write-DemoStep -Message 'Build the reference server and MCP server' `
        -Detail 'Only the projects used by this demo are built.'
    Invoke-DemoBuild -Projects @($referenceServer, $mcpServer) -NoBuild:$NoBuild
    Wait-DemoKeypress

    Write-DemoStep -Message 'Start the OPC UA reference server' `
        -Detail 'The endpoint is opc.tcp://localhost:62541/Quickstarts/ReferenceServer.'
    $null = Start-DemoProcess -Name 'Reference Server' -Project $referenceServer -Arguments @('--autoaccept', '--console')
    Wait-DemoEndpoint -HostName 'localhost' -Port 62541
    Wait-DemoKeypress

    Write-DemoStep -Message 'Start the MCP server with the services profile' `
        -Detail 'Streamable HTTP listens on http://localhost:5100/mcp.'
    $null = Start-DemoProcess -Name 'OPC UA MCP Server' -Project $mcpServer `
        -Arguments @('--transport', 'http', '--port', '5100', '--profile', 'services')
    Wait-DemoEndpoint -HostName 'localhost' -Port 5100
    Wait-DemoKeypress

    Write-DemoStep -Message 'Connect the model to the OPC UA Server' `
        -Detail 'In the MCP client, call Connect with autoAcceptCerts=true and name=refserver.'
    Write-DemoNote 'Connect endpointUrl=opc.tcp://localhost:62541/Quickstarts/ReferenceServer'
    Write-DemoNote 'Then read opcua://sessions/refserver and opcua://sessions/refserver/namespaces.'
    Wait-DemoKeypress

    Write-DemoStep -Message 'Browse, read, write, subscribe and call methods' `
        -Detail 'Use BrowseAll, ReadValue, WriteValue, CreateSubscription, CreateMonitoredItems, Publish and CallMethod.'
    Write-DemoNote 'Start at i=85, the Objects folder. Read i=2258 for ServerStatus.CurrentTime.'
    Write-DemoNote 'The point is that the operator asks for intent; the MCP tool performs OPC UA service calls.'
    Wait-DemoKeypress
}
finally {
    if (-not $KeepRunning) {
        Stop-DemoProcesses
    }
}
