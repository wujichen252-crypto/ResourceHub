# 复制为 deploy.config.local.ps1，并填写你的服务器信息。此文件不会入库。
$DeployConfig = @{
    ServerHost = "47.108.232.238"
    ServerUser = "root"
    ServerPath = "/opt/resourcehub"
    Branch = "main"
    SshPort = 22
    # 如使用密钥，填写私钥路径；留空则使用 SSH 默认密钥/代理。
    IdentityFile = ""
}
