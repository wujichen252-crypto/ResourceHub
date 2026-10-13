param(
    [switch]$Watch,
    [int]$IntervalSeconds = 30
)

$ErrorActionPreference = "Stop"
$configPath = Join-Path $PSScriptRoot "deploy.config.local.ps1"
if (-not (Test-Path -LiteralPath $configPath)) {
    throw "缺少 deploy.config.local.ps1，请先复制 deploy.config.example.ps1 并填写服务器配置。"
}
. $configPath

function Invoke-Deploy {
    $sshArgs = @()
    if ($DeployConfig.SshPort) { $sshArgs += @('-p', [string]$DeployConfig.SshPort) }
    if ($DeployConfig.IdentityFile) { $sshArgs += @('-i', $DeployConfig.IdentityFile) }
    $target = "$($DeployConfig.ServerUser)@$($DeployConfig.ServerHost)"
    $remote = "cd '$($DeployConfig.ServerPath)' && git fetch origin '$($DeployConfig.Branch)' && git checkout '$($DeployConfig.Branch)' && git reset --hard 'origin/$($DeployConfig.Branch)' && docker compose up -d --build --remove-orphans && docker compose ps"
    Write-Host "正在部署 $target ..." -ForegroundColor Cyan
    & ssh @sshArgs $target $remote
    if ($LASTEXITCODE -ne 0) { throw "远程部署失败，退出码：$LASTEXITCODE" }
}

if ($Watch) {
    Write-Host "持续部署已启动：检测到分支推送后自动部署，按 Ctrl+C 停止。" -ForegroundColor Green
    $lastCommit = ""
    while ($true) {
        $currentCommit = (git ls-remote origin $DeployConfig.Branch 2>$null | Select-Object -First 1).Split("`t")[0]
        if ($currentCommit -and $currentCommit -ne $lastCommit) {
            $lastCommit = $currentCommit
            Invoke-Deploy
        }
        Start-Sleep -Seconds $IntervalSeconds
    }
} else {
    Invoke-Deploy
}
