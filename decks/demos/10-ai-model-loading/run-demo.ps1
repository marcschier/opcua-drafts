#Requires -Version 7.4
<#
.SYNOPSIS
    Runs the AI model loading demo.
.DESCRIPTION
    Starts the AI Model Management sample from the marcschier/vision-guided-picking branch together
    with its local OpenAI-compatible verification backend, then runs the sample client to browse
    deployments, invoke a model and print the model provenance returned with the answer.
.PARAMETER StackRoot
    Path to a UA-.NETStandard checkout on marcschier/vision-guided-picking. If omitted, the shared
    demo module locates a checkout that contains the required marker paths.
.PARAMETER NoBuild
    Skip building the referenced projects before running.
.PARAMETER KeepRunning
    Leave the verification backend and OPC UA Server running when the script exits.
.EXAMPLE
    .\run-demo.ps1 -StackRoot C:\src\ua-ai-models
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

$backendProcess = $null
$environmentNames = @(
    'InferenceBackend__EndpointUri',
    'AiModelManagement__LearningStageInterval',
    'AiModelManagement__AsyncInferenceDelay'
)
$savedEnvironment = @{}
foreach ($name in $environmentNames) {
    $savedEnvironment[$name] = [Environment]::GetEnvironmentVariable($name, 'Process')
}

try {
    Write-DemoBanner `
        -Title 'Demo 10 — AI model loading' `
        -Shows 'Model registration, invocation and provenance through OPC UA'

    $requiredPaths = @(
        'samples\AI\README.md',
        'samples\AI\ModelManagementServer\ModelManagementServer.csproj',
        'samples\AI\ModelManagementClient\ModelManagementClient.csproj',
        'samples\AI\verify_backend.py',
        'src\Opc.Ua.AI\Opc.Ua.AI.csproj'
    )
    $root = Resolve-StackRoot -StackRoot $StackRoot -RequiredPaths @($requiredPaths[0])
    Assert-StackBranch -StackRoot $root -Branch 'marcschier/vision-guided-picking' -RequiredPaths $requiredPaths
    Assert-DotNetSdk

    $python = Get-Command python -ErrorAction SilentlyContinue
    if (-not $python) {
        throw 'Python is not on PATH. It is needed for samples\AI\verify_backend.py.'
    }

    $server = Join-Path $root 'samples\AI\ModelManagementServer\ModelManagementServer.csproj'
    $client = Join-Path $root 'samples\AI\ModelManagementClient\ModelManagementClient.csproj'
    $backend = Join-Path $root 'samples\AI\verify_backend.py'

    Write-DemoStep -Message 'Build the server and client' `
        -Detail 'The companion model comes from the Opc.Ua.AI libraries under src.'
    Invoke-DemoBuild -Projects @($server, $client) -NoBuild:$NoBuild
    Wait-DemoKeypress

    Write-DemoStep -Message 'Start the OpenAI-compatible test backend' `
        -Detail 'The test double listens on http://127.0.0.1:5273 and returns verify-model.'
    $backendProcess = Start-Process -FilePath $python.Source -ArgumentList @($backend, '5273') -PassThru
    Wait-DemoEndpoint -HostName '127.0.0.1' -Port 5273
    Wait-DemoKeypress

    Write-DemoStep -Message 'Start the OPC UA AI Model Management server' `
        -Detail 'The server publishes deployments, model source, catalogue and learning-loop nodes.'
    $env:InferenceBackend__EndpointUri = 'http://127.0.0.1:5273/'
    $env:AiModelManagement__LearningStageInterval = '00:00:05'
    $env:AiModelManagement__AsyncInferenceDelay = '00:00:01'
    [void](Start-DemoProcess -Name 'AI Model Management Server' -Project $server `
            -Arguments @('--host', '127.0.0.1', '--port', '62640'))
    Wait-DemoEndpoint -HostName 'localhost' -Port 62640
    Wait-DemoKeypress

    Write-DemoStep -Message 'Run the sample client' `
        -Detail 'It browses the catalogue and deployments, then calls GetCapabilities, Invoke, BeginTransfer and InvokeAsync.'
    & dotnet run --project $client -c Release -f net10.0 --no-build --nologo -- `
        'opc.tcp://localhost:62640/ModelManagementServer'
    if ($LASTEXITCODE -ne 0) {
        throw "AI Model Management client failed with exit code $LASTEXITCODE."
    }
    Wait-DemoKeypress

    Write-DemoStep -Message 'Read the provenance' `
        -Detail 'Focus on UsesModel, ModelUsed and FinishReason returned beside each answer.'
    Write-DemoNote 'The learning loop is simulated in this sample; it does not retrain a model.'
    Write-DemoNote 'The backend is a test double so the OPC UA path is runnable without a cloud account.'
    Wait-DemoKeypress
}
finally {
    foreach ($name in $environmentNames) {
        [Environment]::SetEnvironmentVariable($name, $savedEnvironment[$name], 'Process')
    }
    if (-not $KeepRunning) {
        Stop-DemoProcesses
        if ($backendProcess -and -not $backendProcess.HasExited) {
            Stop-Process -Id $backendProcess.Id -ErrorAction SilentlyContinue
        }
    }
}
