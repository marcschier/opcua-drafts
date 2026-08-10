<#
.SYNOPSIS
    Shared helpers for the demo scripts under decks/demos/.

.DESCRIPTION
    Every demo script does the same four things: check that the machine and the
    checkout can run it, build only the projects it needs, start some servers and
    run a client against them, then stop everything it started. This module holds
    that machinery so each demo script is about the demo.
#>

Set-StrictMode -Version Latest

$script:StartedProcesses = [System.Collections.Generic.List[object]]::new()
$script:StepNumber = 0

function Write-DemoBanner {
    <#
    .SYNOPSIS
        Print the demo's title block.
    #>
    [Diagnostics.CodeAnalysis.SuppressMessageAttribute('PSAvoidUsingWriteHost', '',
        Justification = 'Presenter-facing coloured narration; the host is the point, and this output must not be capturable or redirectable into a caller pipeline.')]
    [CmdletBinding()]
    param(
        [Parameter(Mandatory)][string] $Title,
        [Parameter(Mandatory)][string] $Shows,
        [string] $Duration = '5 minutes'
    )

    $rule = '=' * 78
    Write-Host ''
    Write-Host $rule -ForegroundColor DarkCyan
    Write-Host "  $Title" -ForegroundColor Cyan
    Write-Host "  Shows:    $Shows" -ForegroundColor Gray
    Write-Host "  Runtime:  $Duration" -ForegroundColor Gray
    Write-Host $rule -ForegroundColor DarkCyan
    Write-Host ''
    $script:StepNumber = 0
}

function Write-DemoStep {
    <#
    .SYNOPSIS
        Announce the next numbered step, matching the walkthrough in README.md.
    #>
    [Diagnostics.CodeAnalysis.SuppressMessageAttribute('PSAvoidUsingWriteHost', '',
        Justification = 'Presenter-facing coloured narration; see Write-DemoBanner.')]
    [CmdletBinding()]
    param(
        [Parameter(Mandatory)][string] $Message,
        [string] $Detail
    )

    $script:StepNumber++
    Write-Host ''
    Write-Host ("  [{0}] {1}" -f $script:StepNumber, $Message) -ForegroundColor Yellow
    if ($Detail) {
        Write-Host "      $Detail" -ForegroundColor DarkGray
    }
}

function Write-DemoNote {
    <#
    .SYNOPSIS
        Print an aside for the presenter, indented under the current step.
    #>
    [Diagnostics.CodeAnalysis.SuppressMessageAttribute('PSAvoidUsingWriteHost', '',
        Justification = 'Presenter-facing coloured narration; see Write-DemoBanner.')]
    [CmdletBinding()]
    param([Parameter(Mandatory)][string] $Message)

    Write-Host "      $Message" -ForegroundColor DarkGray
}

function Resolve-StackRoot {
    <#
    .SYNOPSIS
        Locate the UA-.NETStandard checkout the demo runs against.

    .DESCRIPTION
        Uses -StackRoot when given, then the OPCUA_STACK_ROOT environment variable,
        then looks for a sibling checkout containing UA.slnx. When -RequiredPaths is
        given, only a checkout that actually carries those paths is accepted, which
        matters on a machine holding several checkouts on different branches.
    #>
    [CmdletBinding()]
    [OutputType([string])]
    param(
        [string] $StackRoot,
        [string[]] $RequiredPaths = @()
    )

    $candidates = @()
    if ($StackRoot) { $candidates += $StackRoot }
    if ($env:OPCUA_STACK_ROOT) { $candidates += $env:OPCUA_STACK_ROOT }

    $decksRoot = Split-Path -Parent $PSScriptRoot          # decks/demos
    $decksRoot = Split-Path -Parent $decksRoot             # decks
    $repoRoot = Split-Path -Parent $decksRoot              # opcua-drafts
    $gitRoot = Split-Path -Parent $repoRoot                # folder holding sibling checkouts

    foreach ($root in @($gitRoot, (Split-Path -Parent $gitRoot))) {
        if (-not $root -or -not (Test-Path $root)) { continue }
        $siblings = Get-ChildItem -Path $root -Directory -ErrorAction SilentlyContinue |
            Where-Object { Test-Path (Join-Path $_.FullName 'UA.slnx') } |
            Select-Object -ExpandProperty FullName
        $candidates += $siblings
    }

    $viable = @()
    foreach ($candidate in $candidates) {
        if (-not $candidate -or -not (Test-Path (Join-Path $candidate 'UA.slnx'))) { continue }
        $viable += (Resolve-Path $candidate).Path
    }

    if ($RequiredPaths.Count -gt 0) {
        foreach ($candidate in $viable) {
            $satisfied = $true
            foreach ($required in $RequiredPaths) {
                if (-not (Test-Path (Join-Path $candidate $required))) {
                    $satisfied = $false
                    break
                }
            }
            if ($satisfied) { return $candidate }
        }
    }

    if ($viable.Count -gt 0) {
        return $viable[0]
    }

    throw @'
Could not find a UA-.NETStandard checkout.

Pass one explicitly:
    .\run-demo.ps1 -StackRoot D:\git\UA-.NETStandard

or set it once for the session:
    $env:OPCUA_STACK_ROOT = 'D:\git\UA-.NETStandard'
'@
}

