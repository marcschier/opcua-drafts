#Requires -Version 7.4
<#
.SYNOPSIS
    Runs the WoT Connectivity pump aggregation demo.
.DESCRIPTION
    Starts two flat OPC UA tag sources and the generic WoT aggregation server,
    then runs the aggregation client that uploads Thing Models and a Thing Description,
    refreshes the registry projection, browses the materialized Pump, and reads values.
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
        -Title 'Pumps with pump companion spec via WoT Connectivity' `
        -Shows 'Flat tags projected into a companion-spec Pump through WoT documents'

    $root = Resolve-StackRoot -StackRoot $StackRoot -RequiredPaths @(
        'samples\WotCon\AggregationClient\Documents\documents.json'
    )
    Assert-DotNetSdk
    Assert-StackBranch -StackRoot $root -Branch 'master' -RequiredPaths @(
        'src\Opc.Ua.WotCon\Opc.Ua.WotCon.csproj',
        'src\Opc.Ua.WotCon.Bindings\Opc.Ua.WotCon.Bindings.csproj'
    )

    $sourceProject = Join-Path $root 'samples\WotCon\FlatTagServer\FlatTagServer.csproj'
    $serverProject = Join-Path $root 'samples\WotCon\AggregationServer\AggregationServer.csproj'
    $clientProject = Join-Path $root 'samples\WotCon\AggregationClient\AggregationClient.csproj'
    $documents = Join-Path $root 'samples\WotCon\AggregationClient\Documents'

    Write-DemoStep -Message 'Build the WoT aggregation sample projects' `
        -Detail 'The source servers are flat; the aggregation server is generic.'
    Invoke-DemoBuild -Projects @($sourceProject, $serverProject, $clientProject) -NoBuild:$NoBuild
    Wait-DemoKeypress

    Write-DemoStep -Message 'Start the two flat tag sources' `
        -Detail 'Source A and Source B publish simple variables, not a PumpType hierarchy.'
    Start-DemoProcess -Name 'FlatTagServer Source A' -Project $sourceProject -Arguments @(
        '--port', '62551', '--instanceName', 'SourceA',
        '--applicationName', 'FlatTagServerSourceA',
        '--namespace', 'urn:opcfoundation.org:UA:WotAggregation:SourceA',
        '--differentialPressure', '111.25', '--fluidTemperature', '301.15',
        '--massFlow', '0.42', '--level', '4.25', '--cavitation', 'true'
    ) | Out-Null
    Start-DemoProcess -Name 'FlatTagServer Source B' -Project $sourceProject -Arguments @(
        '--port', '62552', '--instanceName', 'SourceB',
        '--applicationName', 'FlatTagServerSourceB',
        '--namespace', 'urn:opcfoundation.org:UA:WotAggregation:SourceB',
        '--bearingTemperature', '333.15', '--pumpPowerInput', '17.75',
        '--pumpEfficiency', '91.5', '--numberOfStarts', '23', '--motorOverheat', 'true'
    ) | Out-Null
    Wait-DemoEndpoint -HostName 'localhost' -Port 62551
    Wait-DemoEndpoint -HostName 'localhost' -Port 62552
    Wait-DemoKeypress

    Write-DemoStep -Message 'Start the generic aggregation server' `
        -Detail 'It receives documents and materializes a runtime Pump address space.'
    Start-DemoProcess -Name 'AggregationServer' -Project $serverProject -Arguments @(
        '--port', '62550', '--applicationName', 'AggregationServer'
    ) | Out-Null
    Wait-DemoEndpoint -HostName 'localhost' -Port 62550
    Wait-DemoKeypress

    Write-DemoStep -Message 'Upload the WoT documents and read the Pump projection' `
        -Detail 'The client uploads DI, Machinery, Pumps, and SamplePump documents, then calls Refresh.'
    & dotnet run --project $clientProject -c Release -f net10.0 --no-build --nologo -- `
        --aggregationEndpoint 'opc.tcp://localhost:62550/AggregationServer' `
        --sourceAEndpoint 'opc.tcp://localhost:62551/SourceA' `
        --sourceBEndpoint 'opc.tcp://localhost:62552/SourceB' `
        --documentsDirectory $documents
    if ($LASTEXITCODE -ne 0) {
        throw "AggregationClient failed with exit code $LASTEXITCODE."
    }
    Write-DemoNote 'Look for four uploaded resources, a successful refresh, a Pump browse, and ten Good values.'
    Wait-DemoKeypress
}
finally {
    if (-not $KeepRunning) { Stop-DemoProcesses }
}