function Assert-DotNetSdk {
    <#
    .SYNOPSIS
        Fail early and clearly when the required .NET SDK is missing.
    #>
    [CmdletBinding()]
    param([int] $MinimumMajor = 10)

    $dotnet = Get-Command dotnet -ErrorAction SilentlyContinue
    if (-not $dotnet) {
        throw 'The .NET SDK is not on PATH. Install .NET 10 from https://dot.net and re-run.'
    }

    $versions = & dotnet --list-sdks 2>$null
    $majors = foreach ($line in $versions) {
        if ($line -match '^(\d+)\.') { [int]$Matches[1] }
    }
    if (-not $majors -or ($majors | Measure-Object -Maximum).Maximum -lt $MinimumMajor) {
        throw "This demo needs the .NET $MinimumMajor SDK. Installed: $($versions -join ', ')"
    }
}

function Assert-StackBranch {
    <#
    .SYNOPSIS
        Refuse to run when the checkout does not carry the code the demo needs.

    .DESCRIPTION
        Demos that depend on a feature branch check for a marker path rather than a
        branch name, so a worktree, a rename or a merge into master all work. The
        branch name is only used in the message that tells the presenter what to do.
    #>
    [CmdletBinding()]
    param(
        [Parameter(Mandatory)][string] $StackRoot,
        [Parameter(Mandatory)][string] $Branch,
        [Parameter(Mandatory)][string[]] $RequiredPaths
    )

    $missing = $RequiredPaths | Where-Object { -not (Test-Path (Join-Path $StackRoot $_)) }
    if (-not $missing) {
        return
    }

    $current = (& git -C $StackRoot rev-parse --abbrev-ref HEAD 2>$null)
    $missingList = $missing -join "`n    "
    throw @"
This demo needs code that is not in the checkout at $StackRoot (currently on '$current').

Missing:
    $missingList

Switch to the feature branch:
    git -C $StackRoot fetch --all
    git -C $StackRoot switch $Branch

or keep master intact and use a worktree:
    git -C $StackRoot worktree add ..\ua-demo $Branch
    .\run-demo.ps1 -StackRoot ..\ua-demo
"@
}

function Invoke-DemoBuild {
    <#
    .SYNOPSIS
        Build the projects a demo needs, quietly, failing loudly.
    #>
    [CmdletBinding()]
    param(
        [Parameter(Mandatory)][string[]] $Projects,
        [string] $Configuration = 'Release',
        [string] $Framework = 'net10.0',
        [switch] $NoBuild
    )

    if ($NoBuild) {
        Write-DemoNote 'Skipping build (-NoBuild).'
        return
    }

    foreach ($project in $Projects) {
        if (-not (Test-Path $project)) {
            throw "Project not found: $project"
        }
        Write-DemoNote "building $(Split-Path -Leaf $project)"
        & dotnet build $project -c $Configuration -f $Framework --nologo -v quiet
        if ($LASTEXITCODE -ne 0) {
            throw "Build failed: $project"
        }
    }
}

function Start-DemoProcess {
    <#
    .SYNOPSIS
        Start a background process the demo will stop again on the way out.
    #>
    [CmdletBinding(SupportsShouldProcess)]
    [OutputType([System.Diagnostics.Process])]
    param(
        [Parameter(Mandatory)][string] $Name,
        [Parameter(Mandatory)][string] $Project,
        [string[]] $Arguments = @(),
        [string] $Configuration = 'Release',
        [string] $Framework = 'net10.0',
        [string] $WorkingDirectory,
        [int] $ReadySeconds = 8
    )

    $runArgs = @('run', '--project', $Project, '-c', $Configuration, '-f', $Framework,
        '--no-build', '--nologo', '--')
    $runArgs += $Arguments

    $startInfo = @{
        FilePath     = 'dotnet'
        ArgumentList = $runArgs
        PassThru     = $true
    }
    if ($WorkingDirectory) { $startInfo['WorkingDirectory'] = $WorkingDirectory }

    Write-DemoNote "starting $Name"
    if (-not $PSCmdlet.ShouldProcess($Name, 'Start')) {
        return $null
    }
    $process = Start-Process @startInfo
    $script:StartedProcesses.Add([pscustomobject]@{ Name = $Name; Process = $process })

    if ($ReadySeconds -gt 0) {
        Start-Sleep -Seconds $ReadySeconds
        if ($process.HasExited) {
            throw "$Name exited immediately with code $($process.ExitCode)."
        }
    }
    return $process
}

function Wait-DemoEndpoint {
    <#
    .SYNOPSIS
        Block until a TCP endpoint accepts a connection, or give up.
    #>
    [CmdletBinding()]
    param(
        [Parameter(Mandatory)][string] $HostName,
        [Parameter(Mandatory)][int] $Port,
        [int] $TimeoutSeconds = 45
    )

    $deadline = (Get-Date).AddSeconds($TimeoutSeconds)
    while ((Get-Date) -lt $deadline) {
        try {
            $client = [System.Net.Sockets.TcpClient]::new()
            $client.Connect($HostName, $Port)
            $client.Close()
            Write-DemoNote "${HostName}:${Port} is accepting connections"
            return
        }
        catch {
            Start-Sleep -Milliseconds 500
        }
    }
    throw "Timed out waiting for ${HostName}:${Port}."
}

function Stop-DemoProcesses {
    <#
    .SYNOPSIS
        Stop everything Start-DemoProcess started, in reverse order.
    #>
    [Diagnostics.CodeAnalysis.SuppressMessageAttribute('PSUseSingularNouns', '',
        Justification = 'The function stops every process the demo started, not one; the plural is the contract.')]
    [CmdletBinding(SupportsShouldProcess)]
    param()

    for ($index = $script:StartedProcesses.Count - 1; $index -ge 0; $index--) {
        $entry = $script:StartedProcesses[$index]
        if ($entry.Process.HasExited) { continue }
        if ($PSCmdlet.ShouldProcess($entry.Name, 'Stop')) {
            Write-DemoNote "stopping $($entry.Name)"
            Stop-Process -Id $entry.Process.Id -ErrorAction SilentlyContinue
        }
    }
    $script:StartedProcesses.Clear()
}

function Wait-DemoKeypress {
    <#
    .SYNOPSIS
        Pause so the presenter can talk over what is on screen.
    #>
    [Diagnostics.CodeAnalysis.SuppressMessageAttribute('PSAvoidUsingWriteHost', '',
        Justification = 'Presenter-facing coloured narration; see Write-DemoBanner.')]
    [CmdletBinding()]
    param([string] $Message = 'Press Enter to continue')

    if ([System.Console]::IsInputRedirected) {
        return
    }
    Write-Host ''
    Write-Host "      $Message..." -ForegroundColor DarkCyan
    [void](Read-Host)
}

Export-ModuleMember -Function @(
    'Write-DemoBanner'
    'Write-DemoStep'
    'Write-DemoNote'
    'Resolve-StackRoot'
    'Assert-DotNetSdk'
    'Assert-StackBranch'
    'Invoke-DemoBuild'
    'Start-DemoProcess'
    'Wait-DemoEndpoint'
    'Stop-DemoProcesses'
    'Wait-DemoKeypress'
)
